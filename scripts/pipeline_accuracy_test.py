#!/usr/bin/env python3
"""Pipeline Dogruluk Testi — 14 Tool x 5+ Senaryo

Tum tool'larin deterministic pipeline'ini test eder:
  Intent + Params -> build_execution_kwargs -> build_command -> FinalCommand

Her test case icin:
  - Beklenen komut parcalarini (must_contain) dogrular
  - Olmamasi gereken parcalari (must_not_contain) denetler
  - risk_level ve requires_root dogrulugunu kontrol eder

Iki mod destekler:
  --mode deterministic   Pipeline'i bilinen intent/params ile test eder (LLM gerektirmez)
  --mode full            Kullanici girdisini LLM -> Pipeline akisiyla test eder (Ollama gerekli)

Kullanim:
    python scripts/pipeline_accuracy_test.py
    python scripts/pipeline_accuracy_test.py --mode full --model qwen2.5:3b
    python scripts/pipeline_accuracy_test.py --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.schemas import IntentType, RiskLevel
from src.ai.tool_registry import (
    build_tool_spec,
    get_execution_tool_id,
    build_execution_kwargs,
)
from src.core.sentinel_coordinator import SentinelCoordinator


# =============================================================================
# ROOT FLAGS — orchestrator ile tutarli
# =============================================================================
_ROOT_FLAGS: frozenset = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})


# =============================================================================
# TEST CASE DEFINITION
# =============================================================================
@dataclass
class PipelineTestCase:
    """Tek bir pipeline test senaryosu."""
    id: str
    description: str
    # Deterministic inputs
    intent: IntentType
    target: str
    params: Dict[str, Any]
    # Expectations
    must_contain: List[str]
    must_not_contain: List[str] = field(default_factory=list)
    expected_executable: str = ""
    expected_requires_root: Optional[bool] = None
    expected_risk: Optional[str] = None  # "low", "medium", "high"
    # Full-pipeline mode (LLM)
    user_input: str = ""  # Dogal dil giris, full mode icin


# =============================================================================
# 70 TEST CASES — 14 Tool x 5 Senaryo
# =============================================================================

TEST_CASES: List[PipelineTestCase] = [
    # =========================================================================
    # HOST_DISCOVERY (nmap_ping_sweep) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="HD-01", description="Temel ping sweep",
        intent=IntentType.HOST_DISCOVERY, target="192.168.1.0/24", params={},
        must_contain=["nmap", "-sn", "192.168.1.0/24"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.1.0/24 agindaki aktif cihazlari bul",
    ),
    PipelineTestCase(
        id="HD-02", description="Timing ile ping sweep",
        intent=IntentType.HOST_DISCOVERY, target="10.0.0.0/16", params={"timing": "4"},
        must_contain=["nmap", "-sn", "-T4", "10.0.0.0/16"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="10.0.0.0/16 agini hizli ping sweep ile tara",
    ),
    PipelineTestCase(
        id="HD-03", description="DNS devre disi ping sweep",
        intent=IntentType.HOST_DISCOVERY, target="172.16.0.0/24", params={"no_dns": "true"},
        must_contain=["nmap", "-sn", "-n", "172.16.0.0/24"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="172.16.0.0/24 agini DNS cozumlemesi olmadan tara",
    ),
    PipelineTestCase(
        id="HD-04", description="Exclude ile ping sweep",
        intent=IntentType.HOST_DISCOVERY, target="192.168.0.0/24",
        params={"exclude": "192.168.0.1"},
        must_contain=["nmap", "-sn", "--exclude", "192.168.0.1", "192.168.0.0/24"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.0.0/24 agini 192.168.0.1 haric tara",
    ),
    PipelineTestCase(
        id="HD-05", description="Timing + no_dns birlikte",
        intent=IntentType.HOST_DISCOVERY, target="10.10.10.0/24",
        params={"timing": "3", "no_dns": "true"},
        must_contain=["nmap", "-sn", "-T3", "-n", "10.10.10.0/24"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="10.10.10.0/24 agini T3 hizda DNS olmadan kesfet",
    ),

    # =========================================================================
    # PORT_SCAN (nmap_port_scan) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="PS-01", description="Temel TCP port scan",
        intent=IntentType.PORT_SCAN, target="192.168.0.8", params={},
        must_contain=["nmap", "-sT", "192.168.0.8"],
        must_not_contain=["-sS"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.0.8 adresinin portlarini tara",
    ),
    PipelineTestCase(
        id="PS-02", description="Top-ports + service detection",
        intent=IntentType.PORT_SCAN, target="192.168.0.8",
        params={"top_ports": "100", "service_detection": "true"},
        must_contain=["nmap", "-sT", "-sV", "--top-ports", "100", "192.168.0.8"],
        must_not_contain=["-sS"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.0.8 ip adresinin ilk 100 portunu tara ve versiyon bilgilerini tara",
    ),
    PipelineTestCase(
        id="PS-03", description="SYN scan (root gerekli)",
        intent=IntentType.PORT_SCAN, target="10.0.0.1",
        params={"scan_type": "sS", "ports": "1-1000"},
        must_contain=["nmap", "-sS", "-p", "1-1000", "10.0.0.1"],
        expected_executable="nmap", expected_requires_root=True,
        expected_risk="high",
        user_input="10.0.0.1 adresine SYN scan yap port 1-1000",
    ),
    PipelineTestCase(
        id="PS-04", description="UDP scan (root gerekli)",
        intent=IntentType.PORT_SCAN, target="10.0.0.2",
        params={"scan_type": "sU", "top_ports": "50"},
        must_contain=["nmap", "-sU", "--top-ports", "50", "10.0.0.2"],
        expected_executable="nmap", expected_requires_root=True,
        expected_risk="high",
        user_input="10.0.0.2 adresine UDP scan yap ilk 50 port",
    ),
    PipelineTestCase(
        id="PS-05", description="Timing + verbose + no_dns birlikte",
        intent=IntentType.PORT_SCAN, target="172.16.0.100",
        params={"timing": "4", "verbose": "true", "no_dns": "true", "top_ports": "200"},
        must_contain=["nmap", "-sT", "--top-ports", "200", "-T4", "-n", "-v", "172.16.0.100"],
        must_not_contain=["-sS"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="172.16.0.100 adresinin ilk 200 portunu hizli tara DNS olmadan detayli cikti",
    ),

    # =========================================================================
    # SERVICE_DETECTION (nmap_service_detection) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="SD-01", description="Temel servis tespiti",
        intent=IntentType.SERVICE_DETECTION, target="192.168.1.1", params={},
        must_contain=["nmap", "-sV", "192.168.1.1"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.1.1 uzerindeki servislerin versiyonlarini tespit et",
    ),
    PipelineTestCase(
        id="SD-02", description="Belirli portlarda servis tespiti",
        intent=IntentType.SERVICE_DETECTION, target="10.0.0.5",
        params={"ports": "22,80,443"},
        must_contain=["nmap", "-sV", "-p", "22,80,443", "10.0.0.5"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="10.0.0.5 uzerinde port 22,80,443 servislerini tespit et",
    ),
    PipelineTestCase(
        id="SD-03", description="Yuksek intensity ile servis tespiti",
        intent=IntentType.SERVICE_DETECTION, target="192.168.1.50",
        params={"intensity": "9"},
        must_contain=["nmap", "-sV", "--version-intensity", "9", "192.168.1.50"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.1.50 servislerini agresif intensity ile tespit et",
    ),
    PipelineTestCase(
        id="SD-04", description="Timing ile servis tespiti",
        intent=IntentType.SERVICE_DETECTION, target="10.10.10.1",
        params={"timing": "3", "ports": "1-100"},
        must_contain=["nmap", "-sV", "-T3", "-p", "1-100", "10.10.10.1"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="10.10.10.1 uzerindeki ilk 100 port servislerini T3 hizda tespit et",
    ),
    PipelineTestCase(
        id="SD-05", description="All ports version detect",
        intent=IntentType.SERVICE_DETECTION, target="192.168.2.1",
        params={"version_mode": "all"},
        must_contain=["nmap", "-sV", "--version-all", "192.168.2.1"],
        expected_executable="nmap", expected_requires_root=False,
        user_input="192.168.2.1 uzerinde tum servislerin versiyonlarini tara",
    ),

    # =========================================================================
    # OS_DETECTION (nmap_os_detection) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="OD-01", description="Temel OS tespiti",
        intent=IntentType.OS_DETECTION, target="192.168.1.1", params={},
        must_contain=["nmap", "-O", "192.168.1.1"],
        expected_executable="nmap", expected_requires_root=True,
        expected_risk="high",
        user_input="192.168.1.1 isletim sistemini tespit et",
    ),
    PipelineTestCase(
        id="OD-02", description="OS + service detection",
        intent=IntentType.OS_DETECTION, target="10.0.0.10",
        params={"service_detection": "true"},
        must_contain=["nmap", "-O", "-sV", "10.0.0.10"],
        expected_executable="nmap", expected_requires_root=True,
        expected_risk="high",
        user_input="10.0.0.10 isletim sistemi ve servis versiyonlarini tespit et",
    ),
    PipelineTestCase(
        id="OD-03", description="OS guess ile",
        intent=IntentType.OS_DETECTION, target="172.16.0.1",
        params={"osscan_guess": "true"},
        must_contain=["nmap", "-O", "--osscan-guess", "172.16.0.1"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="172.16.0.1 isletim sistemi tahmin et",
    ),
    PipelineTestCase(
        id="OD-04", description="Belirli portlarla OS tespiti",
        intent=IntentType.OS_DETECTION, target="192.168.5.5",
        params={"ports": "22,80,443"},
        must_contain=["nmap", "-O", "-p", "22,80,443", "192.168.5.5"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="192.168.5.5 uzerinde port 22,80,443 ile isletim sistemi tespit et",
    ),
    PipelineTestCase(
        id="OD-05", description="Timing + OS tespiti",
        intent=IntentType.OS_DETECTION, target="10.10.10.10",
        params={"timing": "4"},
        must_contain=["nmap", "-O", "-T4", "10.10.10.10"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="10.10.10.10 isletim sistemini hizli tara",
    ),

    # =========================================================================
    # VULN_SCAN (nmap_vuln_scan) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="VS-01", description="Temel zafiyet taramasi",
        intent=IntentType.VULN_SCAN, target="192.168.1.1", params={},
        must_contain=["nmap", "--script", "vuln", "192.168.1.1"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="192.168.1.1 uzerinde zafiyet taramasi yap",
    ),
    PipelineTestCase(
        id="VS-02", description="Belirli portlarda zafiyet taramasi",
        intent=IntentType.VULN_SCAN, target="10.0.0.1",
        params={"ports": "80,443,8080"},
        must_contain=["nmap", "--script", "vuln", "-p", "80,443,8080", "10.0.0.1"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="10.0.0.1 portlari 80,443,8080 uzerinde zafiyet taramasi yap",
    ),
    PipelineTestCase(
        id="VS-03", description="Timing ile zafiyet taramasi",
        intent=IntentType.VULN_SCAN, target="192.168.2.1",
        params={"timing": "3"},
        must_contain=["nmap", "--script", "vuln", "-T3", "192.168.2.1"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="192.168.2.1 uzerinde T3 hizda zafiyet taramasi yap",
    ),
    PipelineTestCase(
        id="VS-04", description="Ozel script ile zafiyet taramasi",
        intent=IntentType.VULN_SCAN, target="10.0.0.5",
        params={"scripts": "http-vuln-cve2017-5638"},
        must_contain=["nmap", "--script", "http-vuln-cve2017-5638", "10.0.0.5"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="10.0.0.5 uzerinde http-vuln-cve2017-5638 scripti ile tara",
    ),
    PipelineTestCase(
        id="VS-05", description="Port + timing + zafiyet",
        intent=IntentType.VULN_SCAN, target="172.16.0.100",
        params={"ports": "1-1000", "timing": "4"},
        must_contain=["nmap", "--script", "vuln", "-p", "1-1000", "-T4", "172.16.0.100"],
        expected_executable="nmap", expected_requires_root=True,
        user_input="172.16.0.100 ilk 1000 portu hizli zafiyet taramasi yap",
    ),

    # =========================================================================
    # SSL_SCAN (ssl_scan) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="SSL-01", description="Temel SSL taramasi",
        intent=IntentType.SSL_SCAN, target="example.com", params={},
        must_contain=["openssl", "s_client", "-connect", "example.com:443", "-showcerts"],
        expected_executable="openssl", expected_requires_root=False,
        user_input="example.com SSL/TLS sertifika analizi yap",
    ),
    PipelineTestCase(
        id="SSL-02", description="Belirli port ile SSL",
        intent=IntentType.SSL_SCAN, target="secure.example.com",
        params={"port": "8443"},
        must_contain=["openssl", "s_client", "-connect", "secure.example.com:8443", "-showcerts"],
        expected_executable="openssl", expected_requires_root=False,
        user_input="secure.example.com port 8443 SSL sertifika kontrolu yap",
    ),
    PipelineTestCase(
        id="SSL-03", description="TLS versiyon belirterek",
        intent=IntentType.SSL_SCAN, target="mysite.com",
        params={"tls_version": "1.2"},
        must_contain=["openssl", "s_client", "-connect", "mysite.com:443", "-showcerts", "-tls1_2"],
        expected_executable="openssl", expected_requires_root=False,
        user_input="mysite.com TLS 1.2 cipher kontrolu yap",
    ),
    PipelineTestCase(
        id="SSL-04", description="STARTTLS ile",
        intent=IntentType.SSL_SCAN, target="mail.example.com",
        params={"starttls": "smtp", "port": "25"},
        must_contain=["openssl", "s_client", "-connect", "mail.example.com:25", "-showcerts", "-starttls", "smtp"],
        expected_executable="openssl", expected_requires_root=False,
        user_input="mail.example.com port 25 STARTTLS kontrolu yap",
    ),
    PipelineTestCase(
        id="SSL-05", description="SNI servername ile",
        intent=IntentType.SSL_SCAN, target="cdn.example.com",
        params={"servername": "www.example.com"},
        must_contain=["openssl", "s_client", "-connect", "cdn.example.com:443", "-showcerts", "-servername", "www.example.com"],
        expected_executable="openssl", expected_requires_root=False,
        user_input="cdn.example.com SNI kontrol yap",
    ),

    # =========================================================================
    # DNS_LOOKUP (dns_lookup) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="DNS-01", description="Temel DNS sorgusu",
        intent=IntentType.DNS_LOOKUP, target="example.com", params={},
        must_contain=["nslookup", "example.com"],
        expected_executable="nslookup", expected_requires_root=False,
        user_input="example.com DNS kayitlarini sorgula",
    ),
    PipelineTestCase(
        id="DNS-02", description="MX record sorgusu",
        intent=IntentType.DNS_LOOKUP, target="google.com",
        params={"record_type": "MX"},
        must_contain=["nslookup", "-type=MX", "google.com"],
        expected_executable="nslookup", expected_requires_root=False,
        user_input="google.com MX kayitlarini sorgula",
    ),
    PipelineTestCase(
        id="DNS-03", description="Ozel DNS sunucusu ile",
        intent=IntentType.DNS_LOOKUP, target="test.com",
        params={"dns_server": "8.8.8.8"},
        must_contain=["nslookup", "test.com", "8.8.8.8"],
        expected_executable="nslookup", expected_requires_root=False,
        user_input="test.com DNS sorgusu 8.8.8.8 sunucusu ile yap",
    ),
    PipelineTestCase(
        id="DNS-04", description="A record sorgusu",
        intent=IntentType.DNS_LOOKUP, target="github.com",
        params={"record_type": "A"},
        must_contain=["nslookup", "-type=A", "github.com"],
        expected_executable="nslookup", expected_requires_root=False,
        user_input="github.com A kaydi sorgula",
    ),
    PipelineTestCase(
        id="DNS-05", description="NS record + ozel sunucu",
        intent=IntentType.DNS_LOOKUP, target="example.org",
        params={"record_type": "NS", "dns_server": "1.1.1.1"},
        must_contain=["nslookup", "-type=NS", "example.org", "1.1.1.1"],
        expected_executable="nslookup", expected_requires_root=False,
        user_input="example.org NS kayitlarini 1.1.1.1 ile sorgula",
    ),

    # =========================================================================
    # WEB_DIR_ENUM (gobuster_dir) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="WD-01", description="Temel dizin taramasi",
        intent=IntentType.WEB_DIR_ENUM, target="http://target.com", params={},
        must_contain=["gobuster", "dir", "-u", "http://target.com"],
        expected_executable="gobuster", expected_requires_root=False,
        user_input="http://target.com uzerinde dizin taramasi yap",
    ),
    PipelineTestCase(
        id="WD-02", description="Extension ile dizin taramasi",
        intent=IntentType.WEB_DIR_ENUM, target="http://target.com",
        params={"extensions": "php,html,txt"},
        must_contain=["gobuster", "dir", "-u", "http://target.com", "-x", "php,html,txt"],
        expected_executable="gobuster", expected_requires_root=False,
        user_input="http://target.com uzerinde php html txt uzantili dosyalari ara",
    ),
    PipelineTestCase(
        id="WD-03", description="Ozel wordlist ile",
        intent=IntentType.WEB_DIR_ENUM, target="http://example.com",
        params={"wordlist": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"},
        must_contain=["gobuster", "dir", "-u", "http://example.com", "-w", "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"],
        expected_executable="gobuster", expected_requires_root=False,
        user_input="http://example.com uzerinde dirbuster medium wordlist ile tara",
    ),
    PipelineTestCase(
        id="WD-04", description="Thread + extension",
        intent=IntentType.WEB_DIR_ENUM, target="http://10.0.0.1:8080",
        params={"threads": "50", "extensions": "php,asp"},
        must_contain=["gobuster", "dir", "-u", "http://10.0.0.1:8080", "-x", "php,asp", "-t", "50"],
        expected_executable="gobuster", expected_requires_root=False,
        user_input="http://10.0.0.1:8080 uzerinde 50 thread ile php asp dosyalari ara",
    ),
    PipelineTestCase(
        id="WD-05", description="Follow redirect + no TLS",
        intent=IntentType.WEB_DIR_ENUM, target="https://secure.target.com",
        params={"follow_redirect": "true", "no_tls_validation": "true"},
        must_contain=["gobuster", "dir", "-u", "https://secure.target.com"],
        expected_executable="gobuster", expected_requires_root=False,
        user_input="https://secure.target.com dizin taramasi redirect takip et sertifika dogrulama olmadan",
    ),

    # =========================================================================
    # SUBDOMAIN_ENUM (subdomain_enum) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="SUB-01", description="Temel subdomain kesfet",
        intent=IntentType.SUBDOMAIN_ENUM, target="example.com", params={},
        must_contain=["bash", "nslookup", "example.com"],
        expected_executable="bash", expected_requires_root=False,
        user_input="example.com alt alanlarini kesfet",
    ),
    PipelineTestCase(
        id="SUB-02", description="Wordlist ile subdomain",
        intent=IntentType.SUBDOMAIN_ENUM, target="target.com",
        params={"wordlist": "/usr/share/wordlists/subdomains.txt"},
        must_contain=["bash", "nslookup", "target.com", "/usr/share/wordlists/subdomains.txt"],
        expected_executable="bash", expected_requires_root=False,
        user_input="target.com alt alanlarini ozel wordlist ile kesfet",
    ),
    PipelineTestCase(
        id="SUB-03", description="Buyuk domain subdomain",
        intent=IntentType.SUBDOMAIN_ENUM, target="google.com", params={},
        must_contain=["bash", "nslookup", "google.com"],
        expected_executable="bash", expected_requires_root=False,
        user_input="google.com subdomain enumeration yap",
    ),
    PipelineTestCase(
        id="SUB-04", description="Gov domain subdomain",
        intent=IntentType.SUBDOMAIN_ENUM, target="gov.tr", params={},
        must_contain=["bash", "nslookup", "gov.tr"],
        expected_executable="bash", expected_requires_root=False,
        user_input="gov.tr domaininin alt alanlarini tara",
    ),
    PipelineTestCase(
        id="SUB-05", description="Edu domain subdomain",
        intent=IntentType.SUBDOMAIN_ENUM, target="mit.edu", params={},
        must_contain=["bash", "nslookup", "mit.edu"],
        expected_executable="bash", expected_requires_root=False,
        user_input="mit.edu subdomain kesfet",
    ),

    # =========================================================================
    # WEB_VULN_SCAN (web_app_scan / nikto) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="WV-01", description="Temel web zafiyet taramasi",
        intent=IntentType.WEB_VULN_SCAN, target="http://target.com", params={},
        must_contain=["URL=\"$1\"", "curl", "TECH:", "http://target.com"],
        expected_executable="", expected_requires_root=False,
        user_input="http://target.com uzerinde nikto ile zafiyet taramasi yap",
    ),
    PipelineTestCase(
        id="WV-02", description="HTTPS web zafiyet taramasi",
        intent=IntentType.WEB_VULN_SCAN, target="https://secure.target.com", params={},
        must_contain=["URL=\"$1\"", "curl", "TECH:", "https://secure.target.com"],
        expected_executable="", expected_requires_root=False,
        user_input="https://secure.target.com web zafiyetlerini tara",
    ),
    PipelineTestCase(
        id="WV-03", description="IP ile web zafiyet taramasi",
        intent=IntentType.WEB_VULN_SCAN, target="http://192.168.1.100", params={},
        must_contain=["URL=\"$1\"", "curl", "TECH:", "http://192.168.1.100"],
        expected_executable="", expected_requires_root=False,
        user_input="http://192.168.1.100 web sunucu zafiyetlerini tara",
    ),
    PipelineTestCase(
        id="WV-04", description="Portlu web zafiyet taramasi",
        intent=IntentType.WEB_VULN_SCAN, target="http://10.0.0.1:8080", params={},
        must_contain=["URL=\"$1\"", "curl", "TECH:", "http://10.0.0.1:8080"],
        expected_executable="", expected_requires_root=False,
        user_input="http://10.0.0.1:8080 nikto zafiyet tara",
    ),
    PipelineTestCase(
        id="WV-05", description="Subdomain web zafiyet taramasi",
        intent=IntentType.WEB_VULN_SCAN, target="http://api.target.com", params={},
        must_contain=["URL=\"$1\"", "curl", "TECH:", "http://api.target.com"],
        expected_executable="", expected_requires_root=False,
        user_input="http://api.target.com web zafiyetlerini kontrol et",
    ),

    # =========================================================================
    # WHOIS_LOOKUP (whois_lookup) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="WH-01", description="Temel whois sorgusu",
        intent=IntentType.WHOIS_LOOKUP, target="example.com", params={},
        must_contain=["whois", "example.com"],
        expected_executable="whois", expected_requires_root=False,
        user_input="example.com whois bilgilerini getir",
    ),
    PipelineTestCase(
        id="WH-02", description="TR domain whois",
        intent=IntentType.WHOIS_LOOKUP, target="google.com.tr", params={},
        must_contain=["whois", "google.com.tr"],
        expected_executable="whois", expected_requires_root=False,
        user_input="google.com.tr domain bilgilerini sorgula",
    ),
    PipelineTestCase(
        id="WH-03", description="IP whois sorgusu",
        intent=IntentType.WHOIS_LOOKUP, target="8.8.8.8", params={},
        must_contain=["whois", "8.8.8.8"],
        expected_executable="whois", expected_requires_root=False,
        user_input="8.8.8.8 IP bilgilerini whois ile sorgula",
    ),
    PipelineTestCase(
        id="WH-04", description="Org domain whois",
        intent=IntentType.WHOIS_LOOKUP, target="wikipedia.org", params={},
        must_contain=["whois", "wikipedia.org"],
        expected_executable="whois", expected_requires_root=False,
        user_input="wikipedia.org alan adi bilgilerini getir",
    ),
    PipelineTestCase(
        id="WH-05", description="Net domain whois",
        intent=IntentType.WHOIS_LOOKUP, target="cloudflare.net", params={},
        must_contain=["whois", "cloudflare.net"],
        expected_executable="whois", expected_requires_root=False,
        user_input="cloudflare.net whois sorgula",
    ),

    # =========================================================================
    # BRUTE_FORCE_SSH (hydra_ssh) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="BFS-01", description="Temel SSH brute force",
        intent=IntentType.BRUTE_FORCE_SSH, target="192.168.1.100",
        params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt"},
        must_contain=["hydra", "-l", "admin", "-P", "/usr/share/wordlists/rockyou.txt", "ssh://192.168.1.100"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="192.168.1.100 SSH admin kullanicisi ile brute force yap",
    ),
    PipelineTestCase(
        id="BFS-02", description="Ozel port SSH brute force",
        intent=IntentType.BRUTE_FORCE_SSH, target="10.0.0.5",
        params={"username": "root", "wordlist": "/usr/share/wordlists/rockyou.txt", "port": "2222"},
        must_contain=["hydra", "-l", "root", "-P", "-s", "2222", "ssh://10.0.0.5"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="10.0.0.5 port 2222 root kullanicisi ile SSH brute force",
    ),
    PipelineTestCase(
        id="BFS-03", description="Thread ile SSH brute force",
        intent=IntentType.BRUTE_FORCE_SSH, target="172.16.0.1",
        params={"username": "user", "wordlist": "/tmp/passwords.txt", "threads": "16"},
        must_contain=["hydra", "-l", "user", "-P", "/tmp/passwords.txt", "-t", "16", "ssh://172.16.0.1"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="172.16.0.1 user ile 16 thread SSH brute force yap",
    ),
    PipelineTestCase(
        id="BFS-04", description="Verbose SSH brute force",
        intent=IntentType.BRUTE_FORCE_SSH, target="192.168.0.50",
        params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt", "verbose": "true"},
        must_contain=["hydra", "-l", "admin", "-P", "-V", "ssh://192.168.0.50"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="192.168.0.50 admin SSH brute force detayli cikti ile",
    ),
    PipelineTestCase(
        id="BFS-05", description="Tam parametreli SSH brute force",
        intent=IntentType.BRUTE_FORCE_SSH, target="10.10.10.10",
        params={"username": "test", "wordlist": "/opt/wordlist.txt", "port": "22", "threads": "8", "verbose": "true"},
        must_contain=["hydra", "-l", "test", "-P", "/opt/wordlist.txt", "-t", "8", "-V", "ssh://10.10.10.10"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="10.10.10.10 test kullanici 8 thread port 22 detayli SSH brute force",
    ),

    # =========================================================================
    # BRUTE_FORCE_HTTP (hydra_http) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="BFH-01", description="Temel HTTP brute force",
        intent=IntentType.BRUTE_FORCE_HTTP, target="192.168.1.1",
        params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt",
                "form_path": "/login", "form_params": "user=^USER^&pass=^PASS^",
                "fail_string": "Invalid"},
        must_contain=["hydra", "-l", "admin", "-P", "192.168.1.1", "http-form-post"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="192.168.1.1 HTTP login admin brute force yap",
    ),
    PipelineTestCase(
        id="BFH-02", description="Ozel port HTTP brute force",
        intent=IntentType.BRUTE_FORCE_HTTP, target="10.0.0.1",
        params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt",
                "form_path": "/login", "form_params": "u=^USER^&p=^PASS^",
                "fail_string": "fail", "port": "8080"},
        must_contain=["hydra", "-l", "admin", "-P", "-s", "8080", "10.0.0.1", "http-form-post"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="10.0.0.1 port 8080 HTTP form brute force admin",
    ),
    PipelineTestCase(
        id="BFH-03", description="Thread ile HTTP brute force",
        intent=IntentType.BRUTE_FORCE_HTTP, target="192.168.2.1",
        params={"username": "user", "wordlist": "/tmp/pass.txt",
                "form_path": "/auth", "form_params": "login=^USER^&password=^PASS^",
                "fail_string": "error", "threads": "32"},
        must_contain=["hydra", "-l", "user", "-P", "/tmp/pass.txt", "-t", "32", "192.168.2.1", "http-form-post"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="192.168.2.1 HTTP auth 32 thread brute force",
    ),
    PipelineTestCase(
        id="BFH-04", description="GET metodu ile HTTP brute force",
        intent=IntentType.BRUTE_FORCE_HTTP, target="10.0.0.5",
        params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt",
                "form_path": "/admin", "form_params": "user=^USER^&pass=^PASS^",
            "fail_string": "denied", "method": "http-get"},
        must_contain=["hydra", "-l", "admin", "-P", "10.0.0.5", "http-get"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="10.0.0.5 HTTP GET form brute force admin",
    ),
    PipelineTestCase(
        id="BFH-05", description="Minimal HTTP brute force",
        intent=IntentType.BRUTE_FORCE_HTTP, target="target.local",
        params={"username": "root", "wordlist": "/usr/share/wordlists/rockyou.txt",
                "form_path": "/login", "form_params": "u=^USER^&p=^PASS^",
                "fail_string": "wrong"},
        must_contain=["hydra", "-l", "root", "-P", "target.local", "http-form-post"],
        expected_executable="hydra", expected_requires_root=False,
        user_input="target.local HTTP login root brute force",
    ),

    # =========================================================================
    # SQL_INJECTION (sqlmap_scan) — 5 senaryo
    # =========================================================================
    PipelineTestCase(
        id="SQL-01", description="Temel SQL injection testi",
        intent=IntentType.SQL_INJECTION, target="http://target.com/page?id=1", params={},
        must_contain=["sqlmap", "-u", "http://target.com/page?id=1", "--batch"],
        expected_executable="sqlmap", expected_requires_root=False,
        user_input="http://target.com/page?id=1 SQL injection testi yap",
    ),
    PipelineTestCase(
        id="SQL-02", description="Level + risk ile SQLi",
        intent=IntentType.SQL_INJECTION, target="http://vuln.com/search?q=test",
        params={"level": "5", "risk": "3"},
        must_contain=["sqlmap", "-u", "http://vuln.com/search?q=test", "--batch", "--level", "5", "--risk", "3"],
        expected_executable="sqlmap", expected_requires_root=False,
        user_input="http://vuln.com/search?q=test agresif SQL injection testi yap",
    ),
    PipelineTestCase(
        id="SQL-03", description="DBS dump ile SQLi",
        intent=IntentType.SQL_INJECTION, target="http://target.com/view?id=5",
        params={"dbs": "true"},
        must_contain=["sqlmap", "-u", "http://target.com/view?id=5", "--batch", "--dbs"],
        expected_executable="sqlmap", expected_requires_root=False,
        user_input="http://target.com/view?id=5 veritabanlarini listele SQL injection ile",
    ),
    PipelineTestCase(
        id="SQL-04", description="Forms ile SQLi",
        intent=IntentType.SQL_INJECTION, target="http://site.com/login",
        params={"forms": "true"},
        must_contain=["sqlmap", "-u", "http://site.com/login", "--batch", "--forms"],
        expected_executable="sqlmap", expected_requires_root=False,
        user_input="http://site.com/login formlari SQL injection ile test et",
    ),
    PipelineTestCase(
        id="SQL-05", description="Thread ile SQLi",
        intent=IntentType.SQL_INJECTION, target="http://app.com/api?uid=1",
        params={"threads": "10", "level": "3"},
        must_contain=["sqlmap", "-u", "http://app.com/api?uid=1", "--batch", "--level", "3", "--threads", "10"],
        expected_executable="sqlmap", expected_requires_root=False,
        user_input="http://app.com/api?uid=1 SQL injection 10 thread level 3 test",
    ),
]


# =============================================================================
# RESULT STRUCTURES
# =============================================================================
@dataclass
class CaseResult:
    id: str
    description: str
    intent: str
    success: bool
    command_produced: str
    errors: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class ToolSummary:
    tool_prefix: str
    total: int = 0
    passed: int = 0
    failed: int = 0

    @property
    def accuracy(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0


# =============================================================================
# RUNNER
# =============================================================================

class PipelineAccuracyRunner:
    """Deterministic pipeline dogruluk testi."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._coordinator = SentinelCoordinator()
        self.results: List[CaseResult] = []

    def run_deterministic(self, cases: List[PipelineTestCase]) -> List[CaseResult]:
        """Her test case'i deterministic pipeline ile calistir."""
        self.results = []
        for tc in cases:
            result = self._run_single(tc)
            self.results.append(result)
            status = "PASS" if result.success else "FAIL"
            if self.verbose or not result.success:
                print(f"  [{status}] {tc.id}: {tc.description}")
                if not result.success:
                    for err in result.errors:
                        print(f"         -> {err}")
                    print(f"         -> Komut: {result.command_produced}")
        return self.results

    def _run_single(self, tc: PipelineTestCase) -> CaseResult:
        errors: List[str] = []
        cmd_str = ""

        t0 = time.monotonic()
        try:
            # 1. build_execution_kwargs
            exec_kwargs = build_execution_kwargs(tc.intent, tc.target, tc.params)
            if not exec_kwargs:
                errors.append("build_execution_kwargs bos sonuc dondurdu")
                return CaseResult(
                    id=tc.id, description=tc.description,
                    intent=tc.intent.value, success=False,
                    command_produced="", errors=errors,
                )

            # 2. Execution tool'u bul
            tool_id = get_execution_tool_id(tc.intent)
            if not tool_id:
                errors.append(f"Execution tool bulunamadi: {tc.intent.value}")
                return CaseResult(
                    id=tc.id, description=tc.description,
                    intent=tc.intent.value, success=False,
                    command_produced="", errors=errors,
                )

            integrated_tool = self._coordinator.manager.get_tool(tool_id)
            if not integrated_tool:
                errors.append(f"ToolManager'da tool bulunamadi: {tool_id}")
                return CaseResult(
                    id=tc.id, description=tc.description,
                    intent=tc.intent.value, success=False,
                    command_produced="", errors=errors,
                )

            # 3. build_command
            cmd_list = integrated_tool.tool.build_command(**exec_kwargs)
            if not cmd_list:
                errors.append("build_command bos liste dondurdu")
                return CaseResult(
                    id=tc.id, description=tc.description,
                    intent=tc.intent.value, success=False,
                    command_produced="", errors=errors,
                )

            cmd_str = " ".join(cmd_list)

            # 4. Executable kontrol
            if tc.expected_executable and cmd_list[0] != tc.expected_executable:
                errors.append(
                    f"Executable yanlis: beklenen={tc.expected_executable}, gercek={cmd_list[0]}"
                )

            # 5. must_contain kontrolu substring bazli yapilir.
            # Bazi komutlar URI/token birlesik formatta olabilir (orn: ssh://host).
            for fragment in tc.must_contain:
                if fragment not in cmd_str:
                    errors.append(f"EKSIK: '{fragment}' komutta bulunamadi")

            # 6. must_not_contain kontrol
            for fragment in tc.must_not_contain:
                if fragment in cmd_str:
                    errors.append(f"OLMAMALI: '{fragment}' komutta bulundu")

            # 7. Dinamik requires_root kontrol
            if tc.expected_requires_root is not None:
                actual_requires_root = bool(_ROOT_FLAGS.intersection(cmd_list))
                if actual_requires_root != tc.expected_requires_root:
                    errors.append(
                        f"requires_root yanlis: beklenen={tc.expected_requires_root}, gercek={actual_requires_root}"
                    )

        except Exception as exc:
            errors.append(f"Exception: {exc}")

        elapsed_ms = (time.monotonic() - t0) * 1000

        return CaseResult(
            id=tc.id,
            description=tc.description,
            intent=tc.intent.value,
            success=len(errors) == 0,
            command_produced=cmd_str,
            errors=errors,
            latency_ms=elapsed_ms,
        )


# =============================================================================
# REPORTING
# =============================================================================

def print_report(results: List[CaseResult]) -> None:
    """Ozet rapor yazdir."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    accuracy = (passed / total * 100) if total else 0

    # Tool bazli ozet
    tool_summaries: Dict[str, ToolSummary] = {}
    for r in results:
        prefix = r.id.rsplit("-", 1)[0]
        if prefix not in tool_summaries:
            tool_summaries[prefix] = ToolSummary(tool_prefix=prefix)
        tool_summaries[prefix].total += 1
        if r.success:
            tool_summaries[prefix].passed += 1
        else:
            tool_summaries[prefix].failed += 1

    print("\n" + "=" * 70)
    print(f"  PIPELINE DOGRULUK RAPORU")
    print("=" * 70)
    print(f"  Toplam: {total}  |  Basarili: {passed}  |  Basarisiz: {failed}  |  Dogruluk: {accuracy:.1f}%")
    print("-" * 70)
    print(f"  {'Tool':<12} {'Toplam':>8} {'Basarili':>10} {'Basarisiz':>10} {'Dogruluk':>10}")
    print("-" * 70)
    for prefix in sorted(tool_summaries.keys()):
        ts = tool_summaries[prefix]
        print(f"  {ts.tool_prefix:<12} {ts.total:>8} {ts.passed:>10} {ts.failed:>10} {ts.accuracy:>9.1f}%")
    print("=" * 70)

    # Basarisiz test detaylari
    failed_results = [r for r in results if not r.success]
    if failed_results:
        print(f"\n  BASARISIZ TESTLER ({len(failed_results)}):")
        print("-" * 70)
        for r in failed_results:
            print(f"  [{r.id}] {r.description}")
            print(f"         Komut: {r.command_produced}")
            for err in r.errors:
                print(f"         -> {err}")
        print()


def save_json_report(results: List[CaseResult], output_path: str) -> None:
    """JSON rapor kaydet."""
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "accuracy_pct": round(
            sum(1 for r in results if r.success) / len(results) * 100, 2
        ) if results else 0,
        "results": [asdict(r) for r in results],
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON rapor kaydedildi: {output_path}")


def save_markdown_report(results: List[CaseResult], output_path: str) -> None:
    """Markdown rapor kaydet."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    accuracy = (passed / total * 100) if total else 0

    lines = [
        f"# Pipeline Dogruluk Raporu",
        f"",
        f"**Tarih:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Toplam:** {total} | **Basarili:** {passed} | **Dogruluk:** {accuracy:.1f}%",
        f"",
        f"## Tool Bazli Sonuclar",
        f"",
        f"| Tool | Toplam | Basarili | Dogruluk |",
        f"|------|--------|----------|----------|",
    ]

    tool_summaries: Dict[str, ToolSummary] = {}
    for r in results:
        prefix = r.id.rsplit("-", 1)[0]
        if prefix not in tool_summaries:
            tool_summaries[prefix] = ToolSummary(tool_prefix=prefix)
        tool_summaries[prefix].total += 1
        if r.success:
            tool_summaries[prefix].passed += 1
        else:
            tool_summaries[prefix].failed += 1

    for prefix in sorted(tool_summaries.keys()):
        ts = tool_summaries[prefix]
        lines.append(f"| {ts.tool_prefix} | {ts.total} | {ts.passed} | {ts.accuracy:.1f}% |")

    # Failed cases
    failed_results = [r for r in results if not r.success]
    if failed_results:
        lines.extend([
            f"",
            f"## Basarisiz Testler",
            f"",
        ])
        for r in failed_results:
            lines.append(f"### [{r.id}] {r.description}")
            lines.append(f"- **Komut:** `{r.command_produced}`")
            for err in r.errors:
                lines.append(f"- {err}")
            lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Markdown rapor kaydedildi: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Pipeline Dogruluk Testi")
    parser.add_argument("--mode", choices=["deterministic", "full"], default="deterministic",
                        help="Test modu: deterministic (LLM yok) veya full (Ollama gerekli)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Tum sonuclari goster")
    parser.add_argument("--output", "-o", default=None,
                        help="JSON cikti dosyasi (ornek: temp/pipeline_accuracy.json)")
    parser.add_argument("--markdown", "-m", default=None,
                        help="Markdown cikti dosyasi (ornek: temp/pipeline_accuracy.md)")
    parser.add_argument("--filter", "-f", default=None,
                        help="Belirli tool prefix'i filtrele (ornek: PS, DNS, BFS)")
    args = parser.parse_args()

    cases = TEST_CASES
    if args.filter:
        prefixes = [p.strip().upper() for p in args.filter.split(",")]
        cases = [tc for tc in TEST_CASES if any(tc.id.startswith(p) for p in prefixes)]
        if not cases:
            print(f"  HATA: '{args.filter}' filtresiyle eslesen test bulunamadi.")
            sys.exit(1)

    if args.mode == "full":
        print("  UYARI: Full mode henuz implemente edilmedi. Deterministic mode kullaniliyor.")

    print(f"\n  Pipeline Dogruluk Testi Basliyor...")
    print(f"  Mod: {args.mode} | Test sayisi: {len(cases)}")
    print("-" * 70)

    runner = PipelineAccuracyRunner(verbose=args.verbose)
    results = runner.run_deterministic(cases)

    print_report(results)

    timestamp = int(time.time())
    if args.output:
        save_json_report(results, args.output)
    else:
        save_json_report(results, f"temp/pipeline_accuracy_{timestamp}.json")

    if args.markdown:
        save_markdown_report(results, args.markdown)
    else:
        save_markdown_report(results, f"temp/pipeline_accuracy_{timestamp}.md")

    # Exit code: basarisiz test varsa 1
    passed = sum(1 for r in results if r.success)
    if passed < len(results):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
