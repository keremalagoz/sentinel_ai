from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import Intent, IntentType


class _DummyResolver:
    def __init__(self, intent: Intent):
        self.intent = intent

    def resolve(self, user_input: str, target_hint=None) -> Intent:
        return self.intent


def test_orchestrator_requests_clarification_for_bruteforce_ssh_without_credentials() -> None:
    orch = AIOrchestrator(model="qwen2.5:3b")
    orch._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.BRUTE_FORCE_SSH,
            target="10.0.0.5",
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orch._hierarchical_resolver = None

    result = orch.process_v2("ssh brute force yap")

    assert result["success"] is False
    assert result["needs_clarification"] is True
    assert "username" in result["message"]
    assert result["agent_observation"] == "clarification_required"


def test_orchestrator_requests_clarification_for_http_bruteforce_without_form_details() -> None:
    orch = AIOrchestrator(model="qwen2.5:3b")
    orch._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.BRUTE_FORCE_HTTP,
            target="http://example.com/login",
            params={"username": "admin", "passlist": "/tmp/words.txt"},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orch._hierarchical_resolver = None

    result = orch.process_v2("http brute force yap")

    assert result["success"] is False
    assert result["needs_clarification"] is True
    assert "form_path" in result["message"]


def test_orchestrator_requests_clarification_for_sql_injection_without_url_target() -> None:
    orch = AIOrchestrator(model="qwen2.5:3b")
    orch._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.SQL_INJECTION,
            target="example.com",
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orch._hierarchical_resolver = None

    result = orch.process_v2("sql injection testi yap")

    assert result["success"] is False
    assert result["needs_clarification"] is True
    assert "URL" in result["message"]


def test_orchestrator_allows_sql_injection_when_url_target_is_present() -> None:
    orch = AIOrchestrator(model="qwen2.5:3b")
    orch._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.SQL_INJECTION,
            target="http://example.com/login.php?id=1",
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orch._hierarchical_resolver = None

    result = orch.process_v2("sql injection testi yap")

    assert result["success"] is True
    assert result["needs_clarification"] is False
    assert result["command"] is not None
    assert result["command"].executable == "sqlmap"
    assert result["command"].arguments[:4] == ["--batch", "--level", "3", "-u"]
