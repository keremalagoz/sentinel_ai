from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import Intent, IntentType
from src.ai.tool_registry import build_execution_kwargs, build_tool_spec


class DummyResolver:
    def __init__(self, intent: Intent):
        self.intent = intent

    def resolve(self, user_input: str, target_hint=None) -> Intent:
        return self.intent


def test_build_tool_spec_applies_registry_defaults_for_sqlmap() -> None:
    spec = build_tool_spec(
        IntentType.SQL_INJECTION,
        target="http://example.com/login.php?id=1",
        params={},
    )

    assert spec is not None
    assert spec.tool == "sqlmap"
    assert spec.arguments == ["--batch", "--level", "3"]


def test_build_execution_kwargs_coerces_types_and_adds_http_prefix() -> None:
    kwargs = build_execution_kwargs(
        IntentType.SQL_INJECTION,
        target="example.com/login.php?id=1",
        params={"risk": "2", "threads": "4", "forms": "true"},
    )

    assert kwargs == {
        "url": "http://example.com/login.php?id=1",
        "level": 3,
        "risk": 2,
        "threads": 4,
        "forms": True,
    }


def test_orchestrator_builds_port_scan_command_from_execution_tool() -> None:
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = DummyResolver(
        Intent(
            intent_type=IntentType.PORT_SCAN,
            target="10.10.10.10",
            params={"ports": "22,443", "timing": 4},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.96,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2("hedefin portlarini tara")

    assert result["success"] is True
    assert result["requires_approval"] is True
    assert result["command"] is not None
    assert result["command"].executable == "nmap"
    assert result["command"].arguments == ["-sT", "-p", "22,443", "-T4", "10.10.10.10"]


def test_orchestrator_marks_os_detection_as_high_risk_when_root_flags_exist() -> None:
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = DummyResolver(
        Intent(
            intent_type=IntentType.OS_DETECTION,
            target="192.168.1.15",
            params={"ports": "22,80", "osscan_guess": True},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.9,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2("isletim sistemini tespit et")

    assert result["success"] is True
    assert result["command"] is not None
    assert result["command"].executable == "nmap"
    assert result["command"].requires_root is True
    assert result["command"].risk_level.value == "high"
    assert "-O" in result["command"].arguments
    assert "--osscan-guess" in result["command"].arguments
