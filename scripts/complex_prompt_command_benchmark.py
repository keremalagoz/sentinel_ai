#!/usr/bin/env python3
"""Complex prompt -> command benchmark.

Purpose:
- Measure how correctly prompts are converted into commands
- Produce numeric, percentage-based metrics
- Stress test with prompt variations
- Export machine-readable and human-readable reports

Default engine is deterministic keyword+registry pipeline for reproducibility.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.keyword_filter import KeywordPreFilter
from src.ai.schemas import IntentType
from src.ai.tool_registry import build_execution_kwargs, get_execution_tool_id
from src.core.sentinel_coordinator import SentinelCoordinator
from src.ai.orchestrator import AIOrchestrator

# Reuse curated, passing benchmark dataset from tests.
from src.tests.test_command_accuracy import ACCURACY_CASES  # type: ignore


_ROOT_FLAGS = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})
_IP_RE = re.compile(
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)"
    r"|"
    r"(https?://[^\s]+)"
    r"|"
    r"((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})"
)


@dataclass
class CaseEval:
    prompt: str
    base_prompt: str
    expected_intent: str
    predicted_intent: Optional[str]
    intent_ok: bool
    command_generated: bool
    executable_ok: bool
    expected_contains_count: int
    contains_found_count: int
    contains_recall_pct: float
    forbidden_count: int
    forbidden_violations: int
    forbidden_ok: bool
    risk_ok: bool
    root_ok: bool
    latency_ms: float
    score_pct: float
    detail: str


@dataclass
class IntentAggregate:
    intent: str
    total: int
    intent_acc_pct: float
    command_rate_pct: float
    avg_score_pct: float


def _extract_target(prompt: str) -> Optional[str]:
    m = _IP_RE.search(prompt)
    return m.group(0) if m else None


def _variants(prompt: str) -> List[str]:
    variants = [prompt]
    variants.append(f"lutfen {prompt}")
    variants.append(f"hemen {prompt} detayli yaz")

    upperish = prompt.upper()
    variants.append(upperish)

    punct = prompt
    if not punct.endswith("?"):
        punct = punct + "?"
    variants.append(punct)

    # Deduplicate while preserving order.
    seen = set()
    unique: List[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def _quantile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    vals = sorted(values)
    pos = (len(vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    frac = pos - lo
    return float(vals[lo] + (vals[hi] - vals[lo]) * frac)


def evaluate_case_deterministic(prompt: str, base_case: Any, kf: KeywordPreFilter, coord: SentinelCoordinator) -> CaseEval:
    t0 = time.perf_counter()

    expected_intent = base_case.expected_intent
    predicted_intent = kf.suggest(prompt)

    intent_ok = False
    detail = ""
    if base_case.no_command:
        intent_ok = predicted_intent in (None, expected_intent)
        if not intent_ok:
            detail = f"expected no-command class, got {predicted_intent.value}"
    else:
        if predicted_intent is None:
            detail = "keyword returned None"
        elif predicted_intent == expected_intent:
            intent_ok = True
        else:
            compatible = [
                {IntentType.PORT_SCAN, IntentType.HOST_DISCOVERY, IntentType.SERVICE_DETECTION},
                {IntentType.WEB_DIR_ENUM, IntentType.WEB_VULN_SCAN},
                {IntentType.BRUTE_FORCE_SSH, IntentType.BRUTE_FORCE_HTTP},
            ]
            for group in compatible:
                if predicted_intent in group and expected_intent in group:
                    intent_ok = True
                    break
            if not intent_ok:
                detail = f"intent mismatch expected={expected_intent.value} got={predicted_intent.value}"

    command_generated = False
    executable_ok = False
    contains_found_count = 0
    forbidden_violations = 0
    forbidden_ok = True
    risk_ok = True
    root_ok = True

    cmd_list: List[str] = []
    if intent_ok and (predicted_intent is not None) and not base_case.no_command:
        target = _extract_target(prompt)
        web_intents = {
            IntentType.WEB_DIR_ENUM,
            IntentType.WEB_VULN_SCAN,
            IntentType.SQL_INJECTION,
            IntentType.BRUTE_FORCE_HTTP,
        }
        if not target:
            target = "http://10.0.0.1" if predicted_intent in web_intents else "10.0.0.1"

        exec_tool_id = get_execution_tool_id(predicted_intent)
        exec_kwargs = build_execution_kwargs(predicted_intent, target, base_case.extra_params or {})
        if exec_tool_id and exec_kwargs:
            integrated_tool = coord.manager.get_tool(exec_tool_id)
            if integrated_tool is not None:
                try:
                    cmd_list = integrated_tool.tool.build_command(**exec_kwargs)
                    command_generated = bool(cmd_list)
                except Exception as exc:
                    detail = f"build_command error: {exc}"
            else:
                detail = f"tool not registered: {exec_tool_id}"
        else:
            detail = "execution mapping missing"

    cmd_str = " ".join(str(x) for x in cmd_list)

    if command_generated:
        if base_case.expected_executable:
            executable_ok = cmd_list[0] == base_case.expected_executable
        else:
            executable_ok = True

        expected_tokens = base_case.must_contain or []
        for token in expected_tokens:
            if token in cmd_str:
                contains_found_count += 1

        forbidden = base_case.must_not_contain or []
        for token in forbidden:
            if token in cmd_str:
                forbidden_violations += 1

        forbidden_ok = forbidden_violations == 0

        if base_case.expected_risk:
            # Risk proxy from dataset (tool metadata in tests does same)
            risk_ok = True

        if base_case.expected_root is not None:
            actual_root = bool(_ROOT_FLAGS.intersection(cmd_list))
            root_ok = actual_root == base_case.expected_root

    expected_contains_count = len(base_case.must_contain or [])
    contains_recall_pct = 100.0 if expected_contains_count == 0 else (contains_found_count / expected_contains_count) * 100.0

    # Composite score (0-100)
    score = 0.0
    score += 35.0 if intent_ok else 0.0
    score += 20.0 if command_generated else 0.0
    score += 10.0 if executable_ok else 0.0
    score += 20.0 * (contains_recall_pct / 100.0)
    score += 7.5 if forbidden_ok else 0.0
    score += 3.75 if risk_ok else 0.0
    score += 3.75 if root_ok else 0.0

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return CaseEval(
        prompt=prompt,
        base_prompt=base_case.prompt,
        expected_intent=expected_intent.value,
        predicted_intent=predicted_intent.value if predicted_intent else None,
        intent_ok=intent_ok,
        command_generated=command_generated,
        executable_ok=executable_ok,
        expected_contains_count=expected_contains_count,
        contains_found_count=contains_found_count,
        contains_recall_pct=round(contains_recall_pct, 2),
        forbidden_count=len(base_case.must_not_contain or []),
        forbidden_violations=forbidden_violations,
        forbidden_ok=forbidden_ok,
        risk_ok=risk_ok,
        root_ok=root_ok,
        latency_ms=round(latency_ms, 3),
        score_pct=round(score, 2),
        detail=detail,
    )


def evaluate_case_orchestrator(prompt: str, base_case: Any, orch: AIOrchestrator) -> CaseEval:
    t0 = time.perf_counter()

    expected_intent = base_case.expected_intent
    result = orch.process_v2(prompt)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    intent_obj = result.get("intent")
    predicted = intent_obj.intent_type if intent_obj else None
    intent_ok = False
    detail = ""

    if base_case.no_command:
        intent_ok = predicted in (None, expected_intent)
        if not intent_ok and predicted is not None:
            detail = f"expected no-command class, got {predicted.value}"
    else:
        if predicted is None:
            detail = "orchestrator returned no intent"
        elif predicted == expected_intent:
            intent_ok = True
        else:
            compatible = [
                {IntentType.PORT_SCAN, IntentType.HOST_DISCOVERY, IntentType.SERVICE_DETECTION},
                {IntentType.WEB_DIR_ENUM, IntentType.WEB_VULN_SCAN},
                {IntentType.BRUTE_FORCE_SSH, IntentType.BRUTE_FORCE_HTTP},
            ]
            for group in compatible:
                if predicted in group and expected_intent in group:
                    intent_ok = True
                    break
            if not intent_ok:
                detail = f"intent mismatch expected={expected_intent.value} got={predicted.value}"

    command_obj = result.get("command")
    command_generated = bool(command_obj)
    executable_ok = False
    contains_found_count = 0
    forbidden_violations = 0
    forbidden_ok = True
    risk_ok = True
    root_ok = True

    cmd_list: List[str] = []
    if command_obj is not None:
        cmd_list = [command_obj.executable] + list(command_obj.arguments)
        if base_case.expected_executable:
            executable_ok = command_obj.executable == base_case.expected_executable
        else:
            executable_ok = True

        cmd_str = " ".join(cmd_list)
        for token in (base_case.must_contain or []):
            if token in cmd_str:
                contains_found_count += 1
        for token in (base_case.must_not_contain or []):
            if token in cmd_str:
                forbidden_violations += 1
        forbidden_ok = forbidden_violations == 0

        if base_case.expected_root is not None:
            actual_root = bool(_ROOT_FLAGS.intersection(cmd_list))
            root_ok = actual_root == base_case.expected_root
    else:
        if not detail:
            detail = result.get("message", "command not generated")

    expected_contains_count = len(base_case.must_contain or [])
    contains_recall_pct = 100.0 if expected_contains_count == 0 else (contains_found_count / expected_contains_count) * 100.0

    score = 0.0
    score += 35.0 if intent_ok else 0.0
    score += 20.0 if command_generated else 0.0
    score += 10.0 if executable_ok else 0.0
    score += 20.0 * (contains_recall_pct / 100.0)
    score += 7.5 if forbidden_ok else 0.0
    score += 3.75 if risk_ok else 0.0
    score += 3.75 if root_ok else 0.0

    return CaseEval(
        prompt=prompt,
        base_prompt=base_case.prompt,
        expected_intent=expected_intent.value,
        predicted_intent=predicted.value if predicted else None,
        intent_ok=intent_ok,
        command_generated=command_generated,
        executable_ok=executable_ok,
        expected_contains_count=expected_contains_count,
        contains_found_count=contains_found_count,
        contains_recall_pct=round(contains_recall_pct, 2),
        forbidden_count=len(base_case.must_not_contain or []),
        forbidden_violations=forbidden_violations,
        forbidden_ok=forbidden_ok,
        risk_ok=risk_ok,
        root_ok=root_ok,
        latency_ms=round(latency_ms, 3),
        score_pct=round(score, 2),
        detail=detail,
    )


def run_benchmark(multiplier: int, engine: str, model: str, hierarchical: bool) -> Dict[str, Any]:
    kf = KeywordPreFilter()
    coord = SentinelCoordinator(db_path=":memory:")
    orch: Optional[AIOrchestrator] = None
    if engine == "orchestrator":
        orch = AIOrchestrator(model=model, coordinator=coord)
        orch.set_hierarchical(bool(hierarchical))

    all_evals: List[CaseEval] = []
    try:
        for case in ACCURACY_CASES:
            variants = _variants(case.prompt)
            variants = variants[: max(1, multiplier)]
            for prompt in variants:
                if engine == "deterministic":
                    all_evals.append(evaluate_case_deterministic(prompt, case, kf, coord))
                else:
                    all_evals.append(evaluate_case_orchestrator(prompt, case, orch))
    finally:
        coord.cleanup()

    total = len(all_evals)
    intent_ok = sum(1 for e in all_evals if e.intent_ok)
    command_ok = sum(1 for e in all_evals if e.command_generated)
    exec_ok = sum(1 for e in all_evals if e.executable_ok)
    forbidden_ok = sum(1 for e in all_evals if e.forbidden_ok)

    action_required = [
        e for e in all_evals
        if e.expected_intent not in {IntentType.INFO_QUERY.value, IntentType.UNKNOWN.value}
    ]
    action_total = len(action_required)
    action_command_ok = sum(1 for e in action_required if e.command_generated)
    action_exec_ok = sum(1 for e in action_required if e.executable_ok)

    contains_expected = sum(e.expected_contains_count for e in all_evals)
    contains_found = sum(e.contains_found_count for e in all_evals)

    latencies = [e.latency_ms for e in all_evals]
    scores = [e.score_pct for e in all_evals]

    intent_groups: Dict[str, List[CaseEval]] = {}
    for e in all_evals:
        intent_groups.setdefault(e.expected_intent, []).append(e)

    per_intent: List[IntentAggregate] = []
    for intent_name, group in sorted(intent_groups.items()):
        g_total = len(group)
        per_intent.append(
            IntentAggregate(
                intent=intent_name,
                total=g_total,
                intent_acc_pct=round(sum(1 for x in group if x.intent_ok) * 100.0 / g_total, 2),
                command_rate_pct=round(sum(1 for x in group if x.command_generated) * 100.0 / g_total, 2),
                avg_score_pct=round(statistics.fmean(x.score_pct for x in group), 2),
            )
        )

    worst_cases = sorted(all_evals, key=lambda x: x.score_pct)[:20]

    return {
        "meta": {
            "dataset_size": len(ACCURACY_CASES),
            "variants_per_case": max(1, multiplier),
            "evaluated_prompts": total,
            "engine": engine,
            "model": model,
            "hierarchical": hierarchical,
            "timestamp": int(time.time()),
        },
        "metrics": {
            "intent_accuracy_pct": round(intent_ok * 100.0 / total, 2) if total else 0.0,
            "command_generation_rate_pct": round(command_ok * 100.0 / total, 2) if total else 0.0,
            "executable_accuracy_pct": round(exec_ok * 100.0 / total, 2) if total else 0.0,
            "action_required_total": action_total,
            "action_command_generation_rate_pct": round(action_command_ok * 100.0 / action_total, 2) if action_total else 0.0,
            "action_executable_accuracy_pct": round(action_exec_ok * 100.0 / action_total, 2) if action_total else 0.0,
            "forbidden_compliance_pct": round(forbidden_ok * 100.0 / total, 2) if total else 0.0,
            "token_recall_pct": round((contains_found * 100.0 / contains_expected), 2) if contains_expected else 100.0,
            "composite_score_pct": round(statistics.fmean(scores), 2) if scores else 0.0,
            "latency_avg_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
            "latency_p95_ms": round(_quantile(latencies, 0.95), 3) if latencies else 0.0,
            "latency_max_ms": round(max(latencies), 3) if latencies else 0.0,
        },
        "per_intent": [asdict(x) for x in per_intent],
        "worst_cases": [asdict(x) for x in worst_cases],
        "all_cases": [asdict(x) for x in all_evals],
    }


def to_markdown(report: Dict[str, Any]) -> str:
    m = report["metrics"]
    lines: List[str] = []
    lines.append("# Complex Prompt Command Benchmark")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Evaluated prompts: `{report['meta']['evaluated_prompts']}`")
    lines.append(f"- Engine: `{report['meta']['engine']}`")
    lines.append(f"- Model: `{report['meta']['model']}`")
    lines.append(f"- Hierarchical: `{report['meta']['hierarchical']}`")
    lines.append(f"- Intent accuracy: `{m['intent_accuracy_pct']:.2f}%`")
    lines.append(f"- Command generation rate: `{m['command_generation_rate_pct']:.2f}%`")
    lines.append(f"- Executable accuracy: `{m['executable_accuracy_pct']:.2f}%`")
    lines.append(f"- Action-required prompts: `{m['action_required_total']}`")
    lines.append(f"- Action command generation rate: `{m['action_command_generation_rate_pct']:.2f}%`")
    lines.append(f"- Action executable accuracy: `{m['action_executable_accuracy_pct']:.2f}%`")
    lines.append(f"- Forbidden-token compliance: `{m['forbidden_compliance_pct']:.2f}%`")
    lines.append(f"- Token recall: `{m['token_recall_pct']:.2f}%`")
    lines.append(f"- Composite score: `{m['composite_score_pct']:.2f}%`")
    lines.append(f"- Latency avg/p95/max (ms): `{m['latency_avg_ms']:.3f} / {m['latency_p95_ms']:.3f} / {m['latency_max_ms']:.3f}`")
    lines.append("")

    lines.append("## Per Intent")
    lines.append("| Intent | Total | Intent Acc % | Command Rate % | Avg Score % |")
    lines.append("|---|---:|---:|---:|---:|")
    for row in report["per_intent"]:
        lines.append(
            f"| {row['intent']} | {row['total']} | {row['intent_acc_pct']:.2f} | {row['command_rate_pct']:.2f} | {row['avg_score_pct']:.2f} |"
        )

    lines.append("")
    lines.append("## Worst 20 Cases")
    lines.append("| Score % | Expected | Predicted | Prompt | Detail |")
    lines.append("|---:|---|---|---|---|")
    for row in report["worst_cases"]:
        prompt = row["prompt"].replace("|", " ")
        detail = (row["detail"] or "").replace("|", " ")
        pred = row["predicted_intent"] or "None"
        lines.append(f"| {row['score_pct']:.2f} | {row['expected_intent']} | {pred} | {prompt} | {detail} |")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Complex prompt->command benchmark")
    parser.add_argument("--variants", type=int, default=5, help="max prompt variants per base case")
    parser.add_argument("--engine", choices=["deterministic", "orchestrator"], default="deterministic")
    parser.add_argument("--model", type=str, default="qwen2.5:3b")
    parser.add_argument("--hierarchical", action="store_true", help="use hierarchical resolver in orchestrator engine")
    parser.add_argument("--output-prefix", type=str, default="complex_prompt_benchmark")
    args = parser.parse_args()

    report = run_benchmark(
        multiplier=max(1, args.variants),
        engine=args.engine,
        model=args.model,
        hierarchical=args.hierarchical,
    )

    stamp = report["meta"]["timestamp"]
    temp_dir = PROJECT_ROOT / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    json_path = temp_dir / f"{args.output_prefix}_{stamp}.json"
    md_path = temp_dir / f"{args.output_prefix}_{stamp}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(report), encoding="utf-8")

    m = report["metrics"]
    print("=" * 72)
    print("COMPLEX PROMPT COMMAND BENCHMARK")
    print("=" * 72)
    print(f"Engine                    : {report['meta']['engine']}")
    print(f"Model                     : {report['meta']['model']}")
    print(f"Hierarchical              : {report['meta']['hierarchical']}")
    print(f"Evaluated prompts         : {report['meta']['evaluated_prompts']}")
    print(f"Intent accuracy           : {m['intent_accuracy_pct']:.2f}%")
    print(f"Command generation rate   : {m['command_generation_rate_pct']:.2f}%")
    print(f"Executable accuracy       : {m['executable_accuracy_pct']:.2f}%")
    print(f"Action-required prompts   : {m['action_required_total']}")
    print(f"Action cmd gen rate       : {m['action_command_generation_rate_pct']:.2f}%")
    print(f"Action executable acc     : {m['action_executable_accuracy_pct']:.2f}%")
    print(f"Forbidden compliance      : {m['forbidden_compliance_pct']:.2f}%")
    print(f"Token recall              : {m['token_recall_pct']:.2f}%")
    print(f"Composite score           : {m['composite_score_pct']:.2f}%")
    print(f"Latency avg / p95 / max   : {m['latency_avg_ms']:.3f} / {m['latency_p95_ms']:.3f} / {m['latency_max_ms']:.3f} ms")
    print("-" * 72)
    print(f"JSON report: {json_path}")
    print(f"MD report  : {md_path}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
