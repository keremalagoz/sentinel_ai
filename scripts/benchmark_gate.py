#!/usr/bin/env python3
"""Sprint 3.7 benchmark regression gate.

Runs `scripts/auto_benchmark.py` and fails with non-zero exit code when
acceptance gates do not pass.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint 3.7 benchmark gate runner")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--category-model", default=None)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--min-accuracy", type=float, default=85.0)
    parser.add_argument("--max-avg-latency", type=float, default=2000.0)
    parser.add_argument("--output", default="temp/benchmark_gate_report.json")
    parser.add_argument("--markdown", default="temp/benchmark_gate_report.md")
    args = parser.parse_args()

    output_path = (PROJECT_ROOT / args.output).resolve()
    markdown_path = (PROJECT_ROOT / args.markdown).resolve()

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "auto_benchmark.py"),
        "--model",
        args.model,
        "--runs",
        str(args.runs),
        "--warmup",
        str(args.warmup),
        "--min-accuracy",
        str(args.min_accuracy),
        "--max-avg-latency",
        str(args.max_avg_latency),
        "--output",
        str(output_path),
        "--markdown",
        str(markdown_path),
    ]

    if args.category_model:
        cmd.extend(["--category-model", args.category_model])

    completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if completed.returncode != 0:
        return completed.returncode

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    gates = payload.get("hierarchical", {}).get("gates", {})

    overall = bool(gates.get("overall_pass", False))
    if not overall:
        print("[benchmark-gate] FAILED", file=sys.stderr)
        print(f"[benchmark-gate] gates={gates}", file=sys.stderr)
        return 1

    print("[benchmark-gate] PASSED")
    print(f"[benchmark-gate] report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
