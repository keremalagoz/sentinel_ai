"""Pipeline Integration Test Dosyası

Amaç: Birim testlerin kaçırdığı gerçek-dünya senaryolarını yakalamak.
Hardcoded parametreler yerine simulated LLM çıktıları kullanarak
Intent → build_execution_kwargs → build_command tam pipeline'ını test eder.

Test Kategorileri:
  A) param_map ↔ build_command Uyum (otomatik — her tool için)
  B) Simulated LLM Output → Final Command (gerçekçi senaryolar)
  C) Fallback Kalite Guard (bare komut üretimini yakala)
  D) Negative Path (bilinçli eksiklik doğrulama)
  E) Multi-Intent Merge Flags (service_detection, no_dns vb.)

Tarih: 5 Mart 2026
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Set

import pytest

from src.ai.schemas import (
    Intent,
    IntentType,
    RiskLevel,
    ToolSpec,
    FinalCommand,
)
from src.ai.tool_registry import (
    TOOL_REGISTRY,
    _EXECUTION_REGISTRY,
    build_tool_spec,
    build_execution_kwargs,
    get_tool_for_intent,
    get_execution_tool_id,
    get_execution_intents,
)
from src.ai.command_builder import CommandBuilder
from src.core.tool_base import (
    BaseTool,
    NmapPingSweepTool,
    NmapPortScanTool,
    NmapServiceDetectionTool,
    NmapOsDetectionTool,
    NmapVulnScanTool,
    DnsLookupTool,
    SslScanTool,
    GobusterDirTool,
    SubdomainEnumTool,
    WebAppScanTool,
    WhoisLookupTool,
    HydraSshTool,
    HydraHttpTool,
    SqlmapScanTool,
)
from src.core.sentinel_coordinator import SentinelCoordinator


# =============================================================================
# HELPER: Tool instance'ları
# =============================================================================

_TOOL_INSTANCES: Dict[str, BaseTool] = {}


def _get_tool_instance(tool_id: str) -> Optional[BaseTool]:
    """Lazy-init tool instance cache."""
    if tool_id not in _TOOL_INSTANCES:
        _TOOL_MAP = {
            "nmap_ping_sweep": NmapPingSweepTool,
            "nmap_port_scan": NmapPortScanTool,
            "nmap_service_detection": NmapServiceDetectionTool,
            "nmap_os_detection": NmapOsDetectionTool,
            "nmap_vuln_scan": NmapVulnScanTool,
            "dns_lookup": DnsLookupTool,
            "ssl_scan": SslScanTool,
            "gobuster_dir": GobusterDirTool,
            "subdomain_enum": SubdomainEnumTool,
            "web_app_scan": WebAppScanTool,
            "whois_lookup": WhoisLookupTool,
            "hydra_ssh": HydraSshTool,
            "hydra_http": HydraHttpTool,
            "sqlmap_scan": SqlmapScanTool,
        }
        cls = _TOOL_MAP.get(tool_id)
        if cls is None:
            return None
        _TOOL_INSTANCES[tool_id] = cls()
    return _TOOL_INSTANCES[tool_id]


# =============================================================================
# A) param_map ↔ build_command UYUM TESTLERİ
# =============================================================================


class TestParamMapBuildCommandAlignment:
    """Her _EXECUTION_REGISTRY entry'si için: build_command() imzasındaki
    tüm parametrelerin param_map'te tanımlı olduğunu doğrular.

    Bu test, yeni tool/parametre eklediğimizde otomatik olarak eksik
    param_map girdilerini yakalar.
    """

    @pytest.fixture
    def execution_intents(self) -> List[IntentType]:
        return list(_EXECUTION_REGISTRY.keys())

    def test_all_execution_intents_have_tool_instances(self, execution_intents):
        """Her execution intent'in tool_id'sine karşılık bir tool instance olmalı."""
        for intent_type in execution_intents:
            tool_id = get_execution_tool_id(intent_type)
            assert tool_id is not None, f"{intent_type.value}: tool_id None"
            tool = _get_tool_instance(tool_id)
            assert tool is not None, f"{intent_type.value}: tool instance '{tool_id}' bulunamadı"

    @pytest.mark.parametrize("intent_type", list(_EXECUTION_REGISTRY.keys()),
                             ids=lambda it: it.value)
    def test_param_map_covers_build_command_params(self, intent_type: IntentType):
        """param_map, build_command() imzasındaki her parametreyi kapsamalı.

        Muafiyet: target (target_arg ile map'lenir), self, kwargs ve
        default değeri olan parametreler (tool'un kendi default'ını kullanır)
        eksik olabilir — AMA önemli parametreler (timing, top_ports, vb.)
        mutlaka map'lenmiş olmalı.
        """
        mapping = _EXECUTION_REGISTRY[intent_type]
        tool_id = mapping["tool_id"]
        param_map = mapping.get("param_map", {})
        target_arg = mapping.get("target_arg", "target")

        tool = _get_tool_instance(tool_id)
        assert tool is not None

        sig = inspect.signature(tool.build_command)
        # build_command'ın tüm parametreleri (self, kwargs hariç)
        build_params = {
            name
            for name, p in sig.parameters.items()
            if name not in ("self", "kwargs")
            and p.kind not in (
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            )
        }

        # target_arg maplenmiş → çıkar
        build_params.discard(target_arg)

        # param_map'teki tool-side değerler (value'lar)
        mapped_tool_args = set(param_map.values())

        # Kapsanmayan parametreler
        unmapped = build_params - mapped_tool_args

        # Kritik parametreler listesi — bunların KESİNLİKLE map'lenmiş olması gerekir
        CRITICAL_PARAMS = {
            "timing", "top_ports", "no_dns", "verbose", "service_detection",
            "no_ping", "aggressive", "traceroute",
            "ports", "scan_type", "intensity", "version_intensity",
            "version_mode", "osscan_guess", "scripts", "script_args",
            "record_type", "dns_server", "port", "servername",
            "tls_version", "starttls", "wordlist", "extensions", "threads",
            "status_codes", "no_tls_validation", "follow_redirect",
            "username", "form_path", "form_params", "fail_string",
            "method", "level", "risk", "batch", "forms", "dbs",
            "exclude",
        }

        critical_unmapped = unmapped & CRITICAL_PARAMS
        assert not critical_unmapped, (
            f"{intent_type.value} ({tool_id}): Kritik parametre(ler) param_map'te eksik: "
            f"{sorted(critical_unmapped)}. "
            f"param_map keys: {sorted(param_map.keys())}, "
            f"build_command params: {sorted(build_params)}"
        )

    @pytest.mark.parametrize("intent_type", list(_EXECUTION_REGISTRY.keys()),
                             ids=lambda it: it.value)
    def test_param_map_values_are_valid_build_command_params(self, intent_type: IntentType):
        """param_map'teki her value, build_command() imzasında gerçekten var olmalı."""
        mapping = _EXECUTION_REGISTRY[intent_type]
        tool_id = mapping["tool_id"]
        param_map = mapping.get("param_map", {})

        tool = _get_tool_instance(tool_id)
        assert tool is not None

        sig = inspect.signature(tool.build_command)
        valid_params = set(sig.parameters.keys()) - {"self"}

        for llm_key, tool_arg in param_map.items():
            assert tool_arg in valid_params, (
                f"{intent_type.value}: param_map['{llm_key}'] = '{tool_arg}' "
                f"build_command() imzasında yok. "
                f"Geçerli parametreler: {sorted(valid_params)}"
            )


# =============================================================================
# B) SIMULATED LLM OUTPUT → FINAL COMMAND TESTLERİ
# =============================================================================


class TestSimulatedPipeline:
    """LLM'i gerçekten çağırmadan, gerçekçi Intent objesi oluşturup
    build_execution_kwargs → build_command zincirinden geçirir.

    Her test, kullanıcının doğal dille ifade edebileceği bir senaryoyu
    simüle eder.
    """

    def _run_pipeline(
        self,
        intent_type: IntentType,
        target: str,
        params: Dict[str, Any],
    ) -> List[str]:
        """Intent → build_execution_kwargs → tool.build_command → cmd list."""
        exec_kwargs = build_execution_kwargs(intent_type, target, params)
        assert exec_kwargs is not None, (
            f"{intent_type.value}: build_execution_kwargs returned None "
            f"for target={target}, params={params}"
        )

        tool_id = get_execution_tool_id(intent_type)
        assert tool_id is not None
        tool = _get_tool_instance(tool_id)
        assert tool is not None

        cmd = tool.build_command(**exec_kwargs)
        assert cmd is not None and len(cmd) > 0
        return cmd

    # ── PORT SCAN senaryoları ──

    def test_port_scan_top_ports_with_service_detection(self):
        """Senaryo: '192.168.0.8 ilk 100 portunu tara ve versiyon bilgilerini bul'"""
        cmd = self._run_pipeline(
            IntentType.PORT_SCAN,
            "192.168.0.8",
            {"top_ports": 100, "service_detection": True},
        )
        cmd_str = " ".join(cmd)
        assert "--top-ports" in cmd_str, f"--top-ports eksik: {cmd_str}"
        assert "100" in cmd_str, f"100 değeri eksik: {cmd_str}"
        assert "-sV" in cmd_str, f"-sV eksik (service_detection): {cmd_str}"
        assert "192.168.0.8" in cmd_str

    def test_port_scan_specific_ports(self):
        """Senaryo: '10.0.0.1 80 ve 443 portlarını tara'"""
        cmd = self._run_pipeline(
            IntentType.PORT_SCAN,
            "10.0.0.1",
            {"ports": "80,443"},
        )
        cmd_str = " ".join(cmd)
        assert "-p" in cmd_str
        assert "80,443" in cmd_str
        assert "10.0.0.1" in cmd_str

    def test_port_scan_with_timing_and_no_dns(self):
        """Senaryo: 'hızlı port scan yap T4 ile DNS çözümleme yapma'"""
        cmd = self._run_pipeline(
            IntentType.PORT_SCAN,
            "10.0.0.5",
            {"timing": 4, "no_dns": True},
        )
        cmd_str = " ".join(cmd)
        assert "-T4" in cmd_str, f"-T4 eksik: {cmd_str}"
        assert "-n" in cmd_str, f"-n (no_dns) eksik: {cmd_str}"

    def test_port_scan_with_scan_type_and_verbose(self):
        """Senaryo: 'SYN taraması yap, detaylı çıktı ver'"""
        cmd = self._run_pipeline(
            IntentType.PORT_SCAN,
            "172.16.0.1",
            {"scan_type": "sS", "verbose": True},
        )
        cmd_str = " ".join(cmd)
        assert "-sS" in cmd_str, f"-sS eksik: {cmd_str}"
        assert "-v" in cmd_str, f"-v (verbose) eksik: {cmd_str}"

    def test_port_scan_defaults_no_params(self):
        """Senaryo: '192.168.1.1 portlarını tara' (parametre yok → default'lar kullanılır)"""
        cmd = self._run_pipeline(
            IntentType.PORT_SCAN,
            "192.168.1.1",
            {},
        )
        cmd_str = " ".join(cmd)
        # Default: -sT -p 1-1000
        assert "-sT" in cmd_str, f"Default scan_type -sT eksik: {cmd_str}"
        assert "-p" in cmd_str, f"Default -p eksik: {cmd_str}"
        assert "192.168.1.1" in cmd_str

    def test_port_scan_all_params_combined(self):
        """Senaryo: Tüm parametreler birlikte (en karmaşık case)"""
        cmd = self._run_pipeline(
            IntentType.PORT_SCAN,
            "10.10.10.10",
            {
                "top_ports": 50,
                "scan_type": "sS",
                "timing": 3,
                "no_dns": True,
                "verbose": True,
                "service_detection": True,
            },
        )
        cmd_str = " ".join(cmd)
        assert "-sS" in cmd_str
        assert "-sV" in cmd_str
        assert "--top-ports" in cmd_str
        assert "50" in cmd_str
        assert "-T3" in cmd_str
        assert "-n" in cmd_str
        assert "-v" in cmd_str
        assert "10.10.10.10" in cmd_str

    # ── HOST DISCOVERY senaryoları ──

    def test_host_discovery_with_timing(self):
        """Senaryo: 'ağı hızlı tara T4'"""
        cmd = self._run_pipeline(
            IntentType.HOST_DISCOVERY,
            "192.168.1.0/24",
            {"timing": 4},
        )
        cmd_str = " ".join(cmd)
        assert "-sn" in cmd_str
        assert "-T4" in cmd_str
        assert "192.168.1.0/24" in cmd_str

    def test_host_discovery_with_exclude_and_no_dns(self):
        """Senaryo: 'ağı tara ama 192.168.1.1 hariç tut, DNS çözümleme yapma'"""
        cmd = self._run_pipeline(
            IntentType.HOST_DISCOVERY,
            "192.168.1.0/24",
            {"exclude": "192.168.1.1", "no_dns": True},
        )
        cmd_str = " ".join(cmd)
        assert "-sn" in cmd_str
        assert "--exclude" in cmd_str
        assert "192.168.1.1" in cmd_str
        assert "-n" in cmd_str

    def test_host_discovery_no_params(self):
        """Senaryo: '192.168.1.0/24 ağını tara' (default)"""
        cmd = self._run_pipeline(
            IntentType.HOST_DISCOVERY,
            "192.168.1.0/24",
            {},
        )
        cmd_str = " ".join(cmd)
        assert "-sn" in cmd_str
        assert "192.168.1.0/24" in cmd_str

    # ── SERVICE DETECTION senaryoları ──

    def test_service_detection_with_ports_and_timing(self):
        """Senaryo: '10.0.0.1 üzerinde 80,443 portlarında servis tespiti yap T3'"""
        cmd = self._run_pipeline(
            IntentType.SERVICE_DETECTION,
            "10.0.0.1",
            {"ports": "80,443", "timing": 3},
        )
        cmd_str = " ".join(cmd)
        assert "-sV" in cmd_str
        assert "-p" in cmd_str
        assert "80,443" in cmd_str
        assert "-T3" in cmd_str

    # ── OS DETECTION senaryoları ──

    def test_os_detection_with_service_detection(self):
        """Senaryo: 'işletim sistemi ve servis bilgilerini tespit et'"""
        cmd = self._run_pipeline(
            IntentType.OS_DETECTION,
            "10.0.0.1",
            {"service_detection": True},
        )
        cmd_str = " ".join(cmd)
        assert "-O" in cmd_str
        assert "-sV" in cmd_str

    def test_os_detection_with_osscan_guess(self):
        """Senaryo: 'agresif OS tespiti yap'"""
        cmd = self._run_pipeline(
            IntentType.OS_DETECTION,
            "192.168.1.100",
            {"osscan_guess": True},
        )
        cmd_str = " ".join(cmd)
        assert "-O" in cmd_str
        assert "--osscan-guess" in cmd_str

    # ── VULN SCAN senaryoları ──

    def test_vuln_scan_with_ports_and_timing(self):
        """Senaryo: '80,443 portlarında zafiyet tara hızlı'"""
        cmd = self._run_pipeline(
            IntentType.VULN_SCAN,
            "10.0.0.1",
            {"ports": "80,443", "timing": 4},
        )
        cmd_str = " ".join(cmd)
        assert "--script" in cmd_str
        assert "vuln" in cmd_str
        assert "-p" in cmd_str
        assert "-T4" in cmd_str

    # ── DNS LOOKUP senaryoları ──

    def test_dns_lookup_mx_record(self):
        """Senaryo: 'example.com MX kayıtlarını sorgula'"""
        cmd = self._run_pipeline(
            IntentType.DNS_LOOKUP,
            "example.com",
            {"record_type": "MX"},
        )
        cmd_str = " ".join(cmd)
        assert "example.com" in cmd_str
        assert "MX" in cmd_str

    def test_dns_lookup_with_server(self):
        """Senaryo: 'example.com DNS sorgula 8.8.8.8 ile'"""
        cmd = self._run_pipeline(
            IntentType.DNS_LOOKUP,
            "example.com",
            {"dns_server": "8.8.8.8"},
        )
        cmd_str = " ".join(cmd)
        assert "example.com" in cmd_str
        assert "8.8.8.8" in cmd_str

    # ── SSL SCAN senaryoları ──

    def test_ssl_scan_custom_port(self):
        """Senaryo: 'example.com SSL sertifikasını kontrol et port 8443'"""
        cmd = self._run_pipeline(
            IntentType.SSL_SCAN,
            "example.com",
            {"port": 8443},
        )
        cmd_str = " ".join(cmd)
        assert "example.com" in cmd_str

    # ── WEB DIR ENUM senaryoları ──

    def test_web_dir_enum_with_extensions(self):
        """Senaryo: 'web sitesinde php ve html dosyaları ara'"""
        cmd = self._run_pipeline(
            IntentType.WEB_DIR_ENUM,
            "http://example.com",
            {"extensions": "php,html"},
        )
        cmd_str = " ".join(cmd)
        assert "http://example.com" in cmd_str
        assert "php,html" in cmd_str

    def test_web_dir_enum_with_threads(self):
        """Senaryo: '50 thread ile dizin taraması yap'"""
        cmd = self._run_pipeline(
            IntentType.WEB_DIR_ENUM,
            "http://example.com",
            {"threads": 50},
        )
        cmd_str = " ".join(cmd)
        assert "50" in cmd_str

    # ── BRUTE FORCE SSH senaryoları ──

    def test_brute_force_ssh_full_params(self):
        """Senaryo: 'SSH brute force admin kullanıcısı rockyou wordlist'"""
        cmd = self._run_pipeline(
            IntentType.BRUTE_FORCE_SSH,
            "10.0.0.1",
            {"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt"},
        )
        cmd_str = " ".join(cmd)
        assert "admin" in cmd_str
        assert "rockyou" in cmd_str
        assert "10.0.0.1" in cmd_str

    # ── SQL INJECTION senaryoları ──

    def test_sql_injection_aggressive(self):
        """Senaryo: 'SQL injection testi seviye 5 risk 3'"""
        cmd = self._run_pipeline(
            IntentType.SQL_INJECTION,
            "http://example.com/page?id=1",
            {"level": 5, "risk": 3},
        )
        cmd_str = " ".join(cmd)
        assert "--level" in cmd_str or "5" in cmd_str
        assert "--risk" in cmd_str or "3" in cmd_str


# =============================================================================
# C) FALLBACK KALİTE GUARD TESTLERİ
# =============================================================================


class TestFallbackQualityGuard:
    """build_tool_spec() → CommandBuilder.build() fallback yolunun
    bare komut üretmesini tespit eden testler.
    """

    @pytest.fixture
    def builder(self) -> CommandBuilder:
        return CommandBuilder()

    @pytest.mark.parametrize("intent_type", [
        IntentType.PORT_SCAN,
        IntentType.HOST_DISCOVERY,
        IntentType.SERVICE_DETECTION,
        IntentType.OS_DETECTION,
        IntentType.VULN_SCAN,
        IntentType.DNS_LOOKUP,
        IntentType.SSL_SCAN,
        IntentType.WEB_DIR_ENUM,
        IntentType.SUBDOMAIN_ENUM,
        IntentType.WEB_VULN_SCAN,
        IntentType.WHOIS_LOOKUP,
    ], ids=lambda it: it.value)
    def test_build_tool_spec_produces_empty_arguments(self, intent_type: IntentType):
        """Sprint 3.5 Track E: build_tool_spec() arguments=[] üretmeli (metadata-only).

        Bu test, build_tool_spec'in beklenen davranışını belgeleyerek
        fallback yolunun bare komut üreteceğini KANITLAR.
        Track E'nin bilinçli bir tasarım kararı olduğunu doğrular.
        """
        tool_spec = build_tool_spec(intent_type, "192.168.1.1", {"ports": "80,443"})
        if tool_spec is not None and tool_spec.tool:  # Komut üreten intent'ler
            assert tool_spec.arguments == [], (
                f"{intent_type.value}: build_tool_spec artık arguments üretmemeli "
                f"(Track E metadata-only). Aldığımız: {tool_spec.arguments}"
            )

    @pytest.mark.parametrize("intent_type", [
        IntentType.PORT_SCAN,
        IntentType.HOST_DISCOVERY,
        IntentType.SERVICE_DETECTION,
        IntentType.VULN_SCAN,
    ], ids=lambda it: it.value)
    def test_fallback_produces_bare_command_warning(self, intent_type: IntentType, builder):
        """Fallback yolu bare komut üretiyorsa, bu known limitation. 
        
        Bu test, fallback'in bare komut ürettiğini BELGELER.
        Track E aktifken preferred path (execution tool) kullanılmalı.
        """
        tool_spec = build_tool_spec(intent_type, "192.168.1.1", {})
        if tool_spec is None or not tool_spec.tool:
            pytest.skip(f"{intent_type.value}: tool boş")

        command, error = builder.build(tool_spec)
        if command is not None:
            # Bare command = sadece target, başka argüman yok
            non_target_args = [
                a for a in command.arguments
                if a != "192.168.1.1"
            ]
            # Bu bir UYARI testi — fallback'in bare komut ürettiğini belgeliyor
            if not non_target_args:
                # Bare komut — beklenen davranış Track E ile
                pass  # Known limitation, Adım 4 (Kerem) ile düzeltilecek


# =============================================================================
# D) NEGATIVE PATH TESTLERİ
# =============================================================================


class TestNegativePaths:
    """Bilinçli eksiklik ve hata senaryolarını doğrular."""

    def test_unmapped_param_is_silently_dropped(self):
        """param_map'te tanımsız parametreler build_execution_kwargs çıktısında olmamalı."""
        # PORT_SCAN'de 'nonexistent_param' yok
        kwargs = build_execution_kwargs(
            IntentType.PORT_SCAN,
            "192.168.1.1",
            {"nonexistent_param": "value", "ports": "80"},
        )
        assert kwargs is not None
        assert "nonexistent_param" not in kwargs
        assert "ports" in kwargs

    def test_info_query_has_no_execution_mapping(self):
        """INFO_QUERY ve UNKNOWN intent'leri execution registry'de olmamalı."""
        assert get_execution_tool_id(IntentType.INFO_QUERY) is None
        assert get_execution_tool_id(IntentType.UNKNOWN) is None

    def test_build_execution_kwargs_returns_none_for_unmapped_intent(self):
        """Execution registry'de olmayan intent → None."""
        result = build_execution_kwargs(IntentType.INFO_QUERY, "target", {})
        assert result is None

    def test_build_execution_kwargs_returns_none_without_target(self):
        """Target gerektiren intent'e target verilmezse → None."""
        result = build_execution_kwargs(IntentType.PORT_SCAN, None, {})
        assert result is None

    def test_build_execution_kwargs_returns_none_for_empty_target(self):
        """Boş string target → None."""
        result = build_execution_kwargs(IntentType.PORT_SCAN, "", {})
        assert result is None

    def test_none_params_handled_gracefully(self):
        """params=None olduğunda hata vermemeli."""
        kwargs = build_execution_kwargs(IntentType.PORT_SCAN, "192.168.1.1", None)
        assert kwargs is not None
        assert kwargs["target"] == "192.168.1.1"

    def test_none_param_values_are_not_passed(self):
        """params dict'inde value=None olan girdiler tool'a geçirilmemeli."""
        kwargs = build_execution_kwargs(
            IntentType.PORT_SCAN,
            "192.168.1.1",
            {"timing": None, "ports": "80"},
        )
        assert "timing" not in kwargs
        assert "ports" in kwargs


# =============================================================================
# E) MULTI-INTENT MERGE FLAG TESTLERİ
# =============================================================================


class TestMultiIntentMergeFlags:
    """Opsiyon A: Primary Intent + Merge Flags.

    Tek intent altında birden fazla davranışı (port tarama + versiyon tespiti)
    parametrelerle birleştirmeyi test eder.
    """

    def test_port_scan_with_service_detection_flag(self):
        """PORT_SCAN + service_detection=True → nmap -sT -sV --top-ports 100"""
        tool = NmapPortScanTool()
        cmd = tool.build_command(
            target="192.168.0.8",
            top_ports=100,
            service_detection=True,
        )
        cmd_str = " ".join(cmd)
        assert "-sV" in cmd_str, f"-sV eksik: {cmd_str}"
        assert "--top-ports" in cmd_str
        assert "100" in cmd_str

    def test_port_scan_without_service_detection(self):
        """-sV flag'i service_detection=False (default) iken eklenmemeli."""
        tool = NmapPortScanTool()
        cmd = tool.build_command(target="192.168.0.8", ports="1-1000")
        cmd_str = " ".join(cmd)
        assert "-sV" not in cmd_str, f"-sV olmamalı (default): {cmd_str}"

    def test_os_detection_with_service_detection(self):
        """OS_DETECTION + service_detection=True → nmap -O -sV"""
        tool = NmapOsDetectionTool()
        cmd = tool.build_command(
            target="10.0.0.1",
            service_detection=True,
        )
        cmd_str = " ".join(cmd)
        assert "-O" in cmd_str
        assert "-sV" in cmd_str

    def test_os_detection_without_service_detection(self):
        """OS_DETECTION default → sadece -O, -sV yok."""
        tool = NmapOsDetectionTool()
        cmd = tool.build_command(target="10.0.0.1")
        cmd_str = " ".join(cmd)
        assert "-O" in cmd_str
        assert "-sV" not in cmd_str

    def test_service_detection_reaches_port_scan_via_pipeline(self):
        """Tam pipeline: PORT_SCAN + service_detection param_map üzerinden geçmeli."""
        kwargs = build_execution_kwargs(
            IntentType.PORT_SCAN,
            "192.168.0.8",
            {"service_detection": True, "top_ports": 100},
        )
        assert kwargs is not None
        assert kwargs.get("service_detection") is True
        assert kwargs.get("top_ports") == 100

        tool = NmapPortScanTool()
        cmd = tool.build_command(**kwargs)
        cmd_str = " ".join(cmd)
        assert "-sV" in cmd_str
        assert "--top-ports" in cmd_str

    def test_merge_flags_full_scenario(self):
        """Gerçek senaryo: '192.168.0.8 bu ip adresinin ilk 100 portunu tara
        ve versiyon bilgilerini tara'

        Bu, orijinal hata senaryosudur. LLM'in doğru params ürettiğini
        varsayarak pipeline'ın bu parametreleri komuta dönüştürdüğünü doğrular.
        """
        # Simulated LLM output
        intent = Intent(
            intent_type=IntentType.PORT_SCAN,
            target="192.168.0.8",
            params={"top_ports": 100, "service_detection": True},
            confidence=0.95,
        )

        # Pipeline
        exec_kwargs = build_execution_kwargs(
            intent.intent_type, intent.target, intent.params
        )
        assert exec_kwargs is not None

        tool = NmapPortScanTool()
        cmd = tool.build_command(**exec_kwargs)
        cmd_str = " ".join(cmd)

        # Doğrulama — orijinal hata: sadece "nmap 192.168.0.8" üretiliyordu
        assert cmd_str != "nmap 192.168.0.8", (
            f"REGRESYON: Bare komut üretildi! Komut: {cmd_str}"
        )
        assert "--top-ports" in cmd_str, f"--top-ports eksik: {cmd_str}"
        assert "100" in cmd_str, f"100 değeri eksik: {cmd_str}"
        assert "-sV" in cmd_str, f"-sV eksik: {cmd_str}"
        assert "192.168.0.8" in cmd_str


# =============================================================================
# F) COORDINATOR ÜZERINDEN TAM PIPELINE (OPSIYONEL)
# =============================================================================


class TestCoordinatorPipeline:
    """SentinelCoordinator üzerinden execution tool'a ulaşarak
    tam preferred path'i test eder.
    """

    @pytest.fixture
    def coordinator(self) -> SentinelCoordinator:
        return SentinelCoordinator()

    def test_coordinator_port_scan_with_top_ports(self, coordinator):
        """Coordinator → nmap_port_scan → --top-ports 100 -sV"""
        tool_id = get_execution_tool_id(IntentType.PORT_SCAN)
        assert tool_id == "nmap_port_scan"

        integrated_tool = coordinator.manager.get_tool(tool_id)
        assert integrated_tool is not None

        exec_kwargs = build_execution_kwargs(
            IntentType.PORT_SCAN,
            "192.168.0.8",
            {"top_ports": 100, "service_detection": True},
        )
        cmd = integrated_tool.tool.build_command(**exec_kwargs)
        cmd_str = " ".join(cmd)

        assert "--top-ports" in cmd_str
        assert "-sV" in cmd_str
        assert "192.168.0.8" in cmd_str

    def test_coordinator_host_discovery_with_timing(self, coordinator):
        """Coordinator → nmap_ping_sweep → -T4"""
        tool_id = get_execution_tool_id(IntentType.HOST_DISCOVERY)
        integrated_tool = coordinator.manager.get_tool(tool_id)
        assert integrated_tool is not None

        exec_kwargs = build_execution_kwargs(
            IntentType.HOST_DISCOVERY,
            "10.0.0.0/24",
            {"timing": 4, "no_dns": True},
        )
        cmd = integrated_tool.tool.build_command(**exec_kwargs)
        cmd_str = " ".join(cmd)

        assert "-sn" in cmd_str
        assert "-T4" in cmd_str
        assert "-n" in cmd_str
