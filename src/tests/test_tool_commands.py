"""Sprint 3.5 - Comprehensive tool command tests."""

from __future__ import annotations

from typing import Callable, Iterator

import pytest

from src.ai.orchestrator import AIOrchestrator
from src.ai.schemas import Intent, IntentType
from src.ai.tool_registry import build_execution_kwargs, get_execution_tool_id, _EXECUTION_REGISTRY, get_missing_required_params
from src.core.sentinel_coordinator import SentinelCoordinator
from src.core.platform_utils import get_shell
from src.core.tool_base import (
    BaseTool,
    DnsLookupTool,
    GobusterDirTool,
    HydraHttpTool,
    HydraSshTool,
    NmapOsDetectionTool,
    NmapPingSweepTool,
    NmapPortScanTool,
    NmapServiceDetectionTool,
    NmapVulnScanTool,
    PingTool,
    SqlmapScanTool,
    SslScanTool,
    SubdomainEnumTool,
    WebAppScanTool,
    WhoisLookupTool,
)


class _DummyTool(BaseTool):
    def __init__(self):
        super().__init__("dummy", timeout=10)

    def build_command(self, **kwargs):
        return ["echo", "ok"]


@pytest.mark.parametrize(
    "builder, expected_program",
    [
        (lambda: PingTool().build_command(target="127.0.0.1"), "ping"),
        (lambda: NmapPingSweepTool().build_command(target="192.168.1.0/24"), "nmap"),
        (lambda: NmapPortScanTool().build_command(target="192.168.1.10"), "nmap"),
        (lambda: NmapServiceDetectionTool().build_command(target="192.168.1.10"), "nmap"),
        (lambda: NmapVulnScanTool().build_command(target="192.168.1.10"), "nmap"),
        (lambda: NmapOsDetectionTool().build_command(target="192.168.1.10"), "nmap"),
        (lambda: DnsLookupTool().build_command(domain="example.com"), "nslookup"),
        (lambda: SslScanTool().build_command(target="example.com"), "openssl"),
        (lambda: GobusterDirTool().build_command(url="http://example.com"), "gobuster"),
        (lambda: SubdomainEnumTool().build_command(domain="example.com"), "bash"),
        (lambda: WebAppScanTool().build_command(url="http://example.com"), get_shell()),
        (lambda: WhoisLookupTool().build_command(target="example.com"), "whois"),
        (
            lambda: HydraSshTool().build_command(
                target="10.0.0.5",
                username="admin",
                wordlist="/tmp/words.txt",
            ),
            "hydra",
        ),
        (
            lambda: HydraHttpTool().build_command(
                target="10.0.0.6",
                username="admin",
                wordlist="/tmp/words.txt",
                form_path="/login",
                form_params="user=^USER^&pass=^PASS^",
                fail_string="invalid",
            ),
            "hydra",
        ),
        (
            lambda: SqlmapScanTool().build_command(url="http://example.com/item.php?id=1"),
            "sqlmap",
        ),
    ],
)
def test_each_tool_returns_command_list(builder: Callable[[], list[str]], expected_program: str):
    cmd = builder()
    assert isinstance(cmd, list)
    assert all(isinstance(part, str) for part in cmd)
    assert cmd[0] == expected_program


@pytest.mark.parametrize(
    "builder, expected_tokens",
    [
        (
            lambda: PingTool().build_command(
                target="127.0.0.1", count=5, timeout=3, packet_size=64
            ),
            ["-W", "3", "-s", "64", "127.0.0.1"],
        ),
        (
            lambda: NmapPingSweepTool().build_command(
                target="192.168.1.0/24", timing=3, exclude="192.168.1.1", no_dns=True
            ),
            ["-sn", "-T3", "--exclude", "192.168.1.1", "-n", "192.168.1.0/24"],
        ),
        (
            lambda: NmapPortScanTool().build_command(
                target="192.168.1.10",
                scan_type="sU",
                top_ports=200,
                timing=4,
                no_dns=True,
                verbose=True,
            ),
            ["-sU", "--top-ports", "200", "-T4", "-n", "-v", "192.168.1.10"],
        ),
        (
            lambda: NmapServiceDetectionTool().build_command(
                target="192.168.1.10", version_intensity=7, version_mode="all", timing=2, no_ping=True, verbose=True
            ),
            ["-sV", "--version-intensity", "7", "--version-all", "-T2", "-Pn", "-v", "192.168.1.10"],
        ),
        (
            lambda: NmapVulnScanTool().build_command(
                target="192.168.1.10", scripts="vuln,http-vuln*", script_args="unsafe=0", timing=5, no_ping=True, verbose=True
            ),
            ["--script", "vuln,http-vuln*", "--script-args", "unsafe=0", "-T5", "-Pn", "-v", "192.168.1.10"],
        ),
        (
            lambda: NmapOsDetectionTool().build_command(
                target="192.168.1.10", top_ports=50, timing=1, osscan_guess=True, service_detection=True, no_ping=True, verbose=True
            ),
            ["-O", "-sV", "--osscan-guess", "--top-ports", "50", "-T1", "-Pn", "-v", "192.168.1.10"],
        ),
        (
            lambda: DnsLookupTool().build_command(
                domain="example.com", record_type="mx", dns_server="1.1.1.1"
            ),
            ["-type=MX", "example.com", "1.1.1.1"],
        ),
        (
            lambda: SslScanTool().build_command(
                target="example.com", port=8443, servername="example.com", tls_version="1.2", starttls="smtp"
            ),
            ["-connect", "example.com:8443", "-servername", "example.com", "-tls1_2", "-starttls", "smtp"],
        ),
        (
            lambda: GobusterDirTool().build_command(
                url="https://example.com",
                threads=32,
                status_codes="200,301,302",
                no_tls_validation=True,
                follow_redirect=True,
            ),
            ["dir", "-t", "32", "-s", "200,301,302", "-k", "-r", "-q"],
        ),
        (
            lambda: WhoisLookupTool().build_command(target="8.8.8.8"),
            ["8.8.8.8"],
        ),
        (
            lambda: HydraSshTool().build_command(
                target="10.0.0.5", username="admin", wordlist="/tmp/w.txt", port=2222, threads=8, verbose=True
            ),
            ["-l", "admin", "-P", "/tmp/w.txt", "-t", "8", "-s", "2222", "-V", "ssh://10.0.0.5"],
        ),
        (
            lambda: HydraHttpTool().build_command(
                target="10.0.0.6",
                username="admin",
                wordlist="/tmp/w.txt",
                form_path="/login",
                form_params="user=^USER^&pass=^PASS^",
                fail_string="invalid",
                method="https-form-post",
                port=443,
            ),
            ["https-form-post", "/login:user=^USER^&pass=^PASS^:invalid"],
        ),
        (
            lambda: SqlmapScanTool().build_command(
                url="http://example.com/item.php?id=1", level=5, risk=3, forms=True, dbs=True, threads=5
            ),
            ["--batch", "--forms", "--level", "5", "--risk", "3", "--dbs", "--threads", "5"],
        ),
    ],
)
def test_optional_parameters_are_encoded(builder: Callable[[], list[str]], expected_tokens: list[str]):
    cmd = builder()
    joined = " ".join(cmd)
    for token in expected_tokens:
        assert token in joined


@pytest.mark.parametrize(
    "builder",
    [
        lambda: PingTool().build_command(target=""),
        lambda: NmapPingSweepTool().build_command(target=""),
        lambda: NmapPortScanTool().build_command(target=""),
        lambda: NmapServiceDetectionTool().build_command(target=""),
        lambda: NmapVulnScanTool().build_command(target=""),
        lambda: NmapOsDetectionTool().build_command(target=""),
        lambda: DnsLookupTool().build_command(domain=""),
        lambda: SslScanTool().build_command(target=""),
        lambda: GobusterDirTool().build_command(url=""),
        lambda: SubdomainEnumTool().build_command(domain=""),
        lambda: WebAppScanTool().build_command(url=""),
        lambda: WhoisLookupTool().build_command(target=""),
        lambda: HydraSshTool().build_command(target="", username="admin", wordlist="/tmp/w.txt"),
        lambda: HydraHttpTool().build_command(
            target="",
            username="admin",
            wordlist="/tmp/w.txt",
            form_path="/login",
            form_params="u=^USER^&p=^PASS^",
            fail_string="invalid",
        ),
        lambda: SqlmapScanTool().build_command(url=""),
    ],
)
def test_empty_targets_raise_value_error(builder: Callable[[], list[str]]):
    with pytest.raises(ValueError):
        builder()


@pytest.mark.parametrize(
    "payload",
    [
        "127.0.0.1;cat /etc/passwd",
        "example.com&&id",
        "target|whoami",
        "10.0.0.1$(id)",
        "host`id`",
        "name{bad}",
        "line\nnext",
    ],
)
def test_validate_target_rejects_shell_metacharacters(payload: str):
    tool = _DummyTool()
    with pytest.raises(ValueError):
        tool.validate_target(payload)


@pytest.mark.parametrize(
    "builder",
    [
        lambda: NmapPingSweepTool().build_command(target="192.168.1.0/24", timing=6),
        lambda: NmapPortScanTool().build_command(target="192.168.1.10", scan_type="sZ"),
        lambda: NmapServiceDetectionTool().build_command(target="192.168.1.10", version_intensity=10),
        lambda: NmapVulnScanTool().build_command(target="192.168.1.10", scripts=""),
        lambda: DnsLookupTool().build_command(domain="example.com", record_type="BAD"),
        lambda: SslScanTool().build_command(target="example.com", tls_version="1.1"),
        lambda: GobusterDirTool().build_command(url="example.com"),
        lambda: HydraSshTool().build_command(target="10.0.0.5", username="admin", wordlist="/tmp/w.txt", threads=0),
        lambda: HydraHttpTool().build_command(
            target="10.0.0.6",
            username="admin",
            wordlist="/tmp/w.txt",
            form_path="/login",
            form_params="u=^USER^&p=^PASS^",
            fail_string="invalid",
            method="ftp-form-post",
        ),
        lambda: SqlmapScanTool().build_command(url="http://example.com", level=0),
    ],
)
def test_invalid_parameters_raise_value_error(builder: Callable[[], list[str]]):
    with pytest.raises(ValueError):
        builder()


@pytest.mark.parametrize(
    "intent, target, params, expected_tool_id",
    [
        (IntentType.OS_DETECTION, "192.168.1.10", {"ports": "22,80", "timing": 3}, "nmap_os_detection"),
        (IntentType.WHOIS_LOOKUP, "example.com", {}, "whois_lookup"),
        (
            IntentType.BRUTE_FORCE_SSH,
            "10.0.0.5",
            {"username": "admin", "wordlist": "/tmp/w.txt", "threads": 4},
            "hydra_ssh",
        ),
        (
            IntentType.BRUTE_FORCE_HTTP,
            "10.0.0.6",
            {
                "username": "admin",
                "wordlist": "/tmp/w.txt",
                "form_path": "/login",
                "form_params": "u=^USER^&p=^PASS^",
                "fail_string": "invalid",
            },
            "hydra_http",
        ),
        (
            IntentType.SQL_INJECTION,
            "http://example.com/item.php?id=1",
            {"level": 3, "risk": 2, "threads": 3},
            "sqlmap_scan",
        ),
    ],
)
def test_execution_registry_maps_new_intents(intent: IntentType, target: str, params: dict, expected_tool_id: str):
    assert get_execution_tool_id(intent) == expected_tool_id
    kwargs = build_execution_kwargs(intent, target, params)
    assert kwargs is not None


@pytest.fixture
def coordinator() -> Iterator[SentinelCoordinator]:
    c = SentinelCoordinator(db_path=":memory:")
    yield c
    c.cleanup()


def test_orchestrator_prefers_execution_tool_command_path(coordinator: SentinelCoordinator):
    orchestrator = AIOrchestrator(model="qwen2.5:3b", coordinator=coordinator)
    orchestrator._intent_resolver.resolve = lambda _user_input, _target: Intent(
        intent_type=IntentType.WEB_VULN_SCAN,
        target="http://example.com",
        params={},
        needs_clarification=False,
        clarification_reason=None,
        confidence=0.99,
    )

    result = orchestrator.process_v2("test", target="http://example.com")

    assert result["success"] is True
    assert result["command"] is not None
    assert result["command"].executable != "nikto"


def test_orchestrator_falls_back_without_coordinator():
    orchestrator = AIOrchestrator(model="qwen2.5:3b", coordinator=None)
    orchestrator._intent_resolver.resolve = lambda _user_input, _target: Intent(
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.10",
        params={"ports": "80,443"},
        needs_clarification=False,
        clarification_reason=None,
        confidence=0.99,
    )

    result = orchestrator.process_v2("test", target="192.168.1.10")

    assert result["success"] is True
    assert result["command"] is not None
    assert result["command"].executable == "nmap"


def test_orchestrator_adds_secondary_commands_for_compound_prompt(coordinator: SentinelCoordinator):
    orchestrator = AIOrchestrator(model="qwen2.5:3b", coordinator=coordinator)
    orchestrator._intent_resolver.resolve = lambda _user_input, _target: Intent(
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"top_ports": 20},
        needs_clarification=False,
        clarification_reason=None,
        confidence=0.99,
    )

    result = orchestrator.process_v2("10.0.0.1 port tara ve dns sorgu yap")
    assert result["success"] is True
    assert result["command"] is not None
    assert "secondary_commands" in result
    assert isinstance(result["secondary_commands"], list)





# =============================================================================
# E2E PIPELINE TESTS: Intent -> build_execution_kwargs -> build_command
# =============================================================================

class TestE2EPipelineCommands:
    """Intent → param mapping → build_command tam akış testleri.

    Bu testler, LLM parametreleri olmadan (varsayılan) ve LLM parametreleri ile
    üretilen komutların doğruluğunu kontrol eder.
    """

    @staticmethod
    def _build_via_pipeline(intent_type: IntentType, target: str, params: dict) -> list[str]:
        """Simulate the preferred execution-tool path."""
        from src.core.tool_base import TOOL_CLASS_MAP
        exec_tool_id = get_execution_tool_id(intent_type)
        assert exec_tool_id is not None, f"No execution tool for {intent_type}"
        tool_cls = TOOL_CLASS_MAP.get(exec_tool_id)
        assert tool_cls is not None, f"No tool class for {exec_tool_id}"
        tool_instance = tool_cls()
        kwargs = build_execution_kwargs(intent_type, target, params)
        assert kwargs is not None
        return tool_instance.build_command(**kwargs)

    def test_port_scan_default_params(self):
        """Kullanıcı sadece 'port tara' derse: varsayılan -sT, -p 1-1000, -sV YOK."""
        cmd = self._build_via_pipeline(IntentType.PORT_SCAN, "192.168.1.10", {})
        assert cmd[0] == "nmap"
        assert "-sT" in cmd
        assert "-sV" not in cmd, "Varsayılan port taramada -sV olmamalı"
        assert "--top-ports" not in cmd
        assert "-p" in cmd
        assert "1-1000" in cmd

    def test_port_scan_with_service_detection(self):
        """Kullanıcı servis tespiti isterse: -sV eklenmeli."""
        cmd = self._build_via_pipeline(
            IntentType.PORT_SCAN, "10.0.0.1", {"service_detection": True}
        )
        assert "-sV" in cmd
        assert "-sT" in cmd

    def test_port_scan_with_top_ports(self):
        """Kullanıcı top_ports belirtirse: --top-ports var, -p YOK."""
        cmd = self._build_via_pipeline(
            IntentType.PORT_SCAN, "10.0.0.1", {"top_ports": 100}
        )
        assert "--top-ports" in cmd
        assert "100" in cmd
        assert "-p" not in cmd, "--top-ports ile -p birlikte kullanılmamalı"

    def test_port_scan_with_no_ping(self):
        """No-ping parametresi -Pn olarak yansimali."""
        cmd = self._build_via_pipeline(
            IntentType.PORT_SCAN, "10.0.0.1", {"no_ping": True}
        )
        assert "-Pn" in cmd

    def test_port_scan_aggressive_mode(self):
        """Aggressive modda -A olmali ve scan_type flag'i olmamali."""
        cmd = self._build_via_pipeline(
            IntentType.PORT_SCAN, "10.0.0.1", {"aggressive": True}
        )
        assert "-A" in cmd
        assert "-sT" not in cmd
        assert "-sS" not in cmd

    def test_port_scan_aggressive_with_no_ping(self):
        """Aggressive + no_ping birlikte calismali."""
        cmd = self._build_via_pipeline(
            IntentType.PORT_SCAN, "10.0.0.1", {"aggressive": True, "no_ping": True}
        )
        assert "-A" in cmd
        assert "-Pn" in cmd

    def test_port_scan_syn_scan_type(self):
        """Kullanıcı SYN scan isterse: -sS olmalı."""
        cmd = self._build_via_pipeline(
            IntentType.PORT_SCAN, "10.0.0.1", {"scan_type": "sS"}
        )
        assert "-sS" in cmd
        assert "-sT" not in cmd

    def test_service_detection_default(self):
        """Servis tespiti varsayılan: -sV, intensity 5."""
        cmd = self._build_via_pipeline(IntentType.SERVICE_DETECTION, "10.0.0.1", {})
        assert "-sV" in cmd
        assert "--version-intensity" in cmd

    def test_os_detection_default(self):
        """OS tespiti varsayılan: -O."""
        cmd = self._build_via_pipeline(IntentType.OS_DETECTION, "10.0.0.1", {})
        assert "-O" in cmd

    def test_vuln_scan_default(self):
        """Zafiyet taraması varsayılan: --script vuln."""
        cmd = self._build_via_pipeline(IntentType.VULN_SCAN, "10.0.0.1", {})
        assert "--script" in cmd
        assert "vuln" in cmd

    def test_dns_lookup_default(self):
        """DNS sorgusu varsayılan."""
        cmd = self._build_via_pipeline(IntentType.DNS_LOOKUP, "example.com", {})
        assert cmd[0] == "nslookup"
        assert "example.com" in cmd

    def test_host_discovery_default(self):
        """Host discovery varsayılan: -sn."""
        cmd = self._build_via_pipeline(IntentType.HOST_DISCOVERY, "192.168.1.0/24", {})
        assert "-sn" in cmd

    def test_web_dir_enum_default(self):
        """Web dizin taraması varsayılan."""
        cmd = self._build_via_pipeline(IntentType.WEB_DIR_ENUM, "http://example.com", {})
        assert cmd[0] == "gobuster"
        assert "dir" in cmd

    def test_brute_force_ssh_pipeline(self):
        """SSH brute force: kullanıcı parametreleri doğru aktarılmalı."""
        cmd = self._build_via_pipeline(
            IntentType.BRUTE_FORCE_SSH,
            "10.0.0.5",
            {"username": "admin", "wordlist": "/tmp/w.txt"},
        )
        assert cmd[0] == "hydra"
        assert "-l" in cmd
        assert "admin" in cmd

    def test_sql_injection_pipeline(self):
        """SQL injection: --batch varsayılan olmalı."""
        cmd = self._build_via_pipeline(
            IntentType.SQL_INJECTION,
            "http://example.com/item.php?id=1",
            {},
        )
        assert cmd[0] == "sqlmap"
        assert "--batch" in cmd

    def test_no_extra_flags_when_params_empty(self):
        """Boş params ile gereksiz flag eklenmemeli (LLM hallucination koruması)."""
        cmd = self._build_via_pipeline(IntentType.PORT_SCAN, "10.0.0.1", {})
        joined = " ".join(cmd)
        assert "-sV" not in joined, "Boş params ile -sV eklenmemeli"
        assert "--top-ports" not in joined, "Boş params ile --top-ports eklenmemeli"
        assert "-n" not in joined, "Boş params ile -n eklenmemeli"
        assert "-v" not in joined, "Boş params ile -v eklenmemeli"
        assert "-T" not in joined, "Boş params ile -T eklenmemeli"


# =============================================================================
# REGISTRY METADATA CONSISTENCY TESTS
# =============================================================================

class TestRegistryConsistency:
    """TOOL_REGISTRY metadata ile gerçek tool davranışının tutarlılığını kontrol eder."""

    def test_port_scan_registry_matches_tool_defaults(self):
        """PORT_SCAN registry metadata gerçek tool varsayılanlarıyla eşleşmeli."""
        from src.ai.tool_registry import TOOL_REGISTRY, get_execution_tool_id
        from src.ai.schemas import IntentType

        tool_def = TOOL_REGISTRY[IntentType.PORT_SCAN]
        # Tool defaults to -sT (TCP Connect), not -sS (SYN)
        assert "-sS" not in tool_def.base_args, \
            "Registry -sS diyor ama tool varsayılanı -sT"
        assert tool_def.requires_root is False, \
            "TCP Connect (-sT) root gerektirmez"

    def test_all_execution_intents_have_tool_defs(self):
        """Tüm execution registry intent'lerinin ToolDef'i olmalı."""
        from src.ai.tool_registry import _EXECUTION_REGISTRY, TOOL_REGISTRY

        for intent_type in _EXECUTION_REGISTRY:
            assert intent_type in TOOL_REGISTRY, \
                f"{intent_type.value} execution registry'de var ama TOOL_REGISTRY'de yok"
            assert TOOL_REGISTRY[intent_type].tool, \
                f"{intent_type.value} için tool boş"

    def test_execution_registry_param_maps_are_valid(self):
        """Param map key'leri build_command()'da parametre olarak bulunmalı."""
        import inspect
        from src.core.tool_base import TOOL_CLASS_MAP

        for intent_type, mapping in _EXECUTION_REGISTRY.items():
            tool_id = mapping["tool_id"]
            param_map = mapping.get("param_map", {})
            tool_cls = TOOL_CLASS_MAP.get(tool_id)
            if tool_cls is None:
                continue
            sig = inspect.signature(tool_cls.build_command)
            param_names = set(sig.parameters.keys()) - {"self", "kwargs"}
            target_arg = mapping.get("target_arg")
            if target_arg:
                param_names.add(target_arg)

            for _param_key, tool_arg in param_map.items():
                assert tool_arg in param_names or "kwargs" in {
                    p.name for p in sig.parameters.values()
                    if p.kind == inspect.Parameter.VAR_KEYWORD
                }, (
                    f"{intent_type.value}: param_map '{tool_arg}' "
                    f"build_command() parametrelerinde yok: {sorted(param_names)}"
                )


# =============================================================================
# PORTS VALIDATION TESTS
# =============================================================================

class TestPortsValidation:
    """ports parametresinin geçersiz değerleri reddettiğini doğrular."""

    @pytest.mark.parametrize("invalid_ports", [
        ";rm -rf /",
        "80;id",
        "80|whoami",
        "$(cat /etc/passwd)",
        "80`id`",
        "abc",
        "80,,443",
        "",
        "0-1000",
        "1-70000",
        "1000-500",
    ])
    def test_nmap_port_scan_rejects_invalid_ports(self, invalid_ports):
        with pytest.raises(ValueError):
            NmapPortScanTool().build_command(target="192.168.1.10", ports=invalid_ports)

    @pytest.mark.parametrize("valid_ports", [
        "80",
        "80,443",
        "1-1000",
        "22,80,443,8080",
        "1-65535",
    ])
    def test_nmap_port_scan_accepts_valid_ports(self, valid_ports):
        cmd = NmapPortScanTool().build_command(target="192.168.1.10", ports=valid_ports)
        assert "-p" in cmd
        assert valid_ports.replace(" ", "") in cmd

    @pytest.mark.parametrize("invalid_ports", [
        ";rm -rf /",
        "abc",
        "$(id)",
    ])
    def test_nmap_vuln_scan_rejects_invalid_ports(self, invalid_ports):
        with pytest.raises(ValueError):
            NmapVulnScanTool().build_command(target="192.168.1.10", ports=invalid_ports)

    @pytest.mark.parametrize("invalid_ports", [
        ";rm -rf /",
        "abc",
        "$(id)",
    ])
    def test_nmap_service_detection_rejects_invalid_ports(self, invalid_ports):
        with pytest.raises(ValueError):
            NmapServiceDetectionTool().build_command(target="192.168.1.10", ports=invalid_ports)

    @pytest.mark.parametrize("invalid_ports", [
        ";rm -rf /",
        "abc",
        "$(id)",
    ])
    def test_nmap_os_detection_rejects_invalid_ports(self, invalid_ports):
        with pytest.raises(ValueError):
            NmapOsDetectionTool().build_command(target="192.168.1.10", ports=invalid_ports)
