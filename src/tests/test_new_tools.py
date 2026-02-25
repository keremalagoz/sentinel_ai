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
    NmapServiceDetectionTool,
    NmapVulnScanTool,
    SslScanTool,
    SubdomainEnumTool,
    WebAppScanTool,
)
from src.core.parser_framework import (
    DnsLookupParser,
    GobusterDirParser,
    NmapServiceDetectionParser,
    NmapVulnScanParser,
    SslScanParser,
    SubdomainEnumParser,
    WebAppScanParser,
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
    ],
)
def test_coordinator_has_execute_methods(coordinator, method_name):
    """Yeni tool'lar için public execute API'leri korunmalı."""
    assert hasattr(coordinator, method_name), f"Missing method: {method_name}"


@pytest.mark.parametrize(
    "tool,kwargs,expected_prefix,required_tokens",
    [
        (
            NmapServiceDetectionTool(),
            {"target": "192.168.1.10", "ports": "80,443", "intensity": 7},
            ["nmap", "-sV", "--version-intensity", "7"],
            ["-p", "80,443", "192.168.1.10"],
        ),
        (
            NmapVulnScanTool(),
            {"target": "192.168.1.10", "ports": "443", "scripts": "vuln"},
            ["nmap", "--script", "vuln"],
            ["-p", "443", "192.168.1.10"],
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
            ["cmd.exe", "/c"],
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
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"],
            ["$domain = 'example.com'", "$wordlist = 'subs.txt'", "nslookup"],
        ),
        (
            WebAppScanTool(),
            {"url": "http://example.com"},
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"],
            ["Invoke-WebRequest", "$url = 'http://example.com'", "TECH: WordPress"],
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
        DnsLookupParser,
        SslScanParser,
        GobusterDirParser,
        SubdomainEnumParser,
        WebAppScanParser,
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
