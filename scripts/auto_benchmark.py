#!/usr/bin/env python3
"""Kapsamli otomatik benchmark scripti.

Bu script, mevcut `intent_benchmark.py` uzerindeki benchmark kosusunu
tekrarli/istatistiksel hale getirir (yalnizca 2-asamali/hierarchical):

- Warmup + tekrarli run
- Sadece Hierarchical (2-asamali) mod
- p50/p90/p95/p99 latency ve jitter
- Dogruluk trendi ve run bazli dagilim
- Basit acceptance gate (accuracy/latency esikleri)
- JSON + Markdown rapor ciktilari

Kullanim:
    python scripts/auto_benchmark.py
    python scripts/auto_benchmark.py --runs 10 --warmup 2
    python scripts/auto_benchmark.py --model qwen2.5:3b
    python scripts/auto_benchmark.py --min-accuracy 85 --max-avg-latency 1500
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from intent_benchmark import run_benchmark, TEST_CASES  # type: ignore


def _quantile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return float(ordered[low])
    low_v = ordered[low]
    high_v = ordered[high]
    return float(low_v + (high_v - low_v) * (pos - low))


@dataclass
class StatPack:
    mean: float
    stdev: float
    minimum: float
    maximum: float
    p50: float
    p90: float
    p95: float
    p99: float


@dataclass
class RunSnapshot:
    run_index: int
    mode: str
    wall_ms: float
    peak_memory_kb: float
    total: int
    correct: int
    incorrect: int
    errors: int
    accuracy_pct: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    category_accuracy_pct: float
    keyword_bypass_count: int
    interrupted: bool = False
    error: Optional[str] = None


@dataclass
class AggregateReport:
    mode: str
    model: str
    category_model: Optional[str]
    runs: int
    warmup: int
    total_cases: int
    accuracy: StatPack
    avg_latency: StatPack
    wall_time: StatPack
    memory_peak_kb: StatPack
    errors_total: int
    incorrect_total: int
    gates: Dict[str, Any]
    snapshots: List[RunSnapshot]


def _statpack(values: List[float]) -> StatPack:
    if not values:
        return StatPack(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return StatPack(
        mean=round(statistics.fmean(values), 3),
        stdev=round(statistics.pstdev(values), 3),
        minimum=round(min(values), 3),
        maximum=round(max(values), 3),
        p50=round(_quantile(values, 0.50), 3),
        p90=round(_quantile(values, 0.90), 3),
        p95=round(_quantile(values, 0.95), 3),
        p99=round(_quantile(values, 0.99), 3),
    )


def _run_once(model: str, category_model: Optional[str], run_index: int) -> RunSnapshot:

    tracemalloc.start()
    t0 = time.perf_counter()
    interrupted = False
    error: Optional[str] = None
    try:
        summary = run_benchmark(
            model=model,
            category_model=category_model,
        )
        total = summary.total
        correct = summary.correct
        incorrect = summary.incorrect
        errors = summary.errors
        accuracy_pct = summary.accuracy_pct
        avg_latency_ms = summary.avg_latency_ms
        min_latency_ms = summary.min_latency_ms
        max_latency_ms = summary.max_latency_ms
        category_accuracy_pct = summary.category_accuracy_pct
        keyword_bypass_count = summary.keyword_bypass_count
    except KeyboardInterrupt:
        interrupted = True
        error = "KeyboardInterrupt"
        total = len(TEST_CASES)
        correct = 0
        incorrect = 0
        errors = 1
        accuracy_pct = 0.0
        avg_latency_ms = 0.0
        min_latency_ms = 0.0
        max_latency_ms = 0.0
        category_accuracy_pct = 0.0
        keyword_bypass_count = 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        total = len(TEST_CASES)
        correct = 0
        incorrect = 0
        errors = 1
        accuracy_pct = 0.0
        avg_latency_ms = 0.0
        min_latency_ms = 0.0
        max_latency_ms = 0.0
        category_accuracy_pct = 0.0
        keyword_bypass_count = 0

    wall_ms = (time.perf_counter() - t0) * 1000.0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return RunSnapshot(
        run_index=run_index,
        mode="hierarchical",
        wall_ms=round(wall_ms, 3),
        peak_memory_kb=round(peak / 1024.0, 3),
        total=total,
        correct=correct,
        incorrect=incorrect,
        errors=errors,
        accuracy_pct=accuracy_pct,
        avg_latency_ms=avg_latency_ms,
        min_latency_ms=min_latency_ms,
        max_latency_ms=max_latency_ms,
        category_accuracy_pct=category_accuracy_pct,
        keyword_bypass_count=keyword_bypass_count,
        interrupted=interrupted,
        error=error,
    )


def _build_report(
    mode: str,
    model: str,
    category_model: Optional[str],
    runs: int,
    warmup: int,
    snapshots: List[RunSnapshot],
    min_accuracy: Optional[float],
    max_avg_latency: Optional[float],
) -> AggregateReport:
    accuracies = [s.accuracy_pct for s in snapshots]
    avg_latencies = [s.avg_latency_ms for s in snapshots]
    wall_times = [s.wall_ms for s in snapshots]
    memory_peaks = [s.peak_memory_kb for s in snapshots]

    errors_total = sum(s.errors for s in snapshots)
    incorrect_total = sum(s.incorrect for s in snapshots)

    gate_accuracy_ok = True if min_accuracy is None else (_statpack(accuracies).mean >= min_accuracy)
    gate_latency_ok = True if max_avg_latency is None else (_statpack(avg_latencies).p95 <= max_avg_latency)

    gates = {
        "min_accuracy": min_accuracy,
        "max_avg_latency": max_avg_latency,
        "accuracy_gate_pass": gate_accuracy_ok,
        "latency_gate_pass": gate_latency_ok,
        "overall_pass": bool(gate_accuracy_ok and gate_latency_ok and errors_total == 0),
        "errors_must_be_zero": errors_total == 0,
    }

    return AggregateReport(
        mode=mode,
        model=model,
        category_model=category_model,
        runs=runs,
        warmup=warmup,
        total_cases=len(TEST_CASES),
        accuracy=_statpack(accuracies),
        avg_latency=_statpack(avg_latencies),
        wall_time=_statpack(wall_times),
        memory_peak_kb=_statpack(memory_peaks),
        errors_total=errors_total,
        incorrect_total=incorrect_total,
        gates=gates,
        snapshots=snapshots,
    )


def _print_console_report(report: AggregateReport) -> None:
    print("\n" + "=" * 78)
    print(f"AUTO BENCHMARK | MODE={report.mode.upper()} | MODEL={report.model}")
    print("=" * 78)
    print(f"Runs / Warmup        : {report.runs} / {report.warmup}")
    print(f"Total Case / Run     : {report.total_cases}")
    print(f"Errors Total         : {report.errors_total}")
    print(f"Incorrect Total      : {report.incorrect_total}")
    print("-" * 78)
    print(
        "Accuracy %           : "
        f"mean={report.accuracy.mean:.2f} "
        f"stdev={report.accuracy.stdev:.2f} "
        f"p95={report.accuracy.p95:.2f}"
    )
    print(
        "Avg Latency (ms)     : "
        f"mean={report.avg_latency.mean:.2f} "
        f"stdev={report.avg_latency.stdev:.2f} "
        f"p95={report.avg_latency.p95:.2f}"
    )
    print(
        "Wall Time (ms)       : "
        f"mean={report.wall_time.mean:.2f} "
        f"p95={report.wall_time.p95:.2f} "
        f"max={report.wall_time.maximum:.2f}"
    )
    print(
        "Peak Mem (KB)        : "
        f"mean={report.memory_peak_kb.mean:.1f} "
        f"p95={report.memory_peak_kb.p95:.1f} "
        f"max={report.memory_peak_kb.maximum:.1f}"
    )
    print("-" * 78)
    print(
        "Gates                : "
        f"accuracy={report.gates['accuracy_gate_pass']} "
        f"latency={report.gates['latency_gate_pass']} "
        f"errors_zero={report.gates['errors_must_be_zero']} "
        f"overall={report.gates['overall_pass']}"
    )
    print("=" * 78)


def _markdown_for_report(report: AggregateReport) -> str:
    lines: List[str] = []
    lines.append(f"# Auto Benchmark Report - {report.mode}")
    lines.append("")
    lines.append("## Configuration")
    lines.append(f"- Model: `{report.model}`")
    lines.append(f"- Category Model: `{report.category_model or '-'}`")
    lines.append(f"- Runs: `{report.runs}`")
    lines.append(f"- Warmup: `{report.warmup}`")
    lines.append(f"- Cases per run: `{report.total_cases}`")
    lines.append("")

    lines.append("## Aggregate Metrics")
    lines.append("| Metric | Mean | Stdev | P50 | P90 | P95 | P99 | Min | Max |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    def row(name: str, s: StatPack) -> str:
        return (
            f"| {name} | {s.mean:.3f} | {s.stdev:.3f} | {s.p50:.3f} | {s.p90:.3f} | "
            f"{s.p95:.3f} | {s.p99:.3f} | {s.minimum:.3f} | {s.maximum:.3f} |"
        )

    lines.append(row("Accuracy %", report.accuracy))
    lines.append(row("Avg Latency (ms)", report.avg_latency))
    lines.append(row("Wall Time (ms)", report.wall_time))
    lines.append(row("Peak Memory (KB)", report.memory_peak_kb))
    lines.append("")

    lines.append("## Gates")
    lines.append(f"- Min Accuracy Target: `{report.gates['min_accuracy']}`")
    lines.append(f"- Max Avg Latency Target (P95): `{report.gates['max_avg_latency']}`")
    lines.append(f"- Accuracy Gate Pass: `{report.gates['accuracy_gate_pass']}`")
    lines.append(f"- Latency Gate Pass: `{report.gates['latency_gate_pass']}`")
    lines.append(f"- Errors Must Be Zero: `{report.gates['errors_must_be_zero']}`")
    lines.append(f"- Overall Pass: `{report.gates['overall_pass']}`")
    lines.append("")

    lines.append("## Run Snapshots")
    lines.append(
        "| Run | Accuracy % | Avg Latency (ms) | Wall (ms) | Peak Mem (KB) | "
        "Errors | Incorrect |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for s in report.snapshots:
        lines.append(
            f"| {s.run_index} | {s.accuracy_pct:.2f} | {s.avg_latency_ms:.2f} | "
            f"{s.wall_ms:.2f} | {s.peak_memory_kb:.1f} | {s.errors} | {s.incorrect} |"
        )

    return "\n".join(lines) + "\n"


def _run_mode(
    model: str,
    category_model: Optional[str],
    runs: int,
    warmup: int,
    min_accuracy: Optional[float],
    max_avg_latency: Optional[float],
) -> AggregateReport:
    mode = "hierarchical"
    print(f"\n[auto-benchmark] mode={mode} warmup={warmup} runs={runs} basliyor...")

    for idx in range(1, warmup + 1):
        _ = _run_once(model=model, category_model=category_model, run_index=-idx)
        print(f"  warmup {idx}/{warmup} tamam")

    snapshots: List[RunSnapshot] = []
    for idx in range(1, runs + 1):
        snap = _run_once(model=model, category_model=category_model, run_index=idx)
        snapshots.append(snap)
        if snap.error:
            print(
                f"  run {idx}/{runs} | ERROR={snap.error} "
                f"interrupted={snap.interrupted}"
            )
        else:
            print(
                f"  run {idx}/{runs} | accuracy={snap.accuracy_pct:.1f}% "
                f"avg_latency={snap.avg_latency_ms:.1f}ms errors={snap.errors}"
            )

    report = _build_report(
        mode=mode,
        model=model,
        category_model=category_model,
        runs=runs,
        warmup=warmup,
        snapshots=snapshots,
        min_accuracy=min_accuracy,
        max_avg_latency=max_avg_latency,
    )
    _print_console_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprehensive automatic benchmark runner")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--category-model", default=None)
    parser.add_argument("--runs", type=int, default=7, help="Olcum run sayisi")
    parser.add_argument("--warmup", type=int, default=2, help="Warmup run sayisi")
    parser.add_argument("--min-accuracy", type=float, default=85.0)
    parser.add_argument("--max-avg-latency", type=float, default=2000.0)
    parser.add_argument("--output", default=None, help="JSON output path")
    parser.add_argument("--markdown", default=None, help="Markdown output path")
    args = parser.parse_args()

    if args.runs <= 0:
        raise SystemExit("--runs 1 veya daha buyuk olmali")
    if args.warmup < 0:
        raise SystemExit("--warmup negatif olamaz")

    ts = int(time.time())
    json_output = Path(args.output) if args.output else PROJECT_ROOT / f"temp/auto_benchmark_{ts}.json"
    md_output = Path(args.markdown) if args.markdown else PROJECT_ROOT / f"temp/auto_benchmark_{ts}.md"

    payload: Dict[str, Any] = {
        "meta": {
            "generated_at_unix": ts,
            "mode": "hierarchical",
            "model": args.model,
            "category_model": args.category_model,
            "runs": args.runs,
            "warmup": args.warmup,
            "total_cases": len(TEST_CASES),
        }
    }

    md_sections: List[str] = []

    hier_report = _run_mode(
        model=args.model,
        category_model=args.category_model,
        runs=args.runs,
        warmup=args.warmup,
        min_accuracy=args.min_accuracy,
        max_avg_latency=args.max_avg_latency,
    )
    payload["hierarchical"] = asdict(hier_report)
    md_sections.append(_markdown_for_report(hier_report))

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text("\n".join(md_sections), encoding="utf-8")

    print(f"\n[auto-benchmark] JSON yazildi: {json_output}")
    print(f"[auto-benchmark] Markdown yazildi: {md_output}")


if __name__ == "__main__":
    main()
