#!/usr/bin/env python3
"""Comprehensive tool build benchmark for all registered tools.

This script validates every tool build surface in the repository by running a
scenario matrix against build_command(). It is broader than auto_benchmark.py:

- Covers every registered tool in TOOL_CLASS_MAP
- Covers every AI execution purpose in _EXECUTION_REGISTRY
- Exercises all declared build_command parameters across the matrix
- Includes positive build scenarios and negative guard scenarios
- Produces console, JSON, and Markdown reports

Usage:
    python scripts/tool_build_benchmark.py
    python scripts/tool_build_benchmark.py --skip-negative
    python scripts/tool_build_benchmark.py --output temp/tool_build.json
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.tool_registry import _EXECUTION_REGISTRY
from src.core.platform_utils import get_ping_count_flag, get_shell, get_shell_exec_flag
from src.core.tool_base import TOOL_CLASS_MAP


def _quantile(values: Sequence[float], q: float) -> float:
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


@dataclass(frozen=True)
class BuildScenario:
    scenario_id: str
    tool_id: str
    purpose: str
    variant: str
    kwargs: dict[str, Any]
    expected_prefix: tuple[str, ...] = ()
    required_tokens: tuple[str, ...] = ()
    forbidden_tokens: tuple[str, ...] = ()
    expected_error: Optional[str] = None


@dataclass
class ScenarioResult:
    scenario_id: str
    tool_id: str
    purpose: str
    variant: str
    kind: str
    success: bool
    duration_ms: float
    command: list[str]
    error: Optional[str] = None


@dataclass
class ParameterCoverage:
    tool_id: str
    parameters: list[str]
    exercised_parameters: list[str]
    missing_parameters: list[str]


@dataclass
class BenchmarkReport:
    total_cases: int
    positive_cases: int
    negative_cases: int
    passed: int
    failed: int
    overall_pass: bool
    mean_duration_ms: float
    p95_duration_ms: float
    tools_covered: list[str]
    uncovered_tools: list[str]
    execution_tools_covered: list[str]
    execution_tools_missing: list[str]
    parameter_coverage: list[ParameterCoverage]
    results: list[ScenarioResult]


PING_PREFIX = ("ping", get_ping_count_flag())
SHELL_PREFIX = (get_shell(), get_shell_exec_flag())


POSITIVE_SCENARIOS: list[BuildScenario] = [
    BuildScenario(
        scenario_id="ping-basic",
        tool_id="ping",
        purpose="network_reachability",
        variant="basic",
        kwargs={"target": "192.168.1.10", "count": 3},
        expected_prefix=PING_PREFIX + ("3",),
        required_tokens=("192.168.1.10",),
    ),
    BuildScenario(
        scenario_id="ping-extended",
        tool_id="ping",
        purpose="network_reachability",
        variant="extended",
        kwargs={"target": "example.com", "count": 2, "timeout": 2, "packet_size": 128},
        expected_prefix=PING_PREFIX + ("2",),
        required_tokens=("-W 2", "-s 128", "example.com"),
    ),
    BuildScenario(
        scenario_id="host-discovery-full",
        tool_id="nmap_ping_sweep",
        purpose="host_discovery",
        variant="full",
        kwargs={
            "target": "192.168.1.0/24",
            "timing": 4,
            "exclude": "192.168.1.254",
            "no_dns": True,
            "verbose": True,
        },
        expected_prefix=("nmap", "-sn", "-T4"),
        required_tokens=("--exclude 192.168.1.254", "-n", "-v", "192.168.1.0/24"),
    ),
    BuildScenario(
        scenario_id="port-scan-full",
        tool_id="nmap_port_scan",
        purpose="port_scan",
        variant="full",
        kwargs={
            "target": "192.168.1.10",
            "ports": "22,80,443",
            "scan_type": "sS",
            "timing": 4,
            "no_dns": True,
            "verbose": True,
            "service_detection": True,
            "no_ping": True,
            "osscan_guess": True,
            "traceroute": True,
        },
        expected_prefix=("nmap", "-sS"),
        required_tokens=(
            "-sV",
            "--osscan-guess",
            "-p 22,80,443",
            "-T4",
            "-n",
            "-Pn",
            "-v",
            "--traceroute",
            "192.168.1.10",
        ),
    ),
    BuildScenario(
        scenario_id="port-scan-aggressive-topports",
        tool_id="nmap_port_scan",
        purpose="port_scan",
        variant="aggressive_top_ports",
        kwargs={"target": "10.0.0.5", "top_ports": 25, "aggressive": True},
        expected_prefix=("nmap", "-A"),
        required_tokens=("--top-ports 25", "10.0.0.5"),
    ),
    BuildScenario(
        scenario_id="service-detection-all",
        tool_id="nmap_service_detection",
        purpose="service_detection",
        variant="all_versions",
        kwargs={
            "target": "192.168.1.10",
            "ports": "80,443",
            "version_intensity": 7,
            "timing": 3,
            "version_mode": "all",
            "verbose": True,
            "no_ping": True,
        },
        expected_prefix=("nmap", "-sV", "--version-intensity", "7"),
        required_tokens=("--version-all", "-T3", "-p 80,443", "-Pn", "-v", "192.168.1.10"),
    ),
    BuildScenario(
        scenario_id="service-detection-light",
        tool_id="nmap_service_detection",
        purpose="service_detection",
        variant="light_versions",
        kwargs={"target": "10.0.0.8", "ports": "22", "intensity": 2, "version_mode": "light"},
        expected_prefix=("nmap", "-sV", "--version-intensity", "2"),
        required_tokens=("--version-light", "-p 22", "10.0.0.8"),
    ),
    BuildScenario(
        scenario_id="os-detection-full",
        tool_id="nmap_os_detection",
        purpose="os_detection",
        variant="full",
        kwargs={
            "target": "192.168.1.11",
            "ports": "22,80",
            "timing": 4,
            "osscan_guess": True,
            "service_detection": True,
            "verbose": True,
            "no_ping": True,
        },
        expected_prefix=("nmap", "-O"),
        required_tokens=("-sV", "--osscan-guess", "-p 22,80", "-T4", "-Pn", "-v", "192.168.1.11"),
    ),
    BuildScenario(
        scenario_id="os-detection-aggressive",
        tool_id="nmap_os_detection",
        purpose="os_detection",
        variant="aggressive_top_ports",
        kwargs={"target": "192.168.1.12", "top_ports": 50, "aggressive": True},
        expected_prefix=("nmap", "-O"),
        required_tokens=("-sV", "--osscan-guess", "--top-ports 50", "192.168.1.12"),
    ),
    BuildScenario(
        scenario_id="vuln-scan-full",
        tool_id="nmap_vuln_scan",
        purpose="vuln_scan",
        variant="full",
        kwargs={
            "target": "192.168.1.20",
            "ports": "80,443",
            "scripts": "vuln",
            "script_args": "unsafe=1",
            "timing": 3,
            "verbose": True,
            "no_ping": True,
        },
        expected_prefix=("nmap", "-sS", "--script", "vuln"),
        required_tokens=("--script-args unsafe=1", "-T3", "-p 80,443", "-Pn", "-v", "192.168.1.20"),
    ),
    BuildScenario(
        scenario_id="dns-lookup-full",
        tool_id="dns_lookup",
        purpose="dns_lookup",
        variant="mx_with_server",
        kwargs={"domain": "example.com", "record_type": "MX", "dns_server": "8.8.8.8"},
        expected_prefix=("nslookup", "-type=MX", "example.com"),
        required_tokens=("8.8.8.8",),
    ),
    BuildScenario(
        scenario_id="ssl-scan-full",
        tool_id="ssl_scan",
        purpose="ssl_scan",
        variant="servername_tls_starttls",
        kwargs={
            "target": "mail.example.com",
            "port": 8443,
            "servername": "mail.example.com",
            "tls_version": "1.2",
            "starttls": "smtp",
        },
        expected_prefix=("openssl", "s_client", "-connect", "mail.example.com:8443"),
        required_tokens=("-showcerts", "-servername mail.example.com", "-tls1_2", "-starttls smtp"),
    ),
    BuildScenario(
        scenario_id="gobuster-full",
        tool_id="gobuster_dir",
        purpose="web_dir_enum",
        variant="full",
        kwargs={
            "url": "https://example.com",
            "wordlist": "common.txt",
            "extensions": "php,txt",
            "threads": 8,
            "status_codes": "200,301,302",
            "no_tls_validation": True,
            "follow_redirect": True,
        },
        expected_prefix=("gobuster", "dir", "-u", "https://example.com", "-w", "common.txt"),
        required_tokens=("-x php,txt", "-t 8", "-s 200,301,302", "-k", "-r", "-q"),
    ),
    BuildScenario(
        scenario_id="subdomain-enum-full",
        tool_id="subdomain_enum",
        purpose="subdomain_enum",
        variant="wordlist_override",
        kwargs={"domain": "example.com", "wordlist": "subs.txt"},
        expected_prefix=("bash", "-c"),
        required_tokens=("nslookup", "FOUND:", "example.com", "subs.txt"),
    ),
    BuildScenario(
        scenario_id="whois-basic",
        tool_id="whois_lookup",
        purpose="whois_lookup",
        variant="basic",
        kwargs={"domain": "example.com"},
        expected_prefix=("whois", "example.com"),
    ),
    BuildScenario(
        scenario_id="web-app-scan-basic",
        tool_id="web_app_scan",
        purpose="web_vuln_scan",
        variant="fingerprint",
        kwargs={"url": "https://example.com"},
        expected_prefix=SHELL_PREFIX,
        required_tokens=("curl -sI", "TECH:", "https://example.com"),
    ),
    BuildScenario(
        scenario_id="hydra-ssh-full",
        tool_id="hydra_ssh",
        purpose="brute_force_ssh",
        variant="custom_port_verbose",
        kwargs={
            "target": "10.0.0.5",
            "username": "admin",
            "wordlist": "users.txt",
            "port": 2222,
            "threads": 8,
            "verbose": True,
        },
        expected_prefix=("hydra", "-l", "admin", "-P", "users.txt", "-t", "8"),
        required_tokens=("-s 2222", "-V", "ssh://10.0.0.5"),
    ),
    BuildScenario(
        scenario_id="hydra-http-full",
        tool_id="hydra_http",
        purpose="brute_force_http",
        variant="custom_port_post",
        kwargs={
            "target": "10.0.0.6",
            "username": "admin",
            "wordlist": "wordlist.txt",
            "form_path": "/login",
            "form_params": "user=^USER^&pass=^PASS^",
            "fail_string": "invalid",
            "port": 8080,
            "threads": 6,
            "method": "http-form-post",
        },
        expected_prefix=("hydra", "-l", "admin", "-P", "wordlist.txt", "-t", "6"),
        required_tokens=("-s 8080", "10.0.0.6", "http-form-post", "/login:user=^USER^&pass=^PASS^:invalid"),
    ),
    BuildScenario(
        scenario_id="hydra-http-https-get",
        tool_id="hydra_http",
        purpose="brute_force_http",
        variant="default_https_get",
        kwargs={
            "target": "secure.example.com",
            "username": "tester",
            "wordlist": "http.txt",
            "form_path": "/signin",
            "form_params": "user=^USER^&pass=^PASS^",
            "fail_string": "fail",
            "port": 443,
            "threads": 4,
            "method": "https-get",
        },
        expected_prefix=("hydra", "-l", "tester", "-P", "http.txt", "-t", "4"),
        required_tokens=("secure.example.com", "https-get", "/signin:user=^USER^&pass=^PASS^:fail"),
        forbidden_tokens=("-s 443",),
    ),
    BuildScenario(
        scenario_id="sqlmap-default",
        tool_id="sqlmap_scan",
        purpose="sql_injection",
        variant="default",
        kwargs={"url": "http://example.com/item.php?id=1"},
        expected_prefix=("sqlmap", "-u", "http://example.com/item.php?id=1", "--batch"),
    ),
    BuildScenario(
        scenario_id="sqlmap-full",
        tool_id="sqlmap_scan",
        purpose="sql_injection",
        variant="forms_dbs_threads",
        kwargs={
            "url": "https://example.com/login.php?id=7",
            "level": 5,
            "risk": 3,
            "batch": False,
            "forms": True,
            "dbs": True,
            "threads": 4,
        },
        expected_prefix=("sqlmap", "-u", "https://example.com/login.php?id=7"),
        required_tokens=("--forms", "--level 5", "--risk 3", "--dbs", "--threads 4"),
        forbidden_tokens=("--batch",),
    ),
]


NEGATIVE_SCENARIOS: list[BuildScenario] = [
    BuildScenario(
        scenario_id="port-scan-invalid-scan-type",
        tool_id="nmap_port_scan",
        purpose="port_scan",
        variant="invalid_scan_type",
        kwargs={"target": "192.168.1.10", "scan_type": "sX"},
        expected_error="Invalid scan type",
    ),
    BuildScenario(
        scenario_id="dns-lookup-invalid-record",
        tool_id="dns_lookup",
        purpose="dns_lookup",
        variant="invalid_record_type",
        kwargs={"domain": "example.com", "record_type": "BAD"},
        expected_error="Invalid DNS record type",
    ),
    BuildScenario(
        scenario_id="ssl-scan-invalid-tls-version",
        tool_id="ssl_scan",
        purpose="ssl_scan",
        variant="invalid_tls_version",
        kwargs={"target": "example.com", "tls_version": "1.1"},
        expected_error="tls_version gecersiz",
    ),
    BuildScenario(
        scenario_id="gobuster-invalid-url",
        tool_id="gobuster_dir",
        purpose="web_dir_enum",
        variant="invalid_scheme",
        kwargs={"url": "ftp://example.com"},
        expected_error="url http:// veya https:// ile baslamali",
    ),
    BuildScenario(
        scenario_id="whois-invalid-domain",
        tool_id="whois_lookup",
        purpose="whois_lookup",
        variant="invalid_domain",
        kwargs={"domain": "example.com;cat"},
        expected_error="Invalid domain",
    ),
    BuildScenario(
        scenario_id="hydra-http-invalid-method",
        tool_id="hydra_http",
        purpose="brute_force_http",
        variant="invalid_method",
        kwargs={
            "target": "10.0.0.6",
            "username": "admin",
            "wordlist": "wordlist.txt",
            "method": "http-form-put",
        },
        expected_error="method gecersiz",
    ),
    BuildScenario(
        scenario_id="sqlmap-invalid-url",
        tool_id="sqlmap_scan",
        purpose="sql_injection",
        variant="invalid_scheme",
        kwargs={"url": "example.com/login.php?id=1"},
        expected_error="url http:// veya https:// ile baslamali",
    ),
]


def all_scenarios(include_negative: bool = True) -> list[BuildScenario]:
    scenarios = list(POSITIVE_SCENARIOS)
    if include_negative:
        scenarios.extend(NEGATIVE_SCENARIOS)
    return scenarios


def build_parameter_coverage(scenarios: Sequence[BuildScenario]) -> dict[str, ParameterCoverage]:
    coverage: dict[str, ParameterCoverage] = {}
    exercised_by_tool: dict[str, set[str]] = {tool_id: set() for tool_id in TOOL_CLASS_MAP}

    for scenario in scenarios:
        exercised_by_tool.setdefault(scenario.tool_id, set()).update(scenario.kwargs.keys())

    for tool_id, tool_cls in TOOL_CLASS_MAP.items():
        signature = inspect.signature(tool_cls.build_command)
        parameters = [
            name
            for name in signature.parameters
            if name not in {"self", "kwargs"}
        ]
        exercised_parameters = sorted(exercised_by_tool.get(tool_id, set()))
        missing_parameters = [name for name in parameters if name not in exercised_parameters]
        coverage[tool_id] = ParameterCoverage(
            tool_id=tool_id,
            parameters=parameters,
            exercised_parameters=exercised_parameters,
            missing_parameters=missing_parameters,
        )

    return coverage


def _validate_command(command: list[str], scenario: BuildScenario) -> None:
    if scenario.expected_prefix:
        prefix = list(scenario.expected_prefix)
        if command[: len(prefix)] != prefix:
            raise AssertionError(
                f"Prefix mismatch for {scenario.scenario_id}: expected {prefix}, got {command[:len(prefix)]}"
            )

    command_text = " ".join(command)
    for token in scenario.required_tokens:
        if token not in command_text:
            raise AssertionError(
                f"Missing token for {scenario.scenario_id}: {token!r} not in {command_text!r}"
            )

    for token in scenario.forbidden_tokens:
        if token in command_text:
            raise AssertionError(
                f"Forbidden token for {scenario.scenario_id}: {token!r} found in {command_text!r}"
            )


def _run_scenario(scenario: BuildScenario) -> ScenarioResult:
    started = time.perf_counter()
    tool = TOOL_CLASS_MAP[scenario.tool_id]()

    try:
        command = tool.build_command(**scenario.kwargs)
        if scenario.expected_error:
            raise AssertionError(f"Expected error was not raised: {scenario.expected_error}")

        _validate_command(command, scenario)
        success = True
        error = None
    except Exception as exc:
        command = []
        if scenario.expected_error and scenario.expected_error in str(exc):
            success = True
            error = None
        else:
            success = False
            error = f"{type(exc).__name__}: {exc}"

    duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        tool_id=scenario.tool_id,
        purpose=scenario.purpose,
        variant=scenario.variant,
        kind="negative" if scenario.expected_error else "positive",
        success=success,
        duration_ms=duration_ms,
        command=command,
        error=error,
    )


def run_build_benchmark(include_negative: bool = True) -> BenchmarkReport:
    scenarios = all_scenarios(include_negative=include_negative)
    results = [_run_scenario(scenario) for scenario in scenarios]
    coverage_map = build_parameter_coverage(scenarios)

    durations = [result.duration_ms for result in results]
    passed = sum(1 for result in results if result.success)
    failed = len(results) - passed
    tools_covered = sorted({scenario.tool_id for scenario in scenarios})
    uncovered_tools = sorted(set(TOOL_CLASS_MAP) - set(tools_covered))

    execution_tool_ids = {mapping["tool_id"] for mapping in _EXECUTION_REGISTRY.values()}
    execution_tools_covered = sorted(tool_id for tool_id in tools_covered if tool_id in execution_tool_ids)
    execution_tools_missing = sorted(execution_tool_ids - set(tools_covered))

    overall_pass = (
        failed == 0
        and not uncovered_tools
        and not execution_tools_missing
        and all(not item.missing_parameters for item in coverage_map.values())
    )

    return BenchmarkReport(
        total_cases=len(results),
        positive_cases=sum(1 for scenario in scenarios if not scenario.expected_error),
        negative_cases=sum(1 for scenario in scenarios if scenario.expected_error),
        passed=passed,
        failed=failed,
        overall_pass=overall_pass,
        mean_duration_ms=round(statistics.fmean(durations), 3) if durations else 0.0,
        p95_duration_ms=round(_quantile(durations, 0.95), 3),
        tools_covered=tools_covered,
        uncovered_tools=uncovered_tools,
        execution_tools_covered=execution_tools_covered,
        execution_tools_missing=execution_tools_missing,
        parameter_coverage=[coverage_map[tool_id] for tool_id in sorted(coverage_map)],
        results=results,
    )


def _print_console_report(report: BenchmarkReport) -> None:
    print("\n" + "=" * 86)
    print("TOOL BUILD BENCHMARK")
    print("=" * 86)
    print(f"Cases                : {report.total_cases} (positive={report.positive_cases}, negative={report.negative_cases})")
    print(f"Passed / Failed      : {report.passed} / {report.failed}")
    print(f"Mean / P95 (ms)      : {report.mean_duration_ms:.3f} / {report.p95_duration_ms:.3f}")
    print(f"Tools Covered        : {len(report.tools_covered)} / {len(TOOL_CLASS_MAP)}")
    print(f"Execution Coverage   : {len(report.execution_tools_covered)} / {len(_EXECUTION_REGISTRY)}")
    print(f"Overall Pass         : {report.overall_pass}")

    missing_parameter_tools = [item.tool_id for item in report.parameter_coverage if item.missing_parameters]
    if report.uncovered_tools:
        print(f"Uncovered Tools      : {', '.join(report.uncovered_tools)}")
    if report.execution_tools_missing:
        print(f"Missing Exec Tools   : {', '.join(report.execution_tools_missing)}")
    if missing_parameter_tools:
        print(f"Missing Parameters   : {', '.join(missing_parameter_tools)}")

    failures = [result for result in report.results if not result.success]
    if failures:
        print("-" * 86)
        print("Failures")
        for result in failures:
            print(f"- {result.scenario_id}: {result.error}")

    print("=" * 86)


def _markdown_for_report(report: BenchmarkReport) -> str:
    lines: list[str] = []
    lines.append("# Tool Build Benchmark Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total cases: `{report.total_cases}`")
    lines.append(f"- Positive cases: `{report.positive_cases}`")
    lines.append(f"- Negative cases: `{report.negative_cases}`")
    lines.append(f"- Passed: `{report.passed}`")
    lines.append(f"- Failed: `{report.failed}`")
    lines.append(f"- Overall pass: `{report.overall_pass}`")
    lines.append(f"- Mean duration (ms): `{report.mean_duration_ms}`")
    lines.append(f"- P95 duration (ms): `{report.p95_duration_ms}`")
    lines.append("")

    lines.append("## Coverage")
    lines.append(f"- Tools covered: `{len(report.tools_covered)}/{len(TOOL_CLASS_MAP)}`")
    lines.append(f"- Execution tools covered: `{len(report.execution_tools_covered)}/{len(_EXECUTION_REGISTRY)}`")
    lines.append(f"- Uncovered tools: `{', '.join(report.uncovered_tools) if report.uncovered_tools else '-'}`")
    lines.append(
        f"- Missing execution tools: `{', '.join(report.execution_tools_missing) if report.execution_tools_missing else '-'}`"
    )
    lines.append("")

    lines.append("## Parameter Coverage")
    lines.append("| Tool | Parameters | Exercised | Missing |")
    lines.append("|---|---|---|---|")
    for item in report.parameter_coverage:
        lines.append(
            f"| {item.tool_id} | {', '.join(item.parameters)} | {', '.join(item.exercised_parameters)} | {', '.join(item.missing_parameters) or '-'} |"
        )
    lines.append("")

    failures = [result for result in report.results if not result.success]
    lines.append("## Failures")
    if failures:
        for result in failures:
            lines.append(f"- {result.scenario_id}: {result.error}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Scenario Results")
    lines.append("| Scenario | Tool | Purpose | Variant | Kind | Success | Duration (ms) |")
    lines.append("|---|---|---|---|---|---|---:|")
    for result in report.results:
        lines.append(
            f"| {result.scenario_id} | {result.tool_id} | {result.purpose} | {result.variant} | {result.kind} | {result.success} | {result.duration_ms:.3f} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprehensive tool build benchmark")
    parser.add_argument("--skip-negative", action="store_true", help="Sadece pozitif build senaryolarini kos")
    parser.add_argument("--output", default=None, help="JSON output path")
    parser.add_argument("--markdown", default=None, help="Markdown output path")
    parser.add_argument("--fail-on-error", action="store_true", help="Herhangi bir hata varsa non-zero cik")
    args = parser.parse_args()

    ts = int(time.time())
    json_output = Path(args.output) if args.output else PROJECT_ROOT / f"temp/tool_build_benchmark_{ts}.json"
    md_output = Path(args.markdown) if args.markdown else PROJECT_ROOT / f"temp/tool_build_benchmark_{ts}.md"

    report = run_build_benchmark(include_negative=not args.skip_negative)
    _print_console_report(report)

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(_markdown_for_report(report), encoding="utf-8")

    print(f"[tool-build-benchmark] JSON yazildi: {json_output}")
    print(f"[tool-build-benchmark] Markdown yazildi: {md_output}")

    if args.fail_on_error and not report.overall_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()