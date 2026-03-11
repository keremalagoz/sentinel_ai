"""Sprint 3.5 layered test runner.

Usage examples:
    python scripts/run_sprint35_tests.py --stage smoke
    python scripts/run_sprint35_tests.py --stage focused
    python scripts/run_sprint35_tests.py --stage integration
    python scripts/run_sprint35_tests.py --stage full
    python scripts/run_sprint35_tests.py --stage perf
    python scripts/run_sprint35_tests.py --stage all
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Dict, List


def run_cmd(command: List[str], label: str) -> int:
    print(f"\n=== [{label}] {' '.join(command)}")
    completed = subprocess.run(command)
    print(f"=== [{label}] exit={completed.returncode}")
    return int(completed.returncode)


def build_stage_commands(python_exec: str, with_benchmark: bool = False) -> Dict[str, List[List[str]]]:
    perf_commands = [
        [python_exec, "-m", "pytest", "src/tests/test_optimizations.py", "-q"],
    ]
    if with_benchmark:
        perf_commands.append(
            [python_exec, "scripts/intent_benchmark.py", "--hierarchical", "--output", "benchmark_sprint35.json"]
        )

    return {
        "smoke": [
            [python_exec, "-m", "pytest", "src/tests/test_new_tools.py", "src/tests/test_registry_consistency.py", "-q"],
        ],
        "focused": [
            [python_exec, "-m", "pytest", "src/tests/test_tool_commands.py", "-q"],
            [python_exec, "-m", "pytest", "src/tests/test_new_tools.py", "src/tests/test_registry_consistency.py", "-q"],
        ],
        "integration": [
            [python_exec, "-m", "pytest", "src/tests/test_ui_backend_boundary.py", "src/tests/test_integration.py", "-q"],
            [python_exec, "-m", "pytest", "src/tests/test_backend_chat_session.py", "-q"],
        ],
        "full": [
            [python_exec, "-m", "pytest", "src/tests/test_tool_commands.py", "-q"],
            [python_exec, "-m", "pytest", "src/tests/test_new_tools.py", "src/tests/test_registry_consistency.py", "-q"],
            [python_exec, "-m", "pytest", "src/tests/test_ui_backend_boundary.py", "src/tests/test_integration.py", "-q"],
            [python_exec, "-m", "pytest", "src/tests/test_backend_chat_session.py", "-q"],
            [python_exec, "-m", "pytest", "src/tests/test_optimizations.py", "-q"],
        ],
        "perf": perf_commands,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sprint 3.5 layered tests")
    parser.add_argument(
        "--stage",
        choices=["smoke", "focused", "integration", "full", "perf", "all"],
        default="all",
        help="Test stage to run",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable path (default: current interpreter)",
    )
    parser.add_argument(
        "--with-benchmark",
        action="store_true",
        help="Also run intent benchmark in perf stage",
    )
    args = parser.parse_args()

    python_exec = args.python
    stages = build_stage_commands(python_exec, with_benchmark=args.with_benchmark)

    selected = [args.stage] if args.stage != "all" else ["smoke", "focused", "integration", "perf"]

    failures = 0
    for stage in selected:
        for cmd in stages[stage]:
            failures += 1 if run_cmd(cmd, stage) != 0 else 0

    if failures:
        print(f"\nSprint 3.5 test run completed with {failures} failing command(s).")
        return 1

    print("\nSprint 3.5 test run completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
