"""Prompt-to-Command End-to-End Test Suite

50+ senaryo: Türkçe/İngilizce promptlar → Intent → Tool → FinalCommand → AIResponse.
LLM çağrısı yapılmaz; Intent doğrudan simüle edilir ve pipeline'ın geri kalanı
gerçek kodla test edilir (build_execution_kwargs → build_command → _v2_to_response).

Bu test, kullanıcının UI'da yaşayacağı tam akışı doğrular:
  Prompt → process_v2() → _v2_to_response() → AIResponse.command

Kapsam:
  - HOST_DISCOVERY (4 senaryo)
  - PORT_SCAN (8 senaryo)
  - SERVICE_DETECTION (4 senaryo)
  - OS_DETECTION (3 senaryo)
  - VULN_SCAN (3 senaryo)
  - SSL_SCAN (4 senaryo)
  - WEB_DIR_ENUM (4 senaryo)
  - WEB_VULN_SCAN (3 senaryo)
  - DNS_LOOKUP (4 senaryo)
  - SUBDOMAIN_ENUM (2 senaryo)
  - WHOIS_LOOKUP (2 senaryo)
  - BRUTE_FORCE_SSH (3 senaryo)
  - SQL_INJECTION (2 senaryo)
  - INFO_QUERY (2 senaryo)
  - UNKNOWN (2 senaryo)
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

import pytest

from src.ai.schemas import (
    FinalCommand,
    Intent,
    IntentType,
    RiskLevel,
)
from src.ai.schemas_legacy import AIResponse, ToolCommand
from src.ai.orchestrator import AIOrchestrator
from src.ai.tool_registry import (
    build_execution_kwargs,
    get_execution_tool_id,
)
from src.core.tool_base import TOOL_CLASS_MAP
from src.core.platform_utils import get_shell, get_shell_exec_flag


# =============================================================================
# SCENARIO DATA MODEL
# =============================================================================


@dataclass
class PromptScenario:
    """Tek bir test senaryosu."""

    id: str                           # Kolay okunur test ID
    prompt: str                       # Kullanıcının yazacağı doğal dil
    intent_type: IntentType           # Beklenen intent
    target: str                       # Beklenen hedef
    params: Dict[str, Any] = field(default_factory=dict)

    # Beklenen komut çıktısı
    expected_executable: str = ""     # Çıktıdaki executable
    expected_args_contain: List[str] = field(default_factory=list)
    expected_args_not_contain: List[str] = field(default_factory=list)
    expected_target_in_cmd: bool = True  # Target komutta var mı?
    expected_requires_root: Optional[bool] = None
    expected_risk_min: Optional[RiskLevel] = None

    # İnfo/unknown senaryoları için: komut üretilmemeli
    expect_no_command: bool = False


# =============================================================================
# 50+ SCENARIO DEFINITIONS
# =============================================================================


SCENARIOS: List[PromptScenario] = [

    # =========================================================================
    # HOST DISCOVERY (4)
    # =========================================================================

    PromptScenario(
        id="host_discovery_basic",
        prompt="192.168.1.0/24 ağını tara",
        intent_type=IntentType.HOST_DISCOVERY,
        target="192.168.1.0/24",
        expected_executable="nmap",
        expected_args_contain=["-sn", "192.168.1.0/24"],
    ),
    PromptScenario(
        id="host_discovery_with_timing",
        prompt="10.0.0.0/24 ağını hızlı tara T4 ile",
        intent_type=IntentType.HOST_DISCOVERY,
        target="10.0.0.0/24",
        params={"timing": 4},
        expected_executable="nmap",
        expected_args_contain=["-sn", "-T4", "10.0.0.0/24"],
    ),
    PromptScenario(
        id="host_discovery_exclude",
        prompt="192.168.1.0/24 ağını tara ama 192.168.1.1 hariç tut",
        intent_type=IntentType.HOST_DISCOVERY,
        target="192.168.1.0/24",
        params={"exclude": "192.168.1.1"},
        expected_executable="nmap",
        expected_args_contain=["-sn", "--exclude", "192.168.1.1"],
    ),
    PromptScenario(
        id="host_discovery_no_dns",
        prompt="10.10.10.0/24 hostlarını bul, DNS çözümleme yapma",
        intent_type=IntentType.HOST_DISCOVERY,
        target="10.10.10.0/24",
        params={"no_dns": True},
        expected_executable="nmap",
        expected_args_contain=["-sn", "-n"],
    ),

    # =========================================================================
    # PORT SCAN (8)
    # =========================================================================

    PromptScenario(
        id="port_scan_basic",
        prompt="192.168.1.1 portlarını tara",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.1",
        expected_executable="nmap",
        expected_args_contain=["-sT", "192.168.1.1"],
    ),
    PromptScenario(
        id="port_scan_specific_ports",
        prompt="10.0.0.1 üzerinde 80 ve 443 portlarını tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"ports": "80,443"},
        expected_executable="nmap",
        expected_args_contain=["-sT", "-p", "80,443", "10.0.0.1"],
    ),
    PromptScenario(
        id="port_scan_range",
        prompt="192.168.0.14 ilk 1500 portunu tara",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.0.14",
        params={"ports": "1-1500"},
        expected_executable="nmap",
        expected_args_contain=["-p", "1-1500", "192.168.0.14"],
    ),
    PromptScenario(
        id="port_scan_top_ports",
        prompt="192.168.0.8 ilk 100 portunu tara",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.0.8",
        params={"top_ports": 100},
        expected_executable="nmap",
        expected_args_contain=["--top-ports", "100"],

    ),
    PromptScenario(
        id="port_scan_with_service_detection",
        prompt="192.168.0.14 port ve versiyon bilgisi taraması yap",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.0.14",
        params={"service_detection": True, "ports": "1-1500"},
        expected_executable="nmap",
        expected_args_contain=["-sT", "-sV", "-p", "1-1500"],
    ),
    PromptScenario(
        id="port_scan_fast_timing",
        prompt="10.0.0.5 hızlı port scan yap T4 ile DNS çözümleme yapma",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.5",
        params={"timing": 4, "no_dns": True},
        expected_executable="nmap",
        expected_args_contain=["-T4", "-n"],
    ),
    PromptScenario(
        id="port_scan_syn_scan",
        prompt="192.168.1.1 SYN taraması yap detaylı çıktı ver",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"scan_type": "sS", "verbose": True},
        expected_executable="nmap",
        expected_args_contain=["-sS", "-v"],
        expected_requires_root=True,
    ),
    PromptScenario(
        id="port_scan_aggressive",
        prompt="10.0.0.1 üzerinde agresif tarama başlat",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"aggressive": True},
        expected_executable="nmap",
        expected_args_contain=["-A", "10.0.0.1"],
        expected_requires_root=True,
    ),

    # =========================================================================
    # SERVICE DETECTION (4)
    # =========================================================================

    PromptScenario(
        id="service_detection_basic",
        prompt="192.168.1.10 servislerini tespit et",
        intent_type=IntentType.SERVICE_DETECTION,
        target="192.168.1.10",
        expected_executable="nmap",
        expected_args_contain=["-sV", "--version-intensity", "5"],
    ),
    PromptScenario(
        id="service_detection_ports",
        prompt="10.0.0.1 80 ve 443 portlarındaki servisleri bul",
        intent_type=IntentType.SERVICE_DETECTION,
        target="10.0.0.1",
        params={"ports": "80,443"},
        expected_executable="nmap",
        expected_args_contain=["-sV", "-p", "80,443"],
    ),
    PromptScenario(
        id="service_detection_light",
        prompt="192.168.5.1 servisleri hızlıca tespit et",
        intent_type=IntentType.SERVICE_DETECTION,
        target="192.168.5.1",
        params={"version_mode": "light"},
        expected_executable="nmap",
        expected_args_contain=["-sV", "--version-light"],
    ),
    PromptScenario(
        id="service_detection_high_intensity",
        prompt="172.16.0.1 tüm versiyon bilgilerini bul",
        intent_type=IntentType.SERVICE_DETECTION,
        target="172.16.0.1",
        params={"version_intensity": 9},
        expected_executable="nmap",
        expected_args_contain=["-sV", "--version-intensity", "9"],
    ),

    # =========================================================================
    # OS DETECTION (3)
    # =========================================================================

    PromptScenario(
        id="os_detection_basic",
        prompt="192.168.1.1 işletim sistemini tespit et",
        intent_type=IntentType.OS_DETECTION,
        target="192.168.1.1",
        expected_executable="nmap",
        expected_args_contain=["-O", "192.168.1.1"],
        expected_requires_root=True,
    ),
    PromptScenario(
        id="os_detection_guess",
        prompt="10.0.0.1 OS tespiti yap, tahmin modu açık",
        intent_type=IntentType.OS_DETECTION,
        target="10.0.0.1",
        params={"osscan_guess": True},
        expected_executable="nmap",
        expected_args_contain=["-O", "--osscan-guess"],
        expected_requires_root=True,
    ),
    PromptScenario(
        id="os_detection_with_service",
        prompt="172.16.0.5 OS ve servis tespiti birlikte yap",
        intent_type=IntentType.OS_DETECTION,
        target="172.16.0.5",
        params={"service_detection": True},
        expected_executable="nmap",
        expected_args_contain=["-O", "-sV"],
        expected_requires_root=True,
    ),

    # =========================================================================
    # VULN SCAN (3)
    # =========================================================================

    PromptScenario(
        id="vuln_scan_basic",
        prompt="192.168.1.1 zafiyet taraması yap",
        intent_type=IntentType.VULN_SCAN,
        target="192.168.1.1",
        expected_executable="nmap",
        expected_args_contain=["-sS", "--script", "vuln"],
        expected_requires_root=True,
        expected_risk_min=RiskLevel.HIGH,
    ),
    PromptScenario(
        id="vuln_scan_specific_ports",
        prompt="10.0.0.1 80 ve 443 portlarında zafiyet tara",
        intent_type=IntentType.VULN_SCAN,
        target="10.0.0.1",
        params={"ports": "80,443"},
        expected_executable="nmap",
        expected_args_contain=["--script", "vuln", "-p", "80,443"],
    ),
    PromptScenario(
        id="vuln_scan_with_timing",
        prompt="172.16.0.1 zafiyet taraması T3 hızında yap",
        intent_type=IntentType.VULN_SCAN,
        target="172.16.0.1",
        params={"timing": 3},
        expected_executable="nmap",
        expected_args_contain=["--script", "vuln", "-T3"],
    ),

    # =========================================================================
    # SSL SCAN (4)
    # =========================================================================

    PromptScenario(
        id="ssl_scan_basic",
        prompt="example.com SSL sertifikasını analiz et",
        intent_type=IntentType.SSL_SCAN,
        target="example.com",
        expected_executable="openssl",
        expected_args_contain=["s_client", "-connect", "example.com:443", "-showcerts"],
    ),
    PromptScenario(
        id="ssl_scan_custom_port",
        prompt="10.0.0.1 8443 portundaki SSL'i kontrol et",
        intent_type=IntentType.SSL_SCAN,
        target="10.0.0.1",
        params={"port": 8443},
        expected_executable="openssl",
        expected_args_contain=["s_client", "-connect", "10.0.0.1:8443"],
    ),
    PromptScenario(
        id="ssl_scan_tls13",
        prompt="example.com TLS 1.3 desteğini kontrol et",
        intent_type=IntentType.SSL_SCAN,
        target="example.com",
        params={"tls_version": "1.3"},
        expected_executable="openssl",
        expected_args_contain=["-tls1_3"],
    ),
    PromptScenario(
        id="ssl_scan_starttls",
        prompt="mail.example.com SMTP üzerinde STARTTLS kontrol et",
        intent_type=IntentType.SSL_SCAN,
        target="mail.example.com",
        params={"starttls": "smtp"},
        expected_executable="openssl",
        expected_args_contain=["-starttls", "smtp"],
    ),

    # =========================================================================
    # WEB DIR ENUM (4)
    # =========================================================================

    PromptScenario(
        id="web_dir_basic",
        prompt="http://example.com dizin taraması yap",
        intent_type=IntentType.WEB_DIR_ENUM,
        target="http://example.com",
        expected_executable="gobuster",
        expected_args_contain=["dir", "-u", "http://example.com", "-w"],
    ),
    PromptScenario(
        id="web_dir_extensions",
        prompt="http://target.com dizin tara, php ve html dosyalarını ara",
        intent_type=IntentType.WEB_DIR_ENUM,
        target="http://target.com",
        params={"extensions": "php,html"},
        expected_executable="gobuster",
        expected_args_contain=["-x", "php,html"],
    ),
    PromptScenario(
        id="web_dir_threads",
        prompt="https://site.com dizin taraması 50 thread ile yap",
        intent_type=IntentType.WEB_DIR_ENUM,
        target="https://site.com",
        params={"threads": 50},
        expected_executable="gobuster",
        expected_args_contain=["-t", "50"],
    ),
    PromptScenario(
        id="web_dir_full",
        prompt="http://webapp.local dizin tara php,txt uzantıları 30 thread",
        intent_type=IntentType.WEB_DIR_ENUM,
        target="http://webapp.local",
        params={"extensions": "php,txt", "threads": 30},
        expected_executable="gobuster",
        expected_args_contain=["dir", "-u", "http://webapp.local", "-x", "php,txt", "-t", "30"],
    ),

    # =========================================================================
    # WEB VULN SCAN (3)
    # =========================================================================

    PromptScenario(
        id="web_vuln_basic",
        prompt="http://example.com web zafiyet taraması yap",
        intent_type=IntentType.WEB_VULN_SCAN,
        target="http://example.com",
        expected_executable=get_shell(),  # powershell.exe on Windows, bash on Linux
        expected_args_contain=[get_shell_exec_flag()],
    ),
    PromptScenario(
        id="web_vuln_https",
        prompt="https://secure.example.com web teknolojilerini tespit et",
        intent_type=IntentType.WEB_VULN_SCAN,
        target="https://secure.example.com",
        expected_executable=get_shell(),
    ),
    PromptScenario(
        id="web_vuln_ip",
        prompt="http://192.168.1.100 web taraması yap",
        intent_type=IntentType.WEB_VULN_SCAN,
        target="http://192.168.1.100",
        expected_executable=get_shell(),
    ),

    # =========================================================================
    # DNS LOOKUP (4)
    # =========================================================================

    PromptScenario(
        id="dns_basic",
        prompt="google.com DNS sorgusu yap",
        intent_type=IntentType.DNS_LOOKUP,
        target="google.com",
        expected_executable="nslookup",
        expected_args_contain=["-type=A", "google.com"],
    ),
    PromptScenario(
        id="dns_mx",
        prompt="example.com MX kayıtlarını sorgula",
        intent_type=IntentType.DNS_LOOKUP,
        target="example.com",
        params={"record_type": "MX"},
        expected_executable="nslookup",
        expected_args_contain=["-type=MX", "example.com"],
    ),
    PromptScenario(
        id="dns_ns",
        prompt="example.com NS sunucularını bul",
        intent_type=IntentType.DNS_LOOKUP,
        target="example.com",
        params={"record_type": "NS"},
        expected_executable="nslookup",
        expected_args_contain=["-type=NS"],
    ),
    PromptScenario(
        id="dns_custom_server",
        prompt="example.com DNS sorgusu 8.8.8.8 sunucusundan yap",
        intent_type=IntentType.DNS_LOOKUP,
        target="example.com",
        params={"dns_server": "8.8.8.8"},
        expected_executable="nslookup",
        expected_args_contain=["example.com", "8.8.8.8"],
    ),

    # =========================================================================
    # SUBDOMAIN ENUM (2)
    # =========================================================================

    PromptScenario(
        id="subdomain_basic",
        prompt="example.com alt alan adlarını keşfet",
        intent_type=IntentType.SUBDOMAIN_ENUM,
        target="example.com",
        expected_executable="bash",
        expected_args_contain=["-c"],
    ),
    PromptScenario(
        id="subdomain_wordlist",
        prompt="target.com subdomain taraması wordlist ile yap",
        intent_type=IntentType.SUBDOMAIN_ENUM,
        target="target.com",
        params={"wordlist": "/tmp/subdomains.txt"},
        expected_executable="bash",
    ),

    # =========================================================================
    # WHOIS LOOKUP (2)
    # =========================================================================

    PromptScenario(
        id="whois_basic",
        prompt="example.com whois bilgisini sorgula",
        intent_type=IntentType.WHOIS_LOOKUP,
        target="example.com",
        expected_executable="whois",
        expected_args_contain=["example.com"],
    ),
    PromptScenario(
        id="whois_ip",
        prompt="8.8.8.8 whois sorgusu yap",
        intent_type=IntentType.WHOIS_LOOKUP,
        target="8.8.8.8",
        expected_executable="whois",
        expected_args_contain=["8.8.8.8"],
    ),

    # =========================================================================
    # BRUTE FORCE SSH (3)
    # =========================================================================

    PromptScenario(
        id="brute_ssh_basic",
        prompt="10.0.0.1 SSH brute force admin kullanıcısı rockyou.txt",
        intent_type=IntentType.BRUTE_FORCE_SSH,
        target="10.0.0.1",
        params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt"},
        expected_executable="hydra",
        expected_args_contain=["-l", "admin", "-P", "/usr/share/wordlists/rockyou.txt"],
    ),
    PromptScenario(
        id="brute_ssh_custom_port",
        prompt="10.0.0.5 SSH brute force root 2222 portu",
        intent_type=IntentType.BRUTE_FORCE_SSH,
        target="10.0.0.5",
        params={"username": "root", "wordlist": "/tmp/passwords.txt", "port": 2222},
        expected_executable="hydra",
        expected_args_contain=["-l", "root", "-s", "2222"],
    ),
    PromptScenario(
        id="brute_ssh_threads",
        prompt="192.168.1.50 SSH saldırısı admin 16 thread",
        intent_type=IntentType.BRUTE_FORCE_SSH,
        target="192.168.1.50",
        params={"username": "admin", "wordlist": "/tmp/pass.txt", "threads": 16},
        expected_executable="hydra",
        expected_args_contain=["-t", "16"],
    ),

    # =========================================================================
    # SQL INJECTION (2)
    # =========================================================================

    PromptScenario(
        id="sql_injection_basic",
        prompt="http://example.com/page?id=1 SQL injection testi yap",
        intent_type=IntentType.SQL_INJECTION,
        target="http://example.com/page?id=1",
        expected_executable="sqlmap",
        expected_args_contain=["--batch", "-u", "http://example.com/page?id=1"],
    ),
    PromptScenario(
        id="sql_injection_aggressive",
        prompt="http://target.com/login SQL injection seviye 5 risk 3",
        intent_type=IntentType.SQL_INJECTION,
        target="http://target.com/login",
        params={"level": 5, "risk": 3},
        expected_executable="sqlmap",
        expected_args_contain=["--batch", "--level", "5", "--risk", "3"],
    ),

    # =========================================================================
    # INFO_QUERY (2) — komut üretilmemeli
    # =========================================================================

    PromptScenario(
        id="info_query_what_is_nmap",
        prompt="nmap nedir?",
        intent_type=IntentType.INFO_QUERY,
        target="",
        expect_no_command=True,
    ),
    PromptScenario(
        id="info_query_how_to_scan",
        prompt="port taraması nasıl yapılır?",
        intent_type=IntentType.INFO_QUERY,
        target="",
        expect_no_command=True,
    ),

    # =========================================================================
    # UNKNOWN (2) — clarification istemeli
    # =========================================================================

    PromptScenario(
        id="unknown_vague",
        prompt="birşeyler yap",
        intent_type=IntentType.UNKNOWN,
        target="",
        expect_no_command=True,
    ),
    PromptScenario(
        id="unknown_offtopic",
        prompt="bugün hava nasıl?",
        intent_type=IntentType.UNKNOWN,
        target="",
        expect_no_command=True,
    ),

    # =========================================================================
    # TYPE COERCION EDGE CASES — LLM'in string döndürdüğü durumlar (7)
    # =========================================================================

    PromptScenario(
        id="coercion_timing_string",
        prompt="192.168.1.1 hızlı tarama T4",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"timing": "4"},  # LLM string olarak doner
        expected_executable="nmap",
        expected_args_contain=["-T4"],
    ),
    PromptScenario(
        id="coercion_no_dns_string",
        prompt="10.0.0.1 DNS çözümleme yapmadan tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"no_dns": "true"},  # LLM "true" string doner
        expected_executable="nmap",
        expected_args_contain=["-n"],
    ),
    PromptScenario(
        id="coercion_top_ports_string",
        prompt="192.168.1.1 en popüler 200 portu tara",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"top_ports": "200"},  # LLM string olarak doner
        expected_executable="nmap",
        expected_args_contain=["--top-ports", "200"],
    ),
    PromptScenario(
        id="coercion_service_detection_string",
        prompt="10.0.0.1 versiyon tespiti ile tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"service_detection": "true"},
        expected_executable="nmap",
        expected_args_contain=["-sV"],
    ),
    PromptScenario(
        id="coercion_aggressive_string",
        prompt="10.0.0.1 agresif tarama",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"aggressive": "true"},
        expected_executable="nmap",
        expected_args_contain=["-A"],
    ),
    PromptScenario(
        id="port_scan_traceroute",
        prompt="192.168.1.1 port taraması traceroute ile",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"traceroute": True},
        expected_executable="nmap",
        expected_args_contain=["--traceroute"],
    ),
    PromptScenario(
        id="port_scan_combined_string_params",
        prompt="10.0.0.1 SYN taraması T3 verbose DNS kapalı traceroute açık",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"scan_type": "sS", "timing": "3", "verbose": "true", "no_dns": "true", "traceroute": "true"},
        expected_executable="nmap",
        expected_args_contain=["-sS", "-T3", "-v", "-n", "--traceroute"],
    ),

    # =========================================================================
    # COMPREHENSIVE NMAP EDGE CASES (13)
    # =========================================================================

    PromptScenario(
        id="top_ports_turkish_suffix",
        prompt="10.0.0.1 ilk 100 portu tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"top_ports": 100},
        expected_executable="nmap",
        expected_args_contain=["--top-ports", "100"],
    ),
    PromptScenario(
        id="top_ports_syn",
        prompt="10.0.0.1 ilk 200 portu SYN taraması ile tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"top_ports": 200, "scan_type": "sS"},
        expected_executable="nmap",
        expected_args_contain=["--top-ports", "200", "-sS"],
    ),
    PromptScenario(
        id="udp_scan",
        prompt="10.0.0.1 UDP taraması yap",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"scan_type": "sU"},
        expected_executable="nmap",
        expected_args_contain=["-sU"],
    ),
    PromptScenario(
        id="no_ping_port_scan",
        prompt="10.0.0.1 ping atmadan port tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"no_ping": True},
        expected_executable="nmap",
        expected_args_contain=["-Pn"],
    ),
    PromptScenario(
        id="single_port",
        prompt="192.168.1.1 port 22 tarama",
        intent_type=IntentType.PORT_SCAN,
        target="192.168.1.1",
        params={"ports": "22"},
        expected_executable="nmap",
        expected_args_contain=["-p", "22"],
    ),
    PromptScenario(
        id="port_range",
        prompt="10.0.0.1 1-65535 portlarını tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"ports": "1-65535"},
        expected_executable="nmap",
        expected_args_contain=["-p", "1-65535"],
    ),
    PromptScenario(
        id="multi_port_csv",
        prompt="10.0.0.1 port 22,80,443,8080 tara",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"ports": "22,80,443,8080"},
        expected_executable="nmap",
        expected_args_contain=["-p", "22,80,443,8080"],
    ),
    PromptScenario(
        id="osscan_guess_verbose",
        prompt="10.0.0.1 OS tespiti yap osscan-guess detaylı",
        intent_type=IntentType.OS_DETECTION,
        target="10.0.0.1",
        params={"osscan_guess": True, "verbose": True},
        expected_executable="nmap",
        expected_args_contain=["-O", "--osscan-guess", "-v"],
    ),
    PromptScenario(
        id="aggressive_traceroute",
        prompt="172.16.0.1 agresif tarama traceroute ile",
        intent_type=IntentType.PORT_SCAN,
        target="172.16.0.1",
        params={"aggressive": True, "traceroute": True},
        expected_executable="nmap",
        expected_args_contain=["-A", "--traceroute"],
    ),
    PromptScenario(
        id="service_detect_ports_timing",
        prompt="10.0.0.1 80 443 portlarında servis tespiti T2",
        intent_type=IntentType.SERVICE_DETECTION,
        target="10.0.0.1",
        params={"ports": "80,443", "timing": 2},
        expected_executable="nmap",
        expected_args_contain=["-sV", "-p", "80,443", "-T2"],
    ),
    PromptScenario(
        id="host_discovery_timing_nodns",
        prompt="192.168.1.0/24 ping taraması T5 DNS yapma",
        intent_type=IntentType.HOST_DISCOVERY,
        target="192.168.1.0/24",
        params={"timing": 5, "no_dns": True},
        expected_executable="nmap",
        expected_args_contain=["-sn", "-T5", "-n"],
    ),
    PromptScenario(
        id="syn_noping_nodns_timing",
        prompt="10.0.0.1 SYN taraması Pn T4 DNS yok",
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"scan_type": "sS", "no_ping": True, "timing": 4, "no_dns": True},
        expected_executable="nmap",
        expected_args_contain=["-sS", "-Pn", "-T4", "-n"],
    ),
    PromptScenario(
        id="vuln_scan_timing_ports",
        prompt="192.168.1.1 80 ve 443 zafiyet taraması T3",
        intent_type=IntentType.VULN_SCAN,
        target="192.168.1.1",
        params={"ports": "80,443", "timing": 3},
        expected_executable="nmap",
        expected_args_contain=["--script", "-T3"],
    ),
]


# =============================================================================
# STUB RESOLVER — LLM yerine senaryodan Intent üreten stub
# =============================================================================


class _ScenarioResolver:
    """Senaryodaki intent_type/target/params'ı döndüren sahte resolver."""

    def __init__(self, scenario: PromptScenario):
        self._scenario = scenario

    def resolve(self, user_input: str, target_hint=None) -> Intent:
        s = self._scenario
        return Intent(
            intent_type=s.intent_type,
            target=s.target or None,
            params=s.params,
            needs_clarification=(s.intent_type == IntentType.UNKNOWN),
            clarification_reason=(
                "Anlasılamadı" if s.intent_type == IntentType.UNKNOWN else None
            ),
            confidence=0.95 if s.intent_type != IntentType.UNKNOWN else 0.2,
        )


# =============================================================================
# PARAMETRIZED TESTS — Full Pipeline
# =============================================================================


class TestPromptToCommand:
    """50+ senaryo: Intent → Tool → Command → AIResponse (legacy bridge dahil)."""

    @pytest.mark.parametrize(
        "scenario",
        [s for s in SCENARIOS if not s.expect_no_command],
        ids=[s.id for s in SCENARIOS if not s.expect_no_command],
    )
    def test_command_producing_scenarios(self, scenario: PromptScenario):
        """Komut üreten senaryolar: executable ve argümanlar doğru mu?"""
        orch = AIOrchestrator(model="qwen2.5:3b")
        orch._intent_resolver = _ScenarioResolver(scenario)
        orch._hierarchical_resolver = None

        # Full pipeline: process_v2 → _v2_to_response (legacy bridge dahil)
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        response = orch.process_with_session(
            scenario.prompt,
            target=scenario.target or None,
            session_id=session_id,
        )

        # Tip kontrolü: AIResponse döndü mü?
        assert isinstance(response, AIResponse), (
            f"[{scenario.id}] process_with_session AIResponse dönmedi: {type(response)}"
        )

        # Komut üretilmiş mi?
        assert response.command is not None, (
            f"[{scenario.id}] Komut üretilmedi! message={response.message}"
        )
        cmd = response.command

        # Executable doğru mu?
        assert cmd.tool == scenario.expected_executable, (
            f"[{scenario.id}] Executable hatalı: "
            f"beklenen={scenario.expected_executable!r}, gerçek={cmd.tool!r}"
        )

        # Argüman kontrolleri
        full_cmd = [cmd.tool] + cmd.arguments
        full_cmd_str = " ".join(str(a) for a in full_cmd)

        for expected_arg in scenario.expected_args_contain:
            assert str(expected_arg) in full_cmd_str, (
                f"[{scenario.id}] Beklenen argüman komutta yok: {expected_arg!r}\n"
                f"  Komut: {full_cmd_str}"
            )

        for unwanted_arg in scenario.expected_args_not_contain:
            assert str(unwanted_arg) not in full_cmd_str, (
                f"[{scenario.id}] İstenmeyen argüman komutta var: {unwanted_arg!r}\n"
                f"  Komut: {full_cmd_str}"
            )

        # Target komutta var mı?
        if scenario.expected_target_in_cmd and scenario.target:
            assert scenario.target in full_cmd_str, (
                f"[{scenario.id}] Target komutta yok: {scenario.target!r}\n"
                f"  Komut: {full_cmd_str}"
            )

        # requires_root kontrolü
        if scenario.expected_requires_root is not None:
            assert cmd.requires_root == scenario.expected_requires_root, (
                f"[{scenario.id}] requires_root hatalı: "
                f"beklenen={scenario.expected_requires_root}, gerçek={cmd.requires_root}"
            )

    @pytest.mark.parametrize(
        "scenario",
        [s for s in SCENARIOS if s.expect_no_command],
        ids=[s.id for s in SCENARIOS if s.expect_no_command],
    )
    def test_no_command_scenarios(self, scenario: PromptScenario):
        """Komut üretilmemesi gereken senaryolar: info_query, unknown."""
        orch = AIOrchestrator(model="qwen2.5:3b")
        orch._intent_resolver = _ScenarioResolver(scenario)
        orch._hierarchical_resolver = None

        response = orch.process_with_session(scenario.prompt)

        assert isinstance(response, AIResponse)
        assert response.command is None, (
            f"[{scenario.id}] Komut üretilmemeliydi ama üretildi: "
            f"{response.command.tool} {response.command.arguments}"
        )
        assert response.message, (
            f"[{scenario.id}] Mesaj boş olmamalı"
        )


# =============================================================================
# STRUCTURAL TESTS — Pipeline Consistency
# =============================================================================


class TestPipelineConsistency:
    """Execution registry'deki her intent için pipeline tutarlılık testleri."""

    EXECUTABLE_TOOLS = [s for s in SCENARIOS if not s.expect_no_command]

    def test_total_scenario_count(self):
        """En az 50 senaryo tanımlı mı?"""
        assert len(SCENARIOS) >= 50, (
            f"Yetersiz senaryo sayısı: {len(SCENARIOS)} (beklenen ≥50)"
        )

    def test_all_executable_intents_covered(self):
        """Her tool üreten intent tipi en az 1 senaryoda geçiyor mu?"""
        covered_intents = {s.intent_type for s in SCENARIOS}
        expected_intents = {
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
            IntentType.SQL_INJECTION,
            IntentType.INFO_QUERY,
            IntentType.UNKNOWN,
        }
        missing = expected_intents - covered_intents
        assert not missing, (
            f"Senaryolarda eksik intent tipleri: {[i.value for i in missing]}"
        )

    def test_legacy_bridge_no_crash_for_every_execution_tool(self):
        """Her execution tool_id için build_command → _v2_to_response zinciri patlamaz."""
        from src.ai.tool_registry import _EXECUTION_REGISTRY

        for intent_type, mapping in _EXECUTION_REGISTRY.items():
            tool_id = mapping.get("tool_id")
            if not tool_id:
                continue

            tool_cls = TOOL_CLASS_MAP.get(tool_id)
            if tool_cls is None:
                continue

            tool = tool_cls()
            target_arg = mapping.get("target_arg", "target")

            # Minimal kwargs
            kwargs = {target_arg: "10.10.10.10"}

            # Brute force araçlarının zorunlu parametreleri
            required = mapping.get("required_params", [])
            for p in required:
                if p == "username":
                    kwargs["username"] = "admin"
                elif p == "wordlist":
                    kwargs["wordlist"] = "/tmp/test.txt"
                elif p == "form_path":
                    kwargs["form_path"] = "/login"
                elif p == "form_params":
                    kwargs["form_params"] = "user=^USER^&pass=^PASS^"
                elif p == "fail_string":
                    kwargs["fail_string"] = "Invalid"

            # URL gereken araçlar
            if target_arg in ("url",):
                kwargs[target_arg] = "http://10.10.10.10"

            # domain gereken araçlar
            if target_arg == "domain":
                kwargs[target_arg] = "example.com"

            try:
                cmd_list = tool.build_command(**kwargs)
            except Exception as e:
                pytest.fail(f"build_command failed for {tool_id}: {e}")

            if not cmd_list:
                continue

            # _v2_to_response bridge — crash yok mu?
            final_cmd = FinalCommand(
                executable=cmd_list[0],
                arguments=cmd_list[1:],
                requires_root=False,
                risk_level=RiskLevel.LOW,
                explanation="test",
            )
            v2_result = {
                "command": final_cmd,
                "message": "test",
                "needs_clarification": False,
            }
            resp = AIOrchestrator._v2_to_response(v2_result)
            assert isinstance(resp, AIResponse), f"_v2_to_response failed for {tool_id}"
            assert resp.command is not None, f"ToolCommand None for {tool_id}"
            assert resp.command.tool == cmd_list[0], (
                f"tool mismatch for {tool_id}: {resp.command.tool} != {cmd_list[0]}"
            )
