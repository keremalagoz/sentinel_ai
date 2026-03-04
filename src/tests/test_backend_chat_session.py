import uuid

from fastapi.testclient import TestClient

from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import Intent, IntentType
from src.application.api_server import app, _orchestrator


class DummyResolver:
    def __init__(self, target: str = "10.10.10.10"):
        self.target = target
        self.calls = []

    def resolve(self, user_input: str, target_hint=None) -> Intent:
        self.calls.append(user_input)
        return Intent(
            intent_type=IntentType.PORT_SCAN,
            target=self.target,
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )



def test_orchestrator_persists_session_and_enriches_context() -> None:
    orch = AIOrchestrator(model="qwen2.5:3b")
    dummy = DummyResolver()
    orch._intent_resolver = dummy
    orch._hierarchical_resolver = None

    session_id = f"test_sess_{uuid.uuid4().hex[:8]}"

    first = orch.process_v2("10.10.10.10 port taramasi yap", session_id=session_id)
    assert first["success"] is True
    assert first["session_id"] == session_id
    assert first["requires_approval"] is True

    second = orch.process_v2("simdi daha detayli tara", session_id=session_id)
    assert second["success"] is True
    assert len(dummy.calls) == 2
    assert "Sohbet baglami" in dummy.calls[1]
    assert "10.10.10.10 port taramasi yap" in dummy.calls[1]

    turns = orch.get_session_turns(session_id, limit=10)
    assert len(turns) >= 4



def test_api_chat_endpoints_backend_only() -> None:
    dummy = DummyResolver(target="192.168.56.10")
    _orchestrator._intent_resolver = dummy
    _orchestrator._hierarchical_resolver = None

    client = TestClient(app)

    create_resp = client.post("/api/chat/session", json={})
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    turn_resp = client.post(
        "/api/chat/turn",
        json={
            "session_id": session_id,
            "message": "hedefte port taramasi yap",
            "memory_turn_limit": 6,
        },
    )
    assert turn_resp.status_code == 200
    payload = turn_resp.json()
    assert payload["session_id"] == session_id
    assert payload["requires_approval"] is True
    assert payload["intent_type"] == IntentType.PORT_SCAN.value
    assert payload["command"] is not None

    history_resp = client.get(f"/api/chat/history/{session_id}?limit=10")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["success"] is True
    assert history["count"] >= 2
