"""Detailed tests for new tool layer.

Bu dosya smoke-style bool return testleri yerine,
spesifik ve assert tabanlı pytest testleri içerir.
"""

import pytest

from src.ai.schemas import IntentType
from src.ai.tool_registry import _EXECUTION_REGISTRY
from src.core.sentinel_coordinator import SentinelCoordinator
from src.core.tool_integration import ToolManager
from src.core.sqlite_backend import SQLiteBackend
from src.core.tool_base import (
    DnsLookupTool,
    GobusterDirTool,
    HydraHttpTool,
    HydraSshTool,
    NmapOsDetectionTool,
    NmapPortScanTool,
    NmapServiceDetectionTool,
    NmapVulnScanTool,
    SqlmapScanTool,
    SslScanTool,
    SubdomainEnumTool,
    WebAppScanTool,
    WhoisLookupTool,
)
from src.core.parser_framework import (
    DnsLookupParser,
    GobusterDirParser,
    HydraHttpParser,
    HydraSshParser,
    NmapOsDetectionParser,
    NmapServiceDetectionParser,
    NmapVulnScanParser,
    SqlmapScanParser,
    SslScanParser,
    SubdomainEnumParser,
    WebAppScanParser,
    WhoisLookupParser,
)


EXPECTED_TOOLS = {
    "ping",
    "nmap_ping_sweep",
    "nmap_port_scan",
    "nmap_service_detection",
    "nmap_vuln_scan",
    "dns_lookup",
    "ssl_scan",
    "gobuster_dir",
    "subdomain_enum",
    "web_app_scan",
    "nmap_os_detection",
    "whois_lookup",
    "hydra_ssh",
    "hydra_http",
    "sqlmap_scan",
}


@pytest.fixture
def coordinator():
    c = SentinelCoordinator(db_path=":memory:")
    yield c
    c.cleanup()


def test_registered_tools_exact_set(coordinator):
    """Coordinator beklenen tool setini birebir register etmeli."""
    registered = set(coordinator.get_available_tools())
    assert registered == EXPECTED_TOOLS


@pytest.mark.parametrize(
    "method_name",
    [
        "execute_service_detection",
        "execute_vuln_scan",
        "execute_dns_lookup",
        "execute_ssl_scan",
        "execute_web_dir_enum",
        "execute_subdomain_enum",
        "execute_web_app_scan",
        "execute_os_detection",
        "execute_whois_lookup",
        "execute_hydra_ssh",
        "execute_hydra_http",
        "execute_sqlmap_scan",
    ],
)
def test_coordinator_has_execute_methods(coordinator, method_name):
    """Yeni tool'lar için public execute API'leri korunmalı."""
    assert hasattr(coordinator, method_name), f"Missing method: {method_name}"


@pytest.mark.parametrize(
    "tool,kwargs,expected_prefix,required_tokens",
    [
        (
            NmapOsDetectionTool(),
            {"target": "192.168.1.10", "ports": "22,80", "timing": 4, "osscan_guess": True},
            ["nmap", "-O"],
            ["--osscan-guess", "-p", "22,80", "-T4", "192.168.1.10"],
        ),
        (
            NmapServiceDetectionTool(),
            {"target": "192.168.1.10", "ports": "80,443", "intensity": 7},
            ["nmap", "-sV", "--version-intensity", "7"],
            ["-p", "80,443", "192.168.1.10"],
        ),
        (
            NmapVulnScanTool(),
            {"target": "192.168.1.10", "ports": "443", "scripts": "vuln"},
            ["nmap", "-sS", "--script", "vuln"],
            ["-p", "443", "192.168.1.10"],
        ),
        (
            WhoisLookupTool(),
            {"target": "example.com"},
            ["whois", "example.com"],
            [],
        ),
        (
            HydraSshTool(),
            {"target": "10.0.0.5", "username": "admin", "wordlist": "/tmp/wordlist.txt", "threads": 8},
            ["hydra", "-l", "admin", "-P", "/tmp/wordlist.txt", "-t", "8"],
            ["ssh://10.0.0.5"],
        ),
        (
            HydraHttpTool(),
            {
                "target": "10.0.0.6",
                "username": "admin",
                "wordlist": "/tmp/wordlist.txt",
                "form_path": "/login",
                "form_params": "user=^USER^&pass=^PASS^",
                "fail_string": "invalid",
            },
            ["hydra", "-l", "admin", "-P", "/tmp/wordlist.txt", "-t", "4"],
            ["10.0.0.6", "http-form-post", "/login:user=^USER^&pass=^PASS^:invalid"],
        ),
        (
            SqlmapScanTool(),
            {"url": "http://example.com/item.php?id=1", "batch": True, "level": 3, "risk": 2},
            ["sqlmap", "-u", "http://example.com/item.php?id=1", "--batch"],
            ["--level", "3", "--risk", "2"],
        ),
        (
            DnsLookupTool(),
            {"domain": "example.com", "record_type": "mx"},
            ["nslookup", "-type=MX", "example.com"],
            [],
        ),
        (
            SslScanTool(),
            {"target": "example.com", "port": 8443},
            [],  # platform-dependent prefix
            ["openssl s_client", "example.com:8443", "-showcerts"],
        ),
        (
            GobusterDirTool(),
            {"url": "http://example.com", "wordlist": "common.txt", "extensions": "php,txt"},
            ["gobuster", "dir", "-u", "http://example.com", "-w", "common.txt"],
            ["-x", "php,txt", "-q"],
        ),
        (
            SubdomainEnumTool(),
            {"domain": "example.com", "wordlist": "subs.txt"},
            [],  # platform-dependent prefix
            ["example.com", "nslookup", "FOUND:"],
        ),
        (
            WebAppScanTool(),
            {"url": "http://example.com"},
            [],  # platform-dependent prefix
            ["http://example.com", "curl", "TECH:"],
        ),
    ],
)
def test_new_tool_command_building_is_specific(tool, kwargs, expected_prefix, required_tokens):
    """Her tool komutu beklenen yapıda üretilmeli."""
    cmd = tool.build_command(**kwargs)

    assert cmd[:len(expected_prefix)] == expected_prefix

    joined = " ".join(cmd)
    for token in required_tokens:
        assert token in joined


@pytest.mark.parametrize(
    "parser_cls",
    [
        NmapServiceDetectionParser,
        NmapVulnScanParser,
        NmapOsDetectionParser,
        DnsLookupParser,
        SslScanParser,
        GobusterDirParser,
        SubdomainEnumParser,
        WebAppScanParser,
        WhoisLookupParser,
        HydraSshParser,
        HydraHttpParser,
        SqlmapScanParser,
    ],
)
def test_parser_classes_are_instantiable(parser_cls):
    """Yeni parser sınıfları hatasız instantiate edilebilmeli."""
    parser = parser_cls()
    assert parser is not None


def test_execution_registry_points_to_registered_tools(coordinator):
    """Execution registry'deki tool_id'ler gerçekten coordinator'da register olmalı."""
    registered = set(coordinator.get_available_tools())

    for intent_type, mapping in _EXECUTION_REGISTRY.items():
        assert isinstance(intent_type, IntentType)
        tool_id = mapping.get("tool_id")
        assert tool_id in registered, f"{intent_type.value} -> {tool_id} not registered"


def test_tool_manager_queue_backpressure():
    """Concurrency doluysa iş kuyruklanmalı, kuyruk dolarsa reddedilmeli."""
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(backend=backend, max_concurrent=1, max_queue_size=1)

    class _DummyIntegratedTool:
        def __init__(self):
            self.executions = 0

        def execute(self, callback=None, **kwargs):
            self.executions += 1

        def cancel(self):
            pass

    manager._tools["dummy"] = _DummyIntegratedTool()

    # 1) İlk iş başlar
    assert manager.execute_tool("dummy", target="127.0.0.1") is True
    assert manager.active_executions == 1
    assert manager.queued_executions == 0

    # 2) İkinci iş kuyruğa düşer
    assert manager.execute_tool("dummy", target="127.0.0.2") is True
    assert manager.active_executions == 1
    assert manager.queued_executions == 1

    # 3) Kuyruk dolu olduğu için üçüncü iş reddedilir
    assert manager.execute_tool("dummy", target="127.0.0.3") is False
    assert manager.queued_executions == 1

    backend.close()


def test_tool_manager_cancel_clears_queued_items():
    """cancel_tool() hem çalışanı iptal etmeli hem queued işleri temizlemeli."""
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(backend=backend, max_concurrent=1, max_queue_size=10)

    class _DummyIntegratedTool:
        def __init__(self):
            self.cancelled = False

        def execute(self, callback=None, **kwargs):
            pass

        def cancel(self):
            self.cancelled = True

    dummy = _DummyIntegratedTool()
    manager._tools["dummy"] = dummy

    assert manager.execute_tool("dummy", target="127.0.0.1") is True
    assert manager.execute_tool("dummy", target="127.0.0.2") is True
    assert manager.queued_executions == 1

    assert manager.cancel_tool("dummy") is True
    assert dummy.cancelled is True
    assert manager.queued_executions == 0

    backend.close()


def test_tool_manager_per_tool_limit_allows_other_tool_progress():
    """Aynı tool limiti doluyken farklı tool global slotta çalışabilmeli."""
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(
        backend=backend,
        max_concurrent=2,
        max_queue_size=10,
        default_per_tool_limit=1,
    )

    class _DummyIntegratedTool:
        def execute(self, callback=None, **kwargs):
            pass

        def cancel(self):
            pass

    manager._tools["tool_a"] = _DummyIntegratedTool()
    manager._tools["tool_b"] = _DummyIntegratedTool()

    # İlk A çalışır
    assert manager.execute_tool("tool_a", target="127.0.0.1") is True
    assert manager.active_executions == 1

    # İkinci A, per-tool limite takılıp kuyruğa düşer
    assert manager.execute_tool("tool_a", target="127.0.0.2") is True
    assert manager.active_executions == 1
    assert manager.queued_executions == 1

    # B ise global boş slotta çalışabilir
    assert manager.execute_tool("tool_b", target="127.0.0.3") is True
    assert manager.active_executions == 2
    assert manager.queued_executions == 1

    backend.close()


def test_adaptive_timeout_estimation_for_scan_tools():
    """Port/senaryo büyüdükçe timeout tahmini artmalı."""
    port_tool = NmapPortScanTool(timeout=120)
    vuln_tool = NmapVulnScanTool(timeout=300)

    small_scan = port_tool.estimate_timeout(ports="80,443", scan_type="sT")
    large_scan = port_tool.estimate_timeout(ports="1-5000", scan_type="sT")
    assert large_scan > small_scan

    default_vuln = vuln_tool.estimate_timeout(ports="80,443", scripts="vuln")
    custom_script_vuln = vuln_tool.estimate_timeout(ports="80,443", scripts="vuln,default")
    assert custom_script_vuln >= default_vuln


def test_tool_manager_runtime_metrics_shape():
    """Runtime metric ciktisi temel alanlari icermeli."""
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(backend=backend, max_concurrent=1, max_queue_size=3)

    metrics = manager.get_runtime_metrics()

    assert "active_executions" in metrics
    assert "queued_executions" in metrics
    assert "per_tool_active" in metrics
    assert "avg_queue_wait_ms" in metrics
    assert "avg_tool_run_ms" in metrics
    assert "recent_count" in metrics

    assert isinstance(metrics["active_executions"], int)
    assert isinstance(metrics["queued_executions"], int)
    assert isinstance(metrics["per_tool_active"], dict)

    backend.close()


def test_tool_manager_callback_exception_does_not_deadlock():
    """User callback patlasa bile _active_count duzelmeli ve kuyruk ilerlemeli."""
    backend = SQLiteBackend(":memory:")
    manager = ToolManager(backend=backend, max_concurrent=1, max_queue_size=5)

    captured_callback = {}

    class _DummyIntegratedTool:
        def execute(self, callback=None, **kwargs):
            # Callback'i yakala, manuel cagirmak icin
            captured_callback["cb"] = callback

        def cancel(self):
            pass

    manager._tools["dummy"] = _DummyIntegratedTool()
    manager._tool_active_counts["dummy"] = 0
    manager._tool_limits["dummy"] = 1

    # Tool'u "patlayan" bir callback ile calistir
    errors_caught = []

    def exploding_callback(result):
        raise RuntimeError("Boom! User callback exploded")

    assert manager.execute_tool("dummy", callback=exploding_callback, target="127.0.0.1") is True
    assert manager.active_executions == 1

    # Simdi tool bitmis gibi callback'i cagiralim (sahte result)
    from src.core.tool_integration import IntegratedToolResult
    from src.core.tool_base import ToolStatus
    from src.core.sqlite_backend import ExecutionStatus, ParseStatus

    fake_result = IntegratedToolResult(
        tool_id="dummy",
        execution_id="exec_test",
        tool_status=ToolStatus.SUCCESS,
        execution_status=ExecutionStatus.SUCCESS,
        parse_status=ParseStatus.PARSED,
        entities_created=0,
        stdout="",
        stderr="",
        exit_code=0,
        duration=1.0,
    )

    # Bu PATLAMAYACAK cunku callback exception izole edilmis
    captured_callback["cb"](fake_result)

    # Kritik assertion: _active_count sifira donmeli
    assert manager.active_executions == 0, (
        f"active_count should be 0 after callback exception, got {manager.active_executions}"
    )

    backend.close()
