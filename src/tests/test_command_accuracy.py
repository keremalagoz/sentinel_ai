"""
Komut Uretim Dogruluk Orani Testi

Kullanici promptlarinin uctan uca dogru komut uretip uretemedigini olcer.
Tek amaci: % kac dogruluk oraniyla komut uretiyoruz?

Pipeline: user_input -> KeywordFilter -> ToolRegistry -> IntegratedTool.build_command -> FinalCommand

LLM gerektirmez -- deterministik pipeline uzerinden calisir.
"""

import pytest
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.ai.keyword_filter import KeywordPreFilter
from src.ai.schemas import IntentType, RiskLevel
from src.ai.tool_registry import (
    build_tool_spec,
    get_execution_tool_id,
    build_execution_kwargs,
)
from src.core.sentinel_coordinator import SentinelCoordinator


# ======================================================================
# Test Case Definition
# ======================================================================

@dataclass
class AccuracyCase:
    prompt: str
    expected_intent: IntentType
    expected_executable: Optional[str] = None
    must_contain: Optional[List[str]] = None
    must_not_contain: Optional[List[str]] = None
    expected_risk: Optional[str] = None
    expected_root: Optional[bool] = None
    no_command: bool = False
    extra_params: Dict[str, Any] = field(default_factory=dict)


# ======================================================================
# _ROOT_FLAGS & helpers
# ======================================================================

_ROOT_FLAGS = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})

_IP_RE = re.compile(
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)"
    r"|"
    r"(https?://[^\s]+)"
    r"|"
    r"((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})"
)


def _extract_target(prompt: str) -> Optional[str]:
    m = _IP_RE.search(prompt)
    return m.group(0) if m else None


# ======================================================================
# 84 SENARYO
#
# Gercek kullanici girdilerini temsil eder.
# Beklenen degerler gercek tool ciktilarini (openssl, bash, powershell.exe
# vb.) yansitir.
#
# Keyword filter eslesmeyebilir — bu gercek accuracy gap'tir.
# ======================================================================

ACCURACY_CASES: List[AccuracyCase] = [

    # ------------------------------------------------------------------
    # HOST_DISCOVERY  (nmap -sn)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="agdaki aktif cihazlari bul 192.168.1.0/24",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap",
        must_contain=["-sn", "192.168.1.0/24"],
        expected_risk="low", expected_root=False,
    ),
    AccuracyCase(
        prompt="yerel agda ping sweep yap",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn"],
    ),
    AccuracyCase(
        prompt="10.0.0.0/16 agindaki canli hostlari kesfet",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn"],
    ),
    AccuracyCase(
        prompt="ping sweep ile 10.10.10.0/24 tara",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn", "10.10.10.0/24"],
    ),
    AccuracyCase(
        prompt="alive host detection 192.168.0.0/24",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn", "192.168.0.0/24"],
    ),
    AccuracyCase(
        prompt="host discovery yap 172.16.0.0/24",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn", "172.16.0.0/24"],
    ),
    AccuracyCase(
        prompt="agdaki aktif hostlari tara",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn"],
    ),
    AccuracyCase(
        prompt="canli host kesfet 10.0.0.0/8",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_executable="nmap", must_contain=["-sn"],
    ),

    # ------------------------------------------------------------------
    # PORT_SCAN  (nmap -sT)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="192.168.1.5 uzerinde acik portlari tara",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap",
        must_contain=["-sT", "192.168.1.5"],
        must_not_contain=["-sS"],
        expected_risk="medium", expected_root=False,
    ),
    AccuracyCase(
        prompt="port taramasi baslat 192.168.1.100",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["-sT", "192.168.1.100"],
    ),
    AccuracyCase(
        prompt="SYN scan yap 10.0.0.1 adresine",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["10.0.0.1"],
    ),
    AccuracyCase(
        prompt="TCP port scan 10.0.0.5",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["-sT", "10.0.0.5"],
    ),
    AccuracyCase(
        prompt="acik port bul 192.168.0.1",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["192.168.0.1"],
    ),
    AccuracyCase(
        prompt="port scan yap 172.16.0.1",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["172.16.0.1"],
    ),
    AccuracyCase(
        prompt="hedefin portlarini tara",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["-sT"],
    ),
    AccuracyCase(
        prompt="udp scan yap 10.0.0.2",
        expected_intent=IntentType.PORT_SCAN,
        expected_executable="nmap", must_contain=["10.0.0.2"],
    ),

    # ------------------------------------------------------------------
    # SERVICE_DETECTION  (nmap -sV)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="servis tespit et 192.168.1.1",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_executable="nmap",
        must_contain=["-sV", "192.168.1.1"],
        expected_risk="medium",
    ),
    AccuracyCase(
        prompt="banner grab yap hedef sunucuya",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_executable="nmap", must_contain=["-sV"],
    ),
    AccuracyCase(
        prompt="servis versiyon tespiti 10.0.0.50",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_executable="nmap", must_contain=["-sV", "10.0.0.50"],
    ),
    AccuracyCase(
        prompt="version detection yap 192.168.1.5",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_executable="nmap", must_contain=["-sV", "192.168.1.5"],
    ),
    AccuracyCase(
        prompt="service detection baslat 10.10.10.1",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_executable="nmap", must_contain=["-sV", "10.10.10.1"],
    ),

    # ------------------------------------------------------------------
    # OS_DETECTION  (nmap -O)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="isletim sistemi tespiti 10.0.0.1",
        expected_intent=IntentType.OS_DETECTION,
        expected_executable="nmap",
        must_contain=["-O", "10.0.0.1"],
        expected_risk="medium", expected_root=True,
    ),
    AccuracyCase(
        prompt="OS fingerprint yap 192.168.1.100",
        expected_intent=IntentType.OS_DETECTION,
        expected_executable="nmap", must_contain=["-O", "192.168.1.100"],
    ),
    AccuracyCase(
        prompt="os detect 172.16.0.5",
        expected_intent=IntentType.OS_DETECTION,
        expected_executable="nmap", must_contain=["-O", "172.16.0.5"],
    ),
    AccuracyCase(
        prompt="isletim sistemi tespit et hedefte",
        expected_intent=IntentType.OS_DETECTION,
        expected_executable="nmap", must_contain=["-O"],
    ),

    # ------------------------------------------------------------------
    # VULN_SCAN  (nmap --script vuln)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="zafiyet taramasi yap 192.168.1.1",
        expected_intent=IntentType.VULN_SCAN,
        expected_executable="nmap",
        must_contain=["--script", "vuln", "192.168.1.1"],
        expected_risk="high", expected_root=True,
    ),
    AccuracyCase(
        prompt="nmap nse scriptleriyle vulnerability scan baslat",
        expected_intent=IntentType.VULN_SCAN,
        expected_executable="nmap", must_contain=["--script"],
    ),
    AccuracyCase(
        prompt="zafiyet tara 10.0.0.1",
        expected_intent=IntentType.VULN_SCAN,
        expected_executable="nmap", must_contain=["--script", "vuln", "10.0.0.1"],
    ),
    AccuracyCase(
        prompt="guvenlik acigi tara 192.168.0.100",
        expected_intent=IntentType.VULN_SCAN,
        expected_executable="nmap", must_contain=["192.168.0.100"],
    ),
    AccuracyCase(
        prompt="vulnerability assessment yap 10.10.10.1",
        expected_intent=IntentType.VULN_SCAN,
        expected_executable="nmap", must_contain=["--script", "vuln"],
    ),
    AccuracyCase(
        prompt="nse script ile zafiyet tara hedefte",
        expected_intent=IntentType.VULN_SCAN,
        expected_executable="nmap", must_contain=["--script"],
    ),

    # ------------------------------------------------------------------
    # SSL_SCAN  (openssl s_client)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="ssl sertifika analizi yap example.com",
        expected_intent=IntentType.SSL_SCAN,
        expected_executable="openssl",
        must_contain=["s_client", "example.com"],
        expected_risk="medium",
    ),
    AccuracyCase(
        prompt="tls cipher kontrol et 10.0.0.1",
        expected_intent=IntentType.SSL_SCAN,
        expected_executable="openssl", must_contain=["s_client", "10.0.0.1"],
    ),
    AccuracyCase(
        prompt="ssl testi yap hedef sunucuya",
        expected_intent=IntentType.SSL_SCAN,
        expected_executable="openssl", must_contain=["s_client"],
    ),
    AccuracyCase(
        prompt="sertifika kontrolu example.org",
        expected_intent=IntentType.SSL_SCAN,
        expected_executable="openssl", must_contain=["example.org"],
    ),
    AccuracyCase(
        prompt="openssl ile ssl scan yap",
        expected_intent=IntentType.SSL_SCAN,
        expected_executable="openssl", must_contain=["s_client"],
    ),

    # ------------------------------------------------------------------
    # WEB_DIR_ENUM  (gobuster dir)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="http://target.com uzerinde dizin taramasi yap",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_executable="gobuster",
        must_contain=["dir", "http://target.com"],
        expected_risk="medium",
    ),
    AccuracyCase(
        prompt="gobuster ile gizli path ara",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_executable="gobuster", must_contain=["dir"],
    ),
    AccuracyCase(
        prompt="web dizin kesfet http://10.0.0.1",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_executable="gobuster", must_contain=["dir"],
    ),
    AccuracyCase(
        prompt="directory enumeration http://target.local",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_executable="gobuster", must_contain=["dir"],
    ),
    AccuracyCase(
        prompt="dizin enum yap http://192.168.1.1",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_executable="gobuster", must_contain=["dir"],
    ),

    # ------------------------------------------------------------------
    # WEB_VULN_SCAN  (powershell.exe / web_app_scan)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="nikto ile web zafiyet taramasi yap",
        expected_intent=IntentType.WEB_VULN_SCAN,
        expected_risk="medium",
    ),
    AccuracyCase(
        prompt="web sunucu zafiyet tara http://192.168.1.1",
        expected_intent=IntentType.WEB_VULN_SCAN,
    ),
    AccuracyCase(
        prompt="nikto http://target.com tara",
        expected_intent=IntentType.WEB_VULN_SCAN,
    ),
    AccuracyCase(
        prompt="web vuln scan http://target.com",
        expected_intent=IntentType.WEB_VULN_SCAN,
    ),
    AccuracyCase(
        prompt="web sunucu guvenlik tarasi yap",
        expected_intent=IntentType.WEB_VULN_SCAN,
    ),

    # ------------------------------------------------------------------
    # DNS_LOOKUP  (nslookup)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="dns sorgu yap example.com",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_executable="nslookup",
        must_contain=["example.com"],
        expected_risk="low",
    ),
    AccuracyCase(
        prompt="MX record sorgula example.com",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_executable="nslookup", must_contain=["example.com"],
    ),
    AccuracyCase(
        prompt="dns lookup target.org",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_executable="nslookup",
    ),
    AccuracyCase(
        prompt="nslookup example.com",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_executable="nslookup", must_contain=["example.com"],
    ),
    AccuracyCase(
        prompt="dns record sorgula example.net",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_executable="nslookup",
    ),

    # ------------------------------------------------------------------
    # WHOIS_LOOKUP  (whois)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="whois sorgusu yap example.com",
        expected_intent=IntentType.WHOIS_LOOKUP,
        expected_executable="whois",
        must_contain=["example.com"],
        expected_risk="low",
    ),
    AccuracyCase(
        prompt="domain bilgi getir target.org",
        expected_intent=IntentType.WHOIS_LOOKUP,
        expected_executable="whois",
    ),
    AccuracyCase(
        prompt="whois example.net",
        expected_intent=IntentType.WHOIS_LOOKUP,
        expected_executable="whois", must_contain=["example.net"],
    ),

    # ------------------------------------------------------------------
    # SUBDOMAIN_ENUM  (bash -c ... nslookup loop)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="subdomain enum yap example.com",
        expected_intent=IntentType.SUBDOMAIN_ENUM,
        expected_executable="bash",
        expected_risk="medium",
    ),
    AccuracyCase(
        prompt="alt alan kesfet target.com",
        expected_intent=IntentType.SUBDOMAIN_ENUM,
        expected_executable="bash",
    ),
    AccuracyCase(
        prompt="subdomain enumeration example.org",
        expected_intent=IntentType.SUBDOMAIN_ENUM,
        expected_executable="bash",
    ),

    # ------------------------------------------------------------------
    # BRUTE_FORCE_SSH  (hydra)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="SSH brute force saldirisi yap 10.0.0.1",
        expected_intent=IntentType.BRUTE_FORCE_SSH,
        expected_executable="hydra",
        must_contain=["ssh"],
        expected_risk="high",
        extra_params={"username": "root", "wordlist": "/usr/share/wordlists/rockyou.txt"},
    ),
    AccuracyCase(
        prompt="hydra ile SSH sifre kir 192.168.1.1",
        expected_intent=IntentType.BRUTE_FORCE_SSH,
        expected_executable="hydra", must_contain=["ssh"],
        extra_params={"username": "root", "wordlist": "/usr/share/wordlists/rockyou.txt"},
    ),
    AccuracyCase(
        prompt="ssh password brute force 10.0.0.5",
        expected_intent=IntentType.BRUTE_FORCE_SSH,
        expected_executable="hydra", must_contain=["ssh"],
        extra_params={"username": "admin", "wordlist": "/usr/share/wordlists/rockyou.txt"},
    ),

    # ------------------------------------------------------------------
    # BRUTE_FORCE_HTTP  (hydra)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="http brute force yap http://target.com/login",
        expected_intent=IntentType.BRUTE_FORCE_HTTP,
        expected_executable="hydra",
        expected_risk="high",
        extra_params={
            "username": "admin",
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "form_path": "/login",
            "form_params": "user=^USER^&pass=^PASS^",
            "fail_string": "failed",
        },
    ),
    AccuracyCase(
        prompt="hydra http form brute force yap",
        expected_intent=IntentType.BRUTE_FORCE_HTTP,
        expected_executable="hydra",
        extra_params={
            "username": "admin",
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "form_path": "/login",
            "form_params": "user=^USER^&pass=^PASS^",
            "fail_string": "failed",
        },
    ),
    AccuracyCase(
        prompt="web login brute force http://target.com",
        expected_intent=IntentType.BRUTE_FORCE_HTTP,
        expected_executable="hydra",
        extra_params={
            "username": "admin",
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "form_path": "/login",
            "form_params": "user=^USER^&pass=^PASS^",
            "fail_string": "failed",
        },
    ),

    # ------------------------------------------------------------------
    # SQL_INJECTION  (sqlmap --batch)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="sql injection testi yap http://target.com/page?id=1",
        expected_intent=IntentType.SQL_INJECTION,
        expected_executable="sqlmap",
        must_contain=["--batch"],
        expected_risk="high",
    ),
    AccuracyCase(
        prompt="sqlmap ile veritabani injection testi",
        expected_intent=IntentType.SQL_INJECTION,
        expected_executable="sqlmap", must_contain=["--batch"],
    ),
    AccuracyCase(
        prompt="sqli testi yap http://target.com",
        expected_intent=IntentType.SQL_INJECTION,
        expected_executable="sqlmap",
    ),

    # ------------------------------------------------------------------
    # INFO_QUERY  (komut uretmemeli)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="nmap nedir ne ise yarar",
        expected_intent=IntentType.INFO_QUERY, no_command=True,
    ),
    AccuracyCase(
        prompt="port tarama nasil calisir acikla",
        expected_intent=IntentType.INFO_QUERY, no_command=True,
    ),
    AccuracyCase(
        prompt="SQL injection nedir",
        expected_intent=IntentType.INFO_QUERY, no_command=True,
    ),
    AccuracyCase(
        prompt="brute force saldirisi ne demek",
        expected_intent=IntentType.INFO_QUERY, no_command=True,
    ),
    AccuracyCase(
        prompt="SSL sertifikasi ne ise yarar",
        expected_intent=IntentType.INFO_QUERY, no_command=True,
    ),

    # ------------------------------------------------------------------
    # UNKNOWN  (komut uretmemeli)
    # ------------------------------------------------------------------
    AccuracyCase(
        prompt="merhaba bugun hava nasil",
        expected_intent=IntentType.UNKNOWN, no_command=True,
    ),
    AccuracyCase(
        prompt="selam",
        expected_intent=IntentType.UNKNOWN, no_command=True,
    ),
    AccuracyCase(
        prompt="hello how are you",
        expected_intent=IntentType.UNKNOWN, no_command=True,
    ),
    AccuracyCase(
        prompt="hey",
        expected_intent=IntentType.UNKNOWN, no_command=True,
    ),
]


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture(scope="module")
def keyword_filter():
    return KeywordPreFilter()


@pytest.fixture(scope="module")
def coordinator(qapp):
    return SentinelCoordinator()


# ======================================================================
# Test Class
# ======================================================================

class TestCommandAccuracy:
    """Uctan uca komut uretim dogruluk oranini olcer."""

    def _run_pipeline(self, case: AccuracyCase, kf: KeywordPreFilter, coord: SentinelCoordinator):
        """Tek bir case'i pipeline'dan gecir."""
        result = {
            "intent_ok": False,
            "command_ok": False,
            "executable_ok": True,
            "contains_ok": True,
            "not_contains_ok": True,
            "risk_ok": True,
            "root_ok": True,
            "detail": "",
        }

        # 1. Intent resolution via keyword filter
        suggested = kf.suggest(case.prompt)

        # INFO_QUERY / UNKNOWN: keyword None veya dogru eslesse = basarili
        if case.no_command:
            if suggested is None or suggested == case.expected_intent:
                result["intent_ok"] = True
                result["command_ok"] = True
                return result
            result["detail"] = (
                f"Expected no-command ({case.expected_intent.value}) "
                f"but keyword suggested {suggested.value}"
            )
            return result

        if suggested is None:
            result["detail"] = "Keyword filter returned None (no match)"
            return result

        # Intent dogrulugu (yakin gruplar kabul edilir)
        if suggested == case.expected_intent:
            result["intent_ok"] = True
        else:
            compatible = [
                {IntentType.PORT_SCAN, IntentType.HOST_DISCOVERY, IntentType.SERVICE_DETECTION},
                {IntentType.WEB_DIR_ENUM, IntentType.WEB_VULN_SCAN},
                {IntentType.BRUTE_FORCE_SSH, IntentType.BRUTE_FORCE_HTTP},
            ]
            for group in compatible:
                if suggested in group and case.expected_intent in group:
                    result["intent_ok"] = True
                    break
            if not result["intent_ok"]:
                result["detail"] = (
                    f"Intent mismatch: expected={case.expected_intent.value}, "
                    f"got={suggested.value}"
                )
                return result

        # 2. Target extraction
        target = _extract_target(case.prompt)
        web_intents = {
            IntentType.WEB_DIR_ENUM, IntentType.WEB_VULN_SCAN,
            IntentType.SQL_INJECTION, IntentType.BRUTE_FORCE_HTTP,
        }
        if not target:
            target = "http://10.0.0.1" if suggested in web_intents else "10.0.0.1"

        # 3. ToolSpec
        try:
            tool_spec = build_tool_spec(suggested, target, case.extra_params or {})
        except ValueError as e:
            result["detail"] = f"build_tool_spec error: {e}"
            return result
        if tool_spec is None:
            result["detail"] = "build_tool_spec returned None"
            return result

        # 4. Command via IntegratedTool
        exec_tool_id = get_execution_tool_id(suggested)
        exec_kwargs = build_execution_kwargs(suggested, target, case.extra_params or {})
        if not exec_tool_id or not exec_kwargs:
            result["detail"] = f"No execution mapping for {suggested.value}"
            return result

        integrated_tool = coord.manager.get_tool(exec_tool_id)
        if integrated_tool is None:
            result["detail"] = f"Tool {exec_tool_id} not registered"
            return result

        try:
            cmd_list = integrated_tool.tool.build_command(**exec_kwargs)
        except (ValueError, TypeError) as e:
            result["command_ok"] = False
            result["detail"] = f"build_command error: {e}"
            return result

        if not cmd_list:
            result["detail"] = "build_command returned empty"
            return result

        result["command_ok"] = True
        cmd_str = " ".join(str(x) for x in cmd_list)

        # 5. Executable
        if case.expected_executable and cmd_list[0] != case.expected_executable:
            result["executable_ok"] = False
            result["detail"] += f"Executable: expected={case.expected_executable}, got={cmd_list[0]}. "

        # 6. must_contain
        if case.must_contain:
            for token in case.must_contain:
                if token not in cmd_str:
                    result["contains_ok"] = False
                    result["detail"] += f"Missing '{token}' in cmd. "

        # 7. must_not_contain
        if case.must_not_contain:
            for token in case.must_not_contain:
                if token in cmd_str:
                    result["not_contains_ok"] = False
                    result["detail"] += f"Unexpected '{token}' in cmd. "

        # 8. Risk
        if case.expected_risk:
            actual_risk = tool_spec.risk_level.value
            if actual_risk != case.expected_risk:
                result["risk_ok"] = False
                result["detail"] += f"Risk: expected={case.expected_risk}, got={actual_risk}. "

        # 9. Root
        if case.expected_root is not None:
            actual_root = bool(_ROOT_FLAGS.intersection(cmd_list))
            if actual_root != case.expected_root:
                result["root_ok"] = False
                result["detail"] += f"Root: expected={case.expected_root}, got={actual_root}. "

        return result

    def test_overall_accuracy(self, keyword_filter, coordinator):
        """Tum case'leri calistirir ve dogruluk oranini raporlar."""
        total = len(ACCURACY_CASES)
        passed = 0
        failures = []

        for i, case in enumerate(ACCURACY_CASES):
            r = self._run_pipeline(case, keyword_filter, coordinator)
            all_ok = all([
                r["intent_ok"], r["command_ok"], r["executable_ok"],
                r["contains_ok"], r["not_contains_ok"],
                r["risk_ok"], r["root_ok"],
            ])
            if all_ok:
                passed += 1
            else:
                failures.append(
                    f"  [{i+1:02d}] {case.prompt[:55]:<57} -> {r['detail']}"
                )

        accuracy = (passed / total * 100) if total else 0

        report_lines = [
            "",
            "=" * 72,
            "  KOMUT URETIM DOGRULUK RAPORU",
            "=" * 72,
            f"  Toplam senaryo : {total}",
            f"  Basarili       : {passed}",
            f"  Basarisiz      : {total - passed}",
            f"  DOGRULUK ORANI : {accuracy:.1f}%",
            "=" * 72,
        ]
        if failures:
            report_lines.append("  Basarisiz senaryolar:")
            report_lines.extend(failures)
            report_lines.append("=" * 72)

        report = "\n".join(report_lines)
        # Windows cp1254 safe print
        sys.stdout.write(report.encode("ascii", errors="replace").decode("ascii"))
        sys.stdout.write("\n")

        # Minimum esik: %70
        assert accuracy >= 70.0, (
            f"Dogruluk orani {accuracy:.1f}% -- minimum esik %70"
        )

    @pytest.mark.parametrize(
        "case",
        ACCURACY_CASES,
        ids=[
            f"{c.expected_intent.value}:{c.prompt[:35]}"
            for c in ACCURACY_CASES
        ],
    )
    def test_individual_case(self, case, keyword_filter, coordinator):
        """Her bir senaryoyu ayri ayri test eder."""
        r = self._run_pipeline(case, keyword_filter, coordinator)
        all_ok = all([
            r["intent_ok"], r["command_ok"], r["executable_ok"],
            r["contains_ok"], r["not_contains_ok"],
            r["risk_ok"], r["root_ok"],
        ])
        assert all_ok, (
            f"Prompt: '{case.prompt}'\n"
            f"Expected: {case.expected_intent.value}\n"
            f"Detail: {r['detail']}"
        )
