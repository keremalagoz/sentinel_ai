"""Legacy Bridge Tests — _v2_to_response, process_with_session, ask_ai_with_session_compat

Covers the UI → Compat → ToolCommand path that was untested (test blind spot).

Finding references:
    - schemas_legacy.ALLOWED_TOOLS whitelist vs execution tool executables
    - orchestrator._v2_to_response model_construct bypass
    - backend_gateway.ask_ai_with_session_compat roundtrip
"""

import uuid
from typing import Dict, Any, List

import pytest

from src.ai.schemas import (
    FinalCommand,
    IntentType,
    Intent,
    RiskLevel,
)
from src.ai.schemas_legacy import AIResponse, ToolCommand, ALLOWED_TOOLS
from src.ai.orchestrator import AIOrchestrator
from src.ai.tool_registry import TOOL_REGISTRY, get_execution_tool_id
from src.application.backend_gateway import BackendGateway


# =============================================================================
# Helpers
# =============================================================================


class _StubResolver:
    """Deterministic intent resolver for testing (no LLM required)."""

    def __init__(self, intent_type: IntentType = IntentType.PORT_SCAN, target: str = "10.0.0.1"):
        self._intent_type = intent_type
        self._target = target

    def resolve(self, user_input: str, target_hint=None) -> Intent:
        return Intent(
            intent_type=self._intent_type,
            target=self._target,
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )


def _make_v2_result(
    executable: str,
    arguments: List[str],
    requires_root: bool = False,
    risk_level: RiskLevel = RiskLevel.LOW,
    explanation: str = "test",
) -> Dict[str, Any]:
    """Build a mock process_v2 result dict."""
    return {
        "success": True,
        "command": FinalCommand(
            executable=executable,
            arguments=arguments,
            requires_root=requires_root,
            risk_level=risk_level,
            explanation=explanation,
        ),
        "secondary_commands": [],
        "message": f"Command ready: {executable}",
        "intent": None,
        "needs_clarification": False,
        "session_id": None,
        "requires_approval": True,
        "agent_observation": "action_suggested",
    }


# =============================================================================
# A) _v2_to_response — core bridge function
# =============================================================================


class TestV2ToResponse:
    """Verify _v2_to_response converts every execution tool executable without error."""

    @pytest.mark.parametrize(
        "executable,arguments",
        [
            ("nmap", ["-sn", "192.168.1.0/24"]),
            ("openssl", ["s_client", "-connect", "example.com:443", "-showcerts"]),
            ("gobuster", ["dir", "-u", "http://example.com", "-w", "/tmp/wordlist.txt"]),
            ("nikto", ["-host", "http://example.com"]),
            ("hydra", ["-l", "admin", "-P", "/tmp/passwords.txt", "ssh://10.0.0.1"]),
            ("nslookup", ["example.com"]),
            ("curl", ["-sI", "http://example.com"]),
            ("sqlmap", ["--batch", "-u", "http://example.com/page?id=1"]),
        ],
        ids=["nmap", "openssl", "gobuster", "nikto", "hydra", "nslookup", "curl", "sqlmap"],
    )
    def test_standard_tools(self, executable: str, arguments: list):
        v2 = _make_v2_result(executable, arguments)
        resp = AIOrchestrator._v2_to_response(v2)

        assert isinstance(resp, AIResponse)
        assert resp.command is not None
        assert resp.command.tool == executable
        assert resp.command.arguments == arguments

    def test_shell_wrapper_tool(self):
        """WebAppScanTool emits shell wrappers (powershell.exe / bash)."""
        long_script = (
            'URL="$1"; HEADERS=$(curl -sI -m 30 "$URL" 2>&1); '
            'echo "$HEADERS" | grep -i "^Server:" | sed "s/^/SERVER: /"; '
            'echo "$HEADERS" | grep -i "^X-Powered-By:" | sed "s/^/POWERED-BY: /";'
        )
        v2 = _make_v2_result(
            executable="bash",
            arguments=["-c", long_script, "--", "http://example.com"],
        )
        resp = AIOrchestrator._v2_to_response(v2)

        assert isinstance(resp, AIResponse)
        assert resp.command is not None
        assert resp.command.tool == "bash"
        assert long_script in resp.command.arguments

    def test_no_command(self):
        """v2 result with no command should return AIResponse with command=None."""
        v2 = {
            "command": None,
            "message": "No target specified",
            "needs_clarification": True,
        }
        resp = AIOrchestrator._v2_to_response(v2)

        assert isinstance(resp, AIResponse)
        assert resp.command is None
        assert resp.needs_clarification is True

    def test_preserves_risk_level(self):
        v2 = _make_v2_result("nmap", ["-O", "10.0.0.1"], True, RiskLevel.HIGH, "OS detection")
        resp = AIOrchestrator._v2_to_response(v2)

        assert resp.command.risk_level == RiskLevel.HIGH
        assert resp.command.requires_root is True
        assert resp.command.explanation == "OS detection"

    def test_preserves_message(self):
        v2 = _make_v2_result("nmap", ["-sn", "10.0.0.0/24"])
        v2["message"] = "Komut hazır: nmap -sn 10.0.0.0/24"
        resp = AIOrchestrator._v2_to_response(v2)

        assert "nmap" in resp.message


# =============================================================================
# B) process_with_session — orchestrator session-aware legacy path
# =============================================================================


class TestProcessWithSession:
    """Verify process_with_session returns AIResponse (not dict)."""

    def test_returns_ai_response_type(self):
        orch = AIOrchestrator(model="qwen2.5:3b")
        orch._intent_resolver = _StubResolver()
        orch._hierarchical_resolver = None

        session_id = f"test_{uuid.uuid4().hex[:8]}"
        result = orch.process_with_session("10.0.0.1 port taramasi yap", session_id=session_id)

        assert isinstance(result, AIResponse)
        assert result.command is not None
        assert result.message  # must have a message

    def test_session_passes_through(self):
        orch = AIOrchestrator(model="qwen2.5:3b")
        orch._intent_resolver = _StubResolver()
        orch._hierarchical_resolver = None

        session_id = f"test_{uuid.uuid4().hex[:8]}"
        # Two calls with same session — no crash
        r1 = orch.process_with_session("scan", session_id=session_id)
        r2 = orch.process_with_session("scan deeper", session_id=session_id)

        assert isinstance(r1, AIResponse)
        assert isinstance(r2, AIResponse)


# =============================================================================
# C) BackendGateway.ask_ai_with_session_compat — full integration
# =============================================================================


class TestGatewayCompat:
    """Verify ask_ai_with_session_compat returns AIResponse type."""

    def test_compat_returns_ai_response(self):
        gw = BackendGateway(model="qwen2.5:3b")
        gw._orchestrator._intent_resolver = _StubResolver()
        gw._orchestrator._hierarchical_resolver = None

        session_id = gw._orchestrator.create_session()
        result = gw.ask_ai_with_session_compat("10.0.0.1 port taramasi", session_id=session_id)

        assert isinstance(result, AIResponse)
        assert result.command is not None
        assert isinstance(result.command.tool, str)

    def test_compat_ssl_scan_tool(self):
        """SSL scan produces openssl — must not crash through compat layer."""
        gw = BackendGateway(model="qwen2.5:3b")
        gw._orchestrator._intent_resolver = _StubResolver(
            intent_type=IntentType.SSL_SCAN,
            target="example.com",
        )
        gw._orchestrator._hierarchical_resolver = None

        session_id = gw._orchestrator.create_session()
        result = gw.ask_ai_with_session_compat("example.com SSL analiz et", session_id=session_id)

        assert isinstance(result, AIResponse)
        assert result.command is not None
        # SSL scan execution tool produces openssl, not nmap
        assert result.command.tool == "openssl"


# =============================================================================
# D) Structural consistency — ALLOWED_TOOLS covers TOOL_REGISTRY
# =============================================================================


class TestWhitelistConsistency:
    """Ensure ALLOWED_TOOLS in schemas_legacy covers all tools in TOOL_REGISTRY."""

    def test_all_registry_tools_in_allowed_tools(self):
        """Every non-empty tool in TOOL_REGISTRY should be in ALLOWED_TOOLS."""
        missing = []
        for intent_type, tool_def in TOOL_REGISTRY.items():
            if tool_def.tool and tool_def.tool not in ALLOWED_TOOLS:
                missing.append(f"{intent_type.value}: tool={tool_def.tool}")

        assert not missing, (
            f"TOOL_REGISTRY tools not in ALLOWED_TOOLS: {missing}. "
            f"Update schemas_legacy.ALLOWED_TOOLS."
        )

    def test_openssl_in_allowed_tools(self):
        """openssl must be in ALLOWED_TOOLS (execution tool for SSL_SCAN)."""
        assert "openssl" in ALLOWED_TOOLS

    def test_sslscan_in_allowed_tools(self):
        """sslscan must be in ALLOWED_TOOLS (BackendGateway accepts it)."""
        assert "sslscan" in ALLOWED_TOOLS
