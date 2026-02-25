"""P0 validation script.

Amaç:
- Queue/backpressure davranışını doğrulamak
- cancel_tool() ile kuyruk temizliğini doğrulamak
- IntentResolver timeout/retry akışını (mock ile) doğrulamak
- Orchestrator local-only servis durumunu doğrulamak

Kullanım:
    C:/Users/thega/Desktop/sentinel_root/.venv/Scripts/python.exe scripts/p0_validation.py

Opsiyonel:
    C:/Users/thega/Desktop/sentinel_root/.venv/Scripts/python.exe scripts/p0_validation.py --with-pytest
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ai.intent_resolver import IntentResolver
from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import IntentType
from src.core.sqlite_backend import SQLiteBackend
from src.core.tool_integration import ToolManager


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def test_queue_backpressure() -> None:
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(backend=backend, max_concurrent=1, max_queue_size=1)

    class DummyTool:
        def __init__(self):
            self.executions = 0
            self.cancelled = False

        def execute(self, callback=None, **kwargs):
            self.executions += 1

        def cancel(self):
            self.cancelled = True

    manager._tools["dummy"] = DummyTool()

    assert manager.execute_tool("dummy", target="127.0.0.1") is True
    assert manager.active_executions == 1
    assert manager.queued_executions == 0

    assert manager.execute_tool("dummy", target="127.0.0.2") is True
    assert manager.active_executions == 1
    assert manager.queued_executions == 1

    assert manager.execute_tool("dummy", target="127.0.0.3") is False
    assert manager.queued_executions == 1

    backend.close()
    _ok("Queue/backpressure davranışı doğrulandı")


def test_cancel_clears_queue() -> None:
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(backend=backend, max_concurrent=1, max_queue_size=10)

    class DummyTool:
        def __init__(self):
            self.cancelled = False

        def execute(self, callback=None, **kwargs):
            pass

        def cancel(self):
            self.cancelled = True

    dummy = DummyTool()
    manager._tools["dummy"] = dummy

    assert manager.execute_tool("dummy", target="127.0.0.1") is True
    assert manager.execute_tool("dummy", target="127.0.0.2") is True
    assert manager.queued_executions == 1

    assert manager.cancel_tool("dummy") is True
    assert dummy.cancelled is True
    assert manager.queued_executions == 0

    backend.close()
    _ok("cancel_tool kuyruk temizliği doğrulandı")


def _valid_intent_json(intent_type: str = "port_scan") -> str:
    return json.dumps(
        {
            "intent_type": intent_type,
            "target": "192.168.1.1",
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
        }
    )


def test_intent_resolver_retry_success() -> None:
    resolver = IntentResolver(model="whiterabbitneo", max_attempts=3, request_timeout=1)

    state = {"count": 0}

    def flaky_call(_messages):
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary error")
        return _valid_intent_json("port_scan")

    resolver._call_local = flaky_call  # type: ignore[attr-defined]

    intent = resolver.resolve("port tara", "192.168.1.1")
    assert state["count"] == 3
    assert intent.intent_type == IntentType.PORT_SCAN
    assert intent.needs_clarification is False
    _ok("IntentResolver retry-success akışı doğrulandı")


def test_intent_resolver_retry_exhausted() -> None:
    resolver = IntentResolver(model="whiterabbitneo", max_attempts=2, request_timeout=1)

    def always_fail(_messages):
        raise RuntimeError("permanent error")

    resolver._call_local = always_fail  # type: ignore[attr-defined]

    intent = resolver.resolve("port tara", "192.168.1.1")
    assert intent.intent_type == IntentType.UNKNOWN
    assert intent.needs_clarification is True
    assert "AI hatasi" in (intent.clarification_reason or "")
    _ok("IntentResolver retry-exhausted akışı doğrulandı")


def test_orchestrator_local_only_service_state() -> None:
    orch = AIOrchestrator(model="whiterabbitneo")
    local_ok, cloud_ok = orch.check_services()
    assert isinstance(local_ok, bool)
    assert cloud_ok is False
    _ok("Orchestrator local-only servis durumu doğrulandı")


def run_optional_pytest() -> None:
    cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m",
        "pytest",
        "-q",
    ]
    print("[INFO] Full pytest çalıştırılıyor...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    _ok("Full pytest tamamlandı")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P0 validation checks")
    parser.add_argument("--with-pytest", action="store_true", help="Full pytest -q da çalıştır")
    args = parser.parse_args()

    tests = [
        test_queue_backpressure,
        test_cancel_clears_queue,
        test_intent_resolver_retry_success,
        test_intent_resolver_retry_exhausted,
        test_orchestrator_local_only_service_state,
    ]

    failed = 0
    print("=" * 72)
    print("P0 VALIDATION SCRIPT")
    print("=" * 72)

    for t in tests:
        try:
            t()
        except Exception as exc:
            failed += 1
            _fail(f"{t.__name__}: {exc}")

    if args.with_pytest:
        try:
            run_optional_pytest()
        except Exception as exc:
            failed += 1
            _fail(f"full_pytest: {exc}")

    print("-" * 72)
    if failed == 0:
        _ok("Tüm P0 kontrolleri geçti")
        return 0

    _fail(f"{failed} kontrol başarısız")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
