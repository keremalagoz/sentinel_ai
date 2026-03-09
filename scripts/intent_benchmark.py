#!/usr/bin/env python3
"""Intent Benchmark Script — Prompt Accuracy Benchmark

Bu script mevcut intent benchmark altyapisini genisletir ve sadece intent tipi
dogrulugunu degil, prompt kalitesini etkileyen bilesenleri birlikte olcer:

- intent dogrulugu
- kategori dogrulugu
- target extraction dogrulugu
- params extraction dogrulugu
- clarification davranisi
- exact-match orani
- weighted prompt quality skoru
- per-intent precision / recall / F1
- confusion matrix
- prompt fingerprint'leri (hash, satir, karakter sayisi)

Kullanim:
    python scripts/intent_benchmark.py
    python scripts/intent_benchmark.py --dataset temp/custom_benchmark.json
    python scripts/intent_benchmark.py --output temp/prompt_benchmark.json
"""

import argparse
import csv
import json
import logging
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

# Proje kokunu path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.hierarchical_resolver import (
    CATEGORY_PROMPT,
    SUB_INTENT_PROMPT_TEMPLATE,
    HierarchicalResolver,
)
from src.ai.keyword_filter import KeywordPreFilter
from src.ai.param_extractor import ParamExtractor
from src.ai.schemas import CategoryType, Intent, IntentType, get_category_for_intent

# Mirror the strict-regex intent set from AIOrchestrator so the benchmark
# evaluates the same params users actually see in production (process_v2).
_STRICT_REGEX_INTENTS: frozenset = frozenset({
    IntentType.HOST_DISCOVERY,
    IntentType.PORT_SCAN,
    IntentType.SERVICE_DETECTION,
    IntentType.OS_DETECTION,
    IntentType.VULN_SCAN,
    IntentType.SSL_SCAN,
    IntentType.WEB_DIR_ENUM,
    IntentType.WEB_VULN_SCAN,
    IntentType.DNS_LOOKUP,
    IntentType.WHOIS_LOOKUP,
    IntentType.SUBDOMAIN_ENUM,
    IntentType.BRUTE_FORCE_SSH,
    IntentType.BRUTE_FORCE_HTTP,
    IntentType.SQL_INJECTION,
})

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# BENCHMARK DATASET
# =============================================================================


@dataclass(frozen=True)
class BenchmarkCase:
    """Tek benchmark girdisi ve beklenen davranis."""

    input_text: str
    expected_intent: IntentType
    expected_category: CategoryType
    expected_target: Optional[str] = None
    expected_params: dict[str, Any] = field(default_factory=dict)
    expected_needs_clarification: bool = False
    expected_clarification_contains: Optional[str] = None
    notes: Optional[str] = None


DEFAULT_CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        input_text="192.168.1.0/24 agindaki aktif cihazlari bul",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_category=CategoryType.SCANNING,
        expected_target="192.168.1.0/24",
    ),
    BenchmarkCase(
        input_text="yerel agda ping sweep yap",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_category=CategoryType.SCANNING,
    ),
    BenchmarkCase(
        input_text="10.0.0.0/16 agindaki canli hostlari kesfet",
        expected_intent=IntentType.HOST_DISCOVERY,
        expected_category=CategoryType.SCANNING,
        expected_target="10.0.0.0/16",
    ),
    BenchmarkCase(
        input_text="192.168.1.5 uzerinde acik portlari tara",
        expected_intent=IntentType.PORT_SCAN,
        expected_category=CategoryType.SCANNING,
        expected_target="192.168.1.5",
    ),
    BenchmarkCase(
        input_text="hedef sunucunun port 1-1024 arasini tara",
        expected_intent=IntentType.PORT_SCAN,
        expected_category=CategoryType.SCANNING,
        expected_params={"ports": "1-1024"},
    ),
    BenchmarkCase(
        input_text="80 ve 443 portlarini kontrol et 10.0.0.1 de",
        expected_intent=IntentType.PORT_SCAN,
        expected_category=CategoryType.SCANNING,
        expected_target="10.0.0.1",
        expected_params={"ports": "80,443"},
    ),
    BenchmarkCase(
        input_text="192.168.1.1 uzerindeki servislerin versiyonlarini tespit et",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_category=CategoryType.SCANNING,
        expected_target="192.168.1.1",
    ),
    BenchmarkCase(
        input_text="banner grab yap hedef sunucuya",
        expected_intent=IntentType.SERVICE_DETECTION,
        expected_category=CategoryType.SCANNING,
    ),
    BenchmarkCase(
        input_text="hedef makinenin isletim sistemini tespit et",
        expected_intent=IntentType.OS_DETECTION,
        expected_category=CategoryType.SCANNING,
    ),
    BenchmarkCase(
        input_text="OS fingerprint yap 192.168.1.100 icin",
        expected_intent=IntentType.OS_DETECTION,
        expected_category=CategoryType.SCANNING,
        expected_target="192.168.1.100",
    ),
    BenchmarkCase(
        input_text="192.168.1.1 uzerinde zafiyet taramasi yap",
        expected_intent=IntentType.VULN_SCAN,
        expected_category=CategoryType.SCANNING,
        expected_target="192.168.1.1",
    ),
    BenchmarkCase(
        input_text="nmap nse scriptleriyle vulnerability scan baslat",
        expected_intent=IntentType.VULN_SCAN,
        expected_category=CategoryType.SCANNING,
    ),
    BenchmarkCase(
        input_text="hedef sunucudaki guvenlik aciklarini tara",
        expected_intent=IntentType.VULN_SCAN,
        expected_category=CategoryType.SCANNING,
    ),
    BenchmarkCase(
        input_text="example.com icin SSL sertifika analizi yap",
        expected_intent=IntentType.SSL_SCAN,
        expected_category=CategoryType.SCANNING,
        expected_target="example.com",
    ),
    BenchmarkCase(
        input_text="TLS cipher konfigurasyonunu kontrol et",
        expected_intent=IntentType.SSL_SCAN,
        expected_category=CategoryType.SCANNING,
    ),
    BenchmarkCase(
        input_text="http://target.com uzerinde dizin taramasi yap",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_category=CategoryType.WEB,
        expected_target="http://target.com",
    ),
    BenchmarkCase(
        input_text="gobuster ile gizli path ara",
        expected_intent=IntentType.WEB_DIR_ENUM,
        expected_category=CategoryType.WEB,
    ),
    BenchmarkCase(
        input_text="nikto ile web zafiyet taramasi yap",
        expected_intent=IntentType.WEB_VULN_SCAN,
        expected_category=CategoryType.WEB,
    ),
    BenchmarkCase(
        input_text="web sunucusundaki zafiyetleri tara",
        expected_intent=IntentType.WEB_VULN_SCAN,
        expected_category=CategoryType.WEB,
    ),
    BenchmarkCase(
        input_text="example.com icin DNS sorgulama yap",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_category=CategoryType.RECON,
        expected_target="example.com",
    ),
    BenchmarkCase(
        input_text="MX record kayitlarini sorgula",
        expected_intent=IntentType.DNS_LOOKUP,
        expected_category=CategoryType.RECON,
        expected_params={"record_type": "MX"},
    ),
    BenchmarkCase(
        input_text="example.com domain bilgilerini getir",
        expected_intent=IntentType.WHOIS_LOOKUP,
        expected_category=CategoryType.RECON,
        expected_target="example.com",
    ),
    BenchmarkCase(
        input_text="example.com alt alanlarini kesfet",
        expected_intent=IntentType.SUBDOMAIN_ENUM,
        expected_category=CategoryType.RECON,
        expected_target="example.com",
    ),
    BenchmarkCase(
        input_text="subdomain enumeration yap hedef icin",
        expected_intent=IntentType.SUBDOMAIN_ENUM,
        expected_category=CategoryType.RECON,
    ),
    BenchmarkCase(
        input_text="SSH brute force saldirisi yap hedef sunucuya",
        expected_intent=IntentType.BRUTE_FORCE_SSH,
        expected_category=CategoryType.ATTACK,
    ),
    BenchmarkCase(
        input_text="HTTP login formunu brute force ile test et",
        expected_intent=IntentType.BRUTE_FORCE_HTTP,
        expected_category=CategoryType.ATTACK,
    ),
    BenchmarkCase(
        input_text="hedef URL uzerinde sqlmap ile SQL injection testi yap",
        expected_intent=IntentType.SQL_INJECTION,
        expected_category=CategoryType.ATTACK,
    ),
    BenchmarkCase(
        input_text="nmap nedir ne ise yarar",
        expected_intent=IntentType.INFO_QUERY,
        expected_category=CategoryType.INFO,
    ),
    BenchmarkCase(
        input_text="port tarama nasil calisir acikla",
        expected_intent=IntentType.INFO_QUERY,
        expected_category=CategoryType.INFO,
    ),
    BenchmarkCase(
        input_text="merhaba bugun hava nasil",
        expected_intent=IntentType.UNKNOWN,
        expected_category=CategoryType.INFO,
        expected_needs_clarification=True,
    ),
    BenchmarkCase(
        input_text="birseyler yap",
        expected_intent=IntentType.UNKNOWN,
        expected_category=CategoryType.INFO,
        expected_needs_clarification=True,
    ),
]


def _expand_default_cases(seed_cases: list[BenchmarkCase]) -> list[BenchmarkCase]:
    generated_cases: list[BenchmarkCase] = []

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.HOST_DISCOVERY,
                expected_category=CategoryType.SCANNING,
                expected_target=target,
            )
            for prompt, target in [
                ("172.16.0.0/24 segmentindeki canli sistemleri listele", "172.16.0.0/24"),
                ("192.168.56.0/24 subnetinde host kesfi yap", "192.168.56.0/24"),
                ("10.10.10.0/24 aginda aktif makineleri bul", "10.10.10.0/24"),
                ("172.20.1.0/24 uzerinde ping sweep baslat", "172.20.1.0/24"),
                ("192.168.50.0/24 icin host discovery calistir", "192.168.50.0/24"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.PORT_SCAN,
                expected_category=CategoryType.SCANNING,
                expected_target=target,
                expected_params=params,
            )
            for prompt, target, params in [
                ("10.10.10.5 sunucusunda ilk 1000 portu tara", "10.10.10.5", {}),
                ("172.16.1.25 uzerinde 21,22,80 portlarini kontrol et", "172.16.1.25", {"ports": "21,22,80"}),
                ("192.168.10.15 hedefinde 8080 ve 8443 acik mi bak", "192.168.10.15", {"ports": "8080,8443"}),
                ("10.0.5.9 hostunda 1-65535 tam port taramasi yap", "10.0.5.9", {"ports": "1-65535"}),
                ("172.31.8.20 icin 53,80,443 port taramasi calistir", "172.31.8.20", {"ports": "53,80,443"}),
                ("192.168.200.10 uzerinde 3306 ve 5432 portlarini tara", "192.168.200.10", {"ports": "3306,5432"}),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.SERVICE_DETECTION,
                expected_category=CategoryType.SCANNING,
                expected_target=target,
                expected_params=params,
            )
            for prompt, target, params in [
                ("10.0.0.15 makinesinde servis versiyonlarini cikar", "10.0.0.15", {}),
                ("172.16.5.40 uzerinde 80 ve 443 servis fingerprint yap", "172.16.5.40", {"ports": "80,443"}),
                ("192.168.3.10 hostunun banner bilgilerini topla", "192.168.3.10", {}),
                ("10.20.30.40 icin acik servislerin versiyonunu tespit et", "10.20.30.40", {}),
                ("172.18.0.12 uzerinde 22 portunun servis surumune bak", "172.18.0.12", {"ports": "22"}),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.OS_DETECTION,
                expected_category=CategoryType.SCANNING,
                expected_target=target,
            )
            for prompt, target in [
                ("10.10.20.15 hostunun isletim sistemini bul", "10.10.20.15"),
                ("172.16.100.25 icin os detection yap", "172.16.100.25"),
                ("192.168.77.4 makinesinin OS fingerprintini cikar", "192.168.77.4"),
                ("10.1.1.8 cihazinin hangi isletim sistemi kullandigini ogren", "10.1.1.8"),
                ("172.20.10.10 hedefinde isletim sistemi tespiti baslat", "172.20.10.10"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.VULN_SCAN,
                expected_category=CategoryType.SCANNING,
                expected_target=target,
            )
            for prompt, target in [
                ("10.0.0.20 sunucusunda zafiyet taramasi yap", "10.0.0.20"),
                ("172.16.10.5 hostunda NSE vuln scriptlerini calistir", "172.16.10.5"),
                ("192.168.9.9 makinesindeki guvenlik aciklarini tara", "192.168.9.9"),
                ("10.50.60.70 hedefi icin vulnerability assessment baslat", "10.50.60.70"),
                ("172.22.22.22 adresinde acik zafiyet kontrolu yap", "172.22.22.22"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.SSL_SCAN,
                expected_category=CategoryType.SCANNING,
                expected_target=target,
            )
            for prompt, target in [
                ("portal.example.com icin tls guvenligini analiz et", "portal.example.com"),
                ("api.example.net sunucusunun SSL konfigurasyonunu kontrol et", "api.example.net"),
                ("mail.example.org alan adinda sertifika incelemesi yap", "mail.example.org"),
                ("secure.example.com uzerinde cipher suite taramasi yap", "secure.example.com"),
                ("vpn.example.com hedefinde SSL sertifika analizi baslat", "vpn.example.com"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.WEB_DIR_ENUM,
                expected_category=CategoryType.WEB,
                expected_target=target,
            )
            for prompt, target in [
                ("https://shop.example.com uzerinde dizin bruteforce yap", "https://shop.example.com"),
                ("http://intranet.local icin web dizinlerini kesfet", "http://intranet.local"),
                ("https://app.test.lab adresinde gizli path ara", "https://app.test.lab"),
                ("http://192.168.1.50 web sunucusunda directory enum baslat", "http://192.168.1.50"),
                ("https://demo.example.org hedefinde gobuster taramasi yap", "https://demo.example.org"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.WEB_VULN_SCAN,
                expected_category=CategoryType.WEB,
                expected_target=target,
            )
            for prompt, target in [
                ("https://portal.example.com uzerinde web guvenlik taramasi yap", "https://portal.example.com"),
                ("http://legacy.example.net web uygulamasini zafiyet acisindan incele", "http://legacy.example.net"),
                ("https://cms.example.org icin nikto benzeri web scan calistir", "https://cms.example.org"),
                ("http://10.10.10.10 uygulamasinda web vulnerability taramasi yap", "http://10.10.10.10"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.DNS_LOOKUP,
                expected_category=CategoryType.RECON,
                expected_target=target,
                expected_params=params,
            )
            for prompt, target, params in [
                ("example.net icin A kaydini sorgula", "example.net", {"record_type": "A"}),
                ("mail.example.org alan adi icin MX kayitlarini getir", "mail.example.org", {"record_type": "MX"}),
                ("api.example.com icin TXT kaydina bak", "api.example.com", {"record_type": "TXT"}),
                ("cdn.example.io AAAA kaydini sorgula", "cdn.example.io", {"record_type": "AAAA"}),
                ("example.edu alan adinin NS kayitlarini getir", "example.edu", {"record_type": "NS"}),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.WHOIS_LOOKUP,
                expected_category=CategoryType.RECON,
                expected_target=target,
            )
            for prompt, target in [
                ("example.net domain whois bilgilerini getir", "example.net"),
                ("example.org alan adinin kayit bilgisini sorgula", "example.org"),
                ("example.edu icin registrar detaylarini ogren", "example.edu"),
                ("example.io domain sahiplik bilgisine bak", "example.io"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.SUBDOMAIN_ENUM,
                expected_category=CategoryType.RECON,
                expected_target=target,
            )
            for prompt, target in [
                ("corp.example.com icin alt alan adlarini bul", "corp.example.com"),
                ("example.net alan adinda subdomain kesfi yap", "example.net"),
                ("api.example.org icin alt alan taramasi baslat", "api.example.org"),
                ("internal.example.local subdomain enumeration yap", "internal.example.local"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.BRUTE_FORCE_SSH,
                expected_category=CategoryType.ATTACK,
                expected_target=target,
            )
            for prompt, target in [
                ("10.0.0.30 hedefinde ssh sifre denemesi yap", "10.0.0.30"),
                ("172.16.10.10 uzerinde SSH brute force testi baslat", "172.16.10.10"),
                ("192.168.44.8 hostu icin ssh login denemelerini otomatiklestir", "192.168.44.8"),
                ("10.50.1.9 adresinde ssh parola gucu testi yap", "10.50.1.9"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.BRUTE_FORCE_HTTP,
                expected_category=CategoryType.ATTACK,
                expected_target=target,
            )
            for prompt, target in [
                ("http://10.0.0.40/login icin http form brute force yap", "http://10.0.0.40/login"),
                ("https://portal.example.com/signin formuna parola denemesi uygula", "https://portal.example.com/signin"),
                ("http://172.16.0.50/auth uzerinde web login brute force testi yap", "http://172.16.0.50/auth"),
                ("https://demo.example.net/login icin form brute force baslat", "https://demo.example.net/login"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.SQL_INJECTION,
                expected_category=CategoryType.ATTACK,
                expected_target=target,
            )
            for prompt, target in [
                ("http://example.com/item.php?id=2 URLsi uzerinde sql injection testi yap", "http://example.com/item.php?id=2"),
                ("https://shop.example.net/product?id=5 hedefinde sqlmap kos", "https://shop.example.net/product?id=5"),
                ("http://10.0.0.70/report.php?user=1 icin SQLi kontrolu yap", "http://10.0.0.70/report.php?user=1"),
                ("https://portal.example.org/view.php?doc=3 urlsi icin sql injection denetimi baslat", "https://portal.example.org/view.php?doc=3"),
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.INFO_QUERY,
                expected_category=CategoryType.INFO,
            )
            for prompt in [
                "nmap service detection ne demek",
                "ssl scan neden yapilir",
                "whois sorgusu ne ise yarar",
                "sql injection testi nedir",
            ]
        ]
    )

    generated_cases.extend(
        [
            BenchmarkCase(
                input_text=prompt,
                expected_intent=IntentType.UNKNOWN,
                expected_category=CategoryType.INFO,
                expected_needs_clarification=True,
            )
            for prompt in [
                "bir bakiver su ise",
                "hedefle ilgili bir sey yap",
                "yardim et ama tam ne oldugunu ben de bilmiyorum",
                "sistemde bir kontrol gec",
            ]
        ]
    )

    unique_cases: list[BenchmarkCase] = []
    seen_inputs: set[str] = set()
    for case in [*seed_cases, *generated_cases]:
        key = case.input_text.strip().lower()
        if key in seen_inputs:
            continue
        seen_inputs.add(key)
        unique_cases.append(case)

    if len(unique_cases) < 100:
        raise ValueError(f"Default benchmark dataset 100 vakaya ulasamadi: {len(unique_cases)}")

    def with_locale(case: BenchmarkCase, locale: str, *, input_text: Optional[str] = None) -> BenchmarkCase:
        locale_note = f"locale:{locale}"
        merged_note = locale_note if not case.notes else f"{case.notes} | {locale_note}"
        return replace(case, input_text=input_text or case.input_text, notes=merged_note)

    def english_prompt(case: BenchmarkCase, index: int) -> str:
        target = case.expected_target or "the target system"
        params = case.expected_params or {}
        template_id = index % 4

        if case.expected_intent == IntentType.HOST_DISCOVERY:
            prompts = [
                f"Discover live hosts on {target}",
                f"Run a ping sweep against {target}",
                f"Perform host discovery on {target}",
                f"Find active devices in {target}",
            ]
            if case.expected_target is None:
                prompts = [
                    "Run a ping sweep on the local network",
                    "Discover active hosts on the local subnet",
                    "Perform host discovery on the local network",
                    "Find live systems on the internal network",
                ]
            return prompts[template_id]

        if case.expected_intent == IntentType.PORT_SCAN:
            ports = params.get("ports")
            if ports:
                prompts = [
                    f"Scan ports {ports} on {target}",
                    f"Check whether ports {ports} are open on {target}",
                    f"Run a port scan for {ports} against {target}",
                    f"Inspect ports {ports} on host {target}",
                ]
            else:
                prompts = [
                    f"Run a port scan on {target}",
                    f"Scan the first 1000 ports on {target}",
                    f"Check open ports on {target}",
                    f"Perform a TCP port scan against {target}",
                ]
            return prompts[template_id]

        if case.expected_intent == IntentType.SERVICE_DETECTION:
            ports = params.get("ports")
            if ports:
                prompts = [
                    f"Detect service versions on ports {ports} of {target}",
                    f"Fingerprint services on ports {ports} for {target}",
                    f"Identify the service running on port set {ports} at {target}",
                    f"Run service detection for ports {ports} on {target}",
                ]
            else:
                prompts = [
                    f"Detect service versions on {target}",
                    f"Grab banners from {target}",
                    f"Identify exposed services on {target}",
                    f"Run service fingerprinting on {target}",
                ]
            return prompts[template_id]

        if case.expected_intent == IntentType.OS_DETECTION:
            return [
                f"Detect the operating system of {target}",
                f"Run OS fingerprinting against {target}",
                f"Identify which operating system {target} is using",
                f"Perform OS detection on {target}",
            ][template_id]

        if case.expected_intent == IntentType.VULN_SCAN:
            return [
                f"Run a vulnerability scan on {target}",
                f"Check {target} for known vulnerabilities",
                f"Launch an NSE vulnerability assessment against {target}",
                f"Scan {target} for security issues",
            ][template_id]

        if case.expected_intent == IntentType.SSL_SCAN:
            return [
                f"Analyze the SSL configuration of {target}",
                f"Check the TLS setup for {target}",
                f"Inspect the certificate and cipher suites on {target}",
                f"Run an SSL scan against {target}",
            ][template_id]

        if case.expected_intent == IntentType.WEB_DIR_ENUM:
            return [
                f"Enumerate hidden directories on {target}",
                f"Run directory brute force against {target}",
                f"Discover hidden paths on {target}",
                f"Start a web directory enumeration on {target}",
            ][template_id]

        if case.expected_intent == IntentType.WEB_VULN_SCAN:
            return [
                f"Run a web vulnerability scan on {target}",
                f"Check the web application at {target} for security issues",
                f"Assess {target} for common web vulnerabilities",
                f"Start a web security scan against {target}",
            ][template_id]

        if case.expected_intent == IntentType.DNS_LOOKUP:
            record_type = str(params.get("record_type", "A"))
            return [
                f"Query the {record_type} DNS record for {target}",
                f"Look up the {record_type} record of {target}",
                f"Resolve the {record_type} entry for {target}",
                f"Run a DNS lookup for the {record_type} record on {target}",
            ][template_id]

        if case.expected_intent == IntentType.WHOIS_LOOKUP:
            return [
                f"Retrieve WHOIS information for {target}",
                f"Look up the domain registration details of {target}",
                f"Get registrar information for {target}",
                f"Run a WHOIS query on {target}",
            ][template_id]

        if case.expected_intent == IntentType.SUBDOMAIN_ENUM:
            return [
                f"Enumerate subdomains for {target}",
                f"Discover subdomains of {target}",
                f"Run subdomain enumeration against {target}",
                f"Find child domains under {target}",
            ][template_id]

        if case.expected_intent == IntentType.BRUTE_FORCE_SSH:
            return [
                f"Run an SSH brute force test against {target}",
                f"Attempt SSH password spraying on {target}",
                f"Start an SSH credential attack against {target}",
                f"Perform an SSH login brute force on {target}",
            ][template_id]

        if case.expected_intent == IntentType.BRUTE_FORCE_HTTP:
            return [
                f"Run an HTTP form brute force against {target}",
                f"Test the login form at {target} with brute force",
                f"Start a web login credential attack on {target}",
                f"Attempt HTTP password guessing on {target}",
            ][template_id]

        if case.expected_intent == IntentType.SQL_INJECTION:
            return [
                f"Test {target} for SQL injection",
                f"Run sqlmap against {target}",
                f"Assess {target} for SQLi issues",
                f"Launch an SQL injection check on {target}",
            ][template_id]

        if case.expected_intent == IntentType.INFO_QUERY:
            prompts = [
                "What is Nmap used for?",
                "How does port scanning work?",
                "Why would someone run an SSL scan?",
                "What is a WHOIS lookup used for?",
            ]
            if "service detection" in case.input_text.lower():
                prompts = [
                    "What does service detection mean in Nmap?",
                    "Explain Nmap service detection",
                    "What is the purpose of service fingerprinting?",
                    "Why is service detection useful during scanning?",
                ]
            elif "ssl" in case.input_text.lower():
                prompts = [
                    "Why is an SSL scan useful?",
                    "What does an SSL scan check?",
                    "Explain the purpose of TLS scanning",
                    "Why would you inspect certificate and cipher settings?",
                ]
            elif "whois" in case.input_text.lower():
                prompts = [
                    "What is a WHOIS lookup used for?",
                    "Explain what WHOIS data tells you",
                    "Why do analysts run WHOIS queries?",
                    "What can you learn from domain registration records?",
                ]
            elif "sql" in case.input_text.lower():
                prompts = [
                    "What is SQL injection testing?",
                    "Explain the purpose of SQLi assessment",
                    "Why would someone use sqlmap?",
                    "What does an SQL injection scan check for?",
                ]
            return prompts[template_id]

        return [
            "Please do something with the target",
            "Handle the target system somehow",
            "I need help with a task but I am not sure what exactly",
            "Check something on the system",
        ][template_id]

    turkish_cases = [with_locale(case, "tr") for case in unique_cases[:100]]
    english_cases: list[BenchmarkCase] = []
    english_seen: set[str] = set()
    for index, case in enumerate(unique_cases[:100]):
        prompt = english_prompt(case, index)
        key = prompt.strip().lower()
        if key in english_seen:
            prompt = f"{prompt} now"
            key = prompt.strip().lower()
        english_seen.add(key)
        english_cases.append(with_locale(case, "en", input_text=prompt))

    if len(turkish_cases) != 100 or len(english_cases) != 100:
        raise ValueError(
            f"Default benchmark dataset locale split bozuldu: tr={len(turkish_cases)} en={len(english_cases)}"
        )

    return turkish_cases + english_cases


DEFAULT_CASES = _expand_default_cases(DEFAULT_CASES)
TEST_CASES = DEFAULT_CASES


# =============================================================================
# RESULTS
# =============================================================================


@dataclass
class CaseResult:
    """Tek benchmark case sonucunun ayrintili kaydi."""

    input_text: str
    expected: str
    actual: str
    confidence: float
    keyword_suggestion: Optional[str]
    correct: bool
    latency_ms: float
    locale: Optional[str] = None
    error: Optional[str] = None
    expected_category: Optional[str] = None
    actual_category: Optional[str] = None
    category_correct: Optional[bool] = None
    category_confidence: Optional[float] = None
    keyword_bypassed: bool = False
    expected_target: Optional[str] = None
    actual_target: Optional[str] = None
    target_correct: bool = False
    expected_params: dict[str, Any] = field(default_factory=dict)
    actual_params: dict[str, Any] = field(default_factory=dict)
    params_correct: bool = False
    expected_needs_clarification: bool = False
    actual_needs_clarification: bool = False
    clarification_correct: bool = False
    exact_match: bool = False
    score_pct: float = 0.0
    category_latency_ms: Optional[float] = None
    sub_intent_latency_ms: Optional[float] = None


@dataclass
class BenchmarkSummary:
    """Benchmark ozet metrikleri."""

    total: int = 0
    resolved: int = 0
    correct: int = 0
    incorrect: int = 0
    errors: int = 0
    exact_match: int = 0
    target_correct: int = 0
    params_correct: int = 0
    clarification_correct: int = 0
    accuracy_pct: float = 0.0
    exact_match_pct: float = 0.0
    target_accuracy_pct: float = 0.0
    params_accuracy_pct: float = 0.0
    clarification_accuracy_pct: float = 0.0
    prompt_quality_pct: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    avg_category_latency_ms: float = 0.0
    avg_sub_intent_latency_ms: float = 0.0
    avg_confidence_pct: float = 0.0
    avg_confidence_correct_pct: float = 0.0
    avg_confidence_wrong_pct: float = 0.0
    confidence_calibration_gap_pct: float = 0.0
    model: str = ""
    category_model: Optional[str] = None
    mode: str = "hierarchical"
    dataset_name: str = "default"
    category_correct: int = 0
    category_accuracy_pct: float = 0.0
    keyword_bypass_count: int = 0
    prompt_signatures: dict[str, dict[str, Any]] = field(default_factory=dict)
    label_metrics: list[dict[str, Any]] = field(default_factory=list)
    confusion_matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)


# =============================================================================
# HELPERS
# =============================================================================


def _normalize_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return " ".join(value.strip().lower().split())
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return [_normalize_scalar(item) for item in value]
    if isinstance(value, dict):
        return _normalize_mapping(value)
    return str(value)


def _normalize_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _normalize_scalar(value)
        for key, value in sorted(data.items(), key=lambda item: item[0])
    }


def _normalize_target(target: Optional[str]) -> Optional[str]:
    return _normalize_scalar(target)


def _prompt_signature(text: str) -> dict[str, Any]:
    stripped = text.strip()
    return {
        "sha256_12": sha256(stripped.encode("utf-8")).hexdigest()[:12],
        "chars": len(stripped),
        "lines": stripped.count("\n") + 1 if stripped else 0,
    }


def build_prompt_signatures() -> dict[str, dict[str, Any]]:
    return {
        "category_prompt": _prompt_signature(CATEGORY_PROMPT),
        "sub_intent_prompt_template": _prompt_signature(SUB_INTENT_PROMPT_TEMPLATE),
    }


def _case_locale(case: BenchmarkCase) -> Optional[str]:
    notes = case.notes or ""
    for part in notes.split("|"):
        token = part.strip().lower()
        if token.startswith("locale:"):
            return token.split(":", 1)[1]
    return None


def configure_file_logging(log_file: Optional[str]) -> Optional[Path]:
    if not log_file:
        return None

    file_path = (PROJECT_ROOT / log_file).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == file_path:
            return file_path

    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    root_logger.addHandler(file_handler)
    return file_path


def _write_comparison_csv(summary: BenchmarkSummary, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "input_text",
                "locale",
                "expected",
                "actual",
                "correct",
                "expected_category",
                "actual_category",
                "category_correct",
                "expected_target",
                "actual_target",
                "target_correct",
                "expected_params",
                "actual_params",
                "params_correct",
                "expected_needs_clarification",
                "actual_needs_clarification",
                "clarification_correct",
                "score_pct",
                "confidence",
                "latency_ms",
                "error",
            ],
        )
        writer.writeheader()
        for row in summary.results:
            writer.writerow(
                {
                    "input_text": row.get("input_text"),
                    "locale": row.get("locale"),
                    "expected": row.get("expected"),
                    "actual": row.get("actual"),
                    "correct": row.get("correct"),
                    "expected_category": row.get("expected_category"),
                    "actual_category": row.get("actual_category"),
                    "category_correct": row.get("category_correct"),
                    "expected_target": row.get("expected_target"),
                    "actual_target": row.get("actual_target"),
                    "target_correct": row.get("target_correct"),
                    "expected_params": json.dumps(row.get("expected_params", {}), ensure_ascii=False),
                    "actual_params": json.dumps(row.get("actual_params", {}), ensure_ascii=False),
                    "params_correct": row.get("params_correct"),
                    "expected_needs_clarification": row.get("expected_needs_clarification"),
                    "actual_needs_clarification": row.get("actual_needs_clarification"),
                    "clarification_correct": row.get("clarification_correct"),
                    "score_pct": row.get("score_pct"),
                    "confidence": row.get("confidence"),
                    "latency_ms": row.get("latency_ms"),
                    "error": row.get("error"),
                }
            )


def _case_from_dict(data: dict[str, Any]) -> BenchmarkCase:
    return BenchmarkCase(
        input_text=str(data["input_text"]),
        expected_intent=IntentType(str(data["expected_intent"])),
        expected_category=CategoryType(str(data["expected_category"])),
        expected_target=data.get("expected_target"),
        expected_params=dict(data.get("expected_params", {})),
        expected_needs_clarification=bool(data.get("expected_needs_clarification", False)),
        expected_clarification_contains=data.get("expected_clarification_contains"),
        notes=data.get("notes"),
    )


def load_cases(dataset_path: Optional[str]) -> tuple[list[BenchmarkCase], str]:
    if not dataset_path:
        return (DEFAULT_CASES, "default")

    file_path = (PROJECT_ROOT / dataset_path).resolve()
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Dataset JSON must be a list")

    return ([_case_from_dict(item) for item in raw], file_path.name)


def evaluate_case(
    case: BenchmarkCase,
    intent: Intent,
    *,
    latency_ms: float,
    actual_category: Optional[CategoryType] = None,
    category_confidence: Optional[float] = None,
    keyword_suggestion: Optional[IntentType] = None,
    keyword_bypassed: bool = False,
    category_latency_ms: Optional[float] = None,
    sub_intent_latency_ms: Optional[float] = None,
) -> CaseResult:
    expected_params = _normalize_mapping(case.expected_params)
    actual_params = _normalize_mapping(intent.params)

    target_correct = _normalize_target(intent.target) == _normalize_target(case.expected_target)
    params_correct = actual_params == expected_params

    clarification_correct = intent.needs_clarification == case.expected_needs_clarification
    if case.expected_needs_clarification and case.expected_clarification_contains:
        clarification_correct = clarification_correct and (
            case.expected_clarification_contains.lower()
            in (intent.clarification_reason or "").lower()
        )
    elif not case.expected_needs_clarification:
        clarification_correct = clarification_correct and not bool(intent.clarification_reason)

    correct = intent.intent_type == case.expected_intent
    resolved_category = actual_category or get_category_for_intent(intent.intent_type)
    category_correct = resolved_category == case.expected_category
    exact_match = correct and target_correct and params_correct and clarification_correct

    score = (
        (0.55 if correct else 0.0)
        + (0.15 if category_correct else 0.0)
        + (0.15 if target_correct else 0.0)
        + (0.10 if params_correct else 0.0)
        + (0.05 if clarification_correct else 0.0)
    ) * 100.0

    return CaseResult(
        input_text=case.input_text,
        locale=_case_locale(case),
        expected=case.expected_intent.value,
        actual=intent.intent_type.value,
        confidence=float(intent.confidence),
        keyword_suggestion=keyword_suggestion.value if keyword_suggestion else None,
        correct=correct,
        latency_ms=round(latency_ms, 1),
        expected_category=case.expected_category.value,
        actual_category=resolved_category.value,
        category_correct=category_correct,
        category_confidence=category_confidence,
        keyword_bypassed=keyword_bypassed,
        expected_target=case.expected_target,
        actual_target=intent.target,
        target_correct=target_correct,
        expected_params=case.expected_params,
        actual_params=intent.params,
        params_correct=params_correct,
        expected_needs_clarification=case.expected_needs_clarification,
        actual_needs_clarification=bool(intent.needs_clarification),
        clarification_correct=clarification_correct,
        exact_match=exact_match,
        score_pct=round(score, 1),
        category_latency_ms=round(category_latency_ms, 1) if category_latency_ms is not None else None,
        sub_intent_latency_ms=round(sub_intent_latency_ms, 1) if sub_intent_latency_ms is not None else None,
    )


def _build_label_metrics(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = sorted(
        {row["expected"] for row in results if row.get("error") is None}
        | {row["actual"] for row in results if row.get("error") is None}
    )
    metrics: list[dict[str, Any]] = []

    for label in labels:
        tp = sum(
            1
            for row in results
            if row.get("error") is None and row["expected"] == label and row["actual"] == label
        )
        fp = sum(
            1
            for row in results
            if row.get("error") is None and row["expected"] != label and row["actual"] == label
        )
        fn = sum(
            1
            for row in results
            if row.get("error") is None and row["expected"] == label and row["actual"] != label
        )
        support = sum(1 for row in results if row.get("error") is None and row["expected"] == label)
        predicted = sum(1 for row in results if row.get("error") is None and row["actual"] == label)

        precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        metrics.append(
            {
                "label": label,
                "support": support,
                "predicted": predicted,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision_pct": round(precision, 1),
                "recall_pct": round(recall, 1),
                "f1_pct": round(f1, 1),
            }
        )

    return metrics


def _build_confusion_matrix(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = defaultdict(dict)
    labels = sorted(
        {row["expected"] for row in results if row.get("error") is None}
        | {row["actual"] for row in results if row.get("error") is None}
    )

    for expected in labels:
        for actual in labels:
            count = sum(
                1
                for row in results
                if row.get("error") is None and row["expected"] == expected and row["actual"] == actual
            )
            if count:
                matrix[expected][actual] = count

    return dict(matrix)


def finalize_summary(summary: BenchmarkSummary) -> BenchmarkSummary:
    resolved = [row for row in summary.results if row.get("error") is None]
    failed = [row for row in summary.results if row.get("error") is not None]

    summary.resolved = len(resolved)
    summary.errors = len(failed)
    summary.correct = sum(1 for row in resolved if row["correct"])
    summary.incorrect = sum(1 for row in resolved if not row["correct"])
    summary.exact_match = sum(1 for row in resolved if row["exact_match"])
    summary.target_correct = sum(1 for row in resolved if row["target_correct"])
    summary.params_correct = sum(1 for row in resolved if row["params_correct"])
    summary.clarification_correct = sum(1 for row in resolved if row["clarification_correct"])
    summary.category_correct = sum(1 for row in resolved if row.get("category_correct"))
    summary.keyword_bypass_count = sum(1 for row in resolved if row.get("keyword_bypassed"))

    if resolved:
        summary.accuracy_pct = round(summary.correct / len(resolved) * 100.0, 1)
        summary.exact_match_pct = round(summary.exact_match / len(resolved) * 100.0, 1)
        summary.target_accuracy_pct = round(summary.target_correct / len(resolved) * 100.0, 1)
        summary.params_accuracy_pct = round(summary.params_correct / len(resolved) * 100.0, 1)
        summary.clarification_accuracy_pct = round(summary.clarification_correct / len(resolved) * 100.0, 1)
        summary.category_accuracy_pct = round(summary.category_correct / len(resolved) * 100.0, 1)
        summary.prompt_quality_pct = round(sum(row["score_pct"] for row in resolved) / len(resolved), 1)

        latencies = [float(row["latency_ms"]) for row in resolved]
        summary.avg_latency_ms = round(sum(latencies) / len(latencies), 1)
        summary.max_latency_ms = round(max(latencies), 1)
        summary.min_latency_ms = round(min(latencies), 1)

        category_latencies = [
            float(row["category_latency_ms"])
            for row in resolved
            if row.get("category_latency_ms") is not None
        ]
        if category_latencies:
            summary.avg_category_latency_ms = round(sum(category_latencies) / len(category_latencies), 1)

        sub_latencies = [
            float(row["sub_intent_latency_ms"])
            for row in resolved
            if row.get("sub_intent_latency_ms") is not None
        ]
        if sub_latencies:
            summary.avg_sub_intent_latency_ms = round(sum(sub_latencies) / len(sub_latencies), 1)

        confidences = [float(row["confidence"]) for row in resolved]
        summary.avg_confidence_pct = round(sum(confidences) / len(confidences) * 100.0, 1)

        correct_conf = [float(row["confidence"]) for row in resolved if row["correct"]]
        wrong_conf = [float(row["confidence"]) for row in resolved if not row["correct"]]
        if correct_conf:
            summary.avg_confidence_correct_pct = round(sum(correct_conf) / len(correct_conf) * 100.0, 1)
        if wrong_conf:
            summary.avg_confidence_wrong_pct = round(sum(wrong_conf) / len(wrong_conf) * 100.0, 1)

        summary.confidence_calibration_gap_pct = round(abs(summary.avg_confidence_pct - summary.accuracy_pct), 1)

    summary.label_metrics = _build_label_metrics(summary.results)
    summary.confusion_matrix = _build_confusion_matrix(summary.results)
    return summary


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================


def run_benchmark(
    model: str = "qwen2.5:3b",
    category_model: Optional[str] = None,
    dataset_path: Optional[str] = None,
    progress_every: int = 10,
) -> BenchmarkSummary:
    cases, dataset_name = load_cases(dataset_path)
    kf = KeywordPreFilter()

    summary = BenchmarkSummary(
        model=model,
        category_model=category_model,
        total=len(cases),
        mode="hierarchical",
        dataset_name=dataset_name,
        prompt_signatures=build_prompt_signatures(),
    )

    resolver = HierarchicalResolver(
        category_model=category_model,
        sub_intent_model=model,
    )
    logger.info("Mod: HIERARCHICAL (Stage1=%s, Stage2=%s)", category_model or model, model)

    for idx, case in enumerate(cases, 1):
        logger.info("  [%02d/%02d] %s", idx, len(cases), case.input_text[:80])
        kw_suggest = kf.suggest(case.input_text)

        try:
            keyword_bypassed = kw_suggest is not None
            category_latency_ms = 0.0

            if keyword_bypassed:
                resolved_category = get_category_for_intent(kw_suggest)
                category_confidence = 1.0
            else:
                t0_category = time.monotonic()
                category_result = resolver.resolve_category(case.input_text)
                category_latency_ms = (time.monotonic() - t0_category) * 1000
                resolved_category = category_result.category
                category_confidence = category_result.confidence

            t0_sub = time.monotonic()
            intent = resolver.resolve_sub_intent(case.input_text, resolved_category)
            sub_intent_latency_ms = (time.monotonic() - t0_sub) * 1000
            latency_ms = category_latency_ms + sub_intent_latency_ms

            # ── Post-processing: mirror production pipeline (process_v2) ──
            # 1. Strict-regex param pruning: keep only regex-extracted params
            if intent.intent_type in _STRICT_REGEX_INTENTS:
                intent.params = ParamExtractor.extract(case.input_text, intent.intent_type)

            # 2. Regex target resolution: prefer full URL over LLM-truncated target
            regex_target = ParamExtractor.extract_target(case.input_text)
            if regex_target and regex_target.startswith(("http://", "https://")):
                intent.target = regex_target

            # 3. Keyword fallback: if LLM returned UNKNOWN but keyword knows better
            if (
                intent.intent_type == IntentType.UNKNOWN
                and kw_suggest is not None
                and kw_suggest != IntentType.UNKNOWN
            ):
                intent.intent_type = kw_suggest
                intent.params = ParamExtractor.extract(case.input_text, kw_suggest)
                if not intent.target:
                    intent.target = regex_target

            # 4. INFO_QUERY keyword override: info patterns are high-precision
            #    ("nedir", "what does X check", "nasil calisir", etc.), so when
            #    keyword suggests INFO_QUERY but LLM returns an action intent,
            #    the keyword should win — mirrors process_v2 cross-validation.
            if (
                kw_suggest == IntentType.INFO_QUERY
                and intent.intent_type != IntentType.INFO_QUERY
                and intent.intent_type in _STRICT_REGEX_INTENTS
            ):
                intent.intent_type = IntentType.INFO_QUERY
                intent.params = {}
                intent.target = None

            result = evaluate_case(
                case,
                intent,
                latency_ms=latency_ms,
                actual_category=resolved_category,
                category_confidence=category_confidence,
                keyword_suggestion=kw_suggest,
                keyword_bypassed=keyword_bypassed,
                category_latency_ms=category_latency_ms,
                sub_intent_latency_ms=sub_intent_latency_ms,
            )

            if not result.correct:
                logger.warning(
                    "    YANLIS: beklenen=%s, gerceklesen=%s | target_ok=%s params_ok=%s clarification_ok=%s",
                    result.expected,
                    result.actual,
                    result.target_correct,
                    result.params_correct,
                    result.clarification_correct,
                )

            summary.results.append(asdict(result))

            if progress_every > 0 and idx % progress_every == 0:
                resolved_so_far = [row for row in summary.results if row.get("error") is None]
                correct_so_far = sum(1 for row in resolved_so_far if row.get("correct"))
                accuracy_so_far = (correct_so_far / len(resolved_so_far) * 100.0) if resolved_so_far else 0.0
                logger.info(
                    "    Ilerleme: %d/%d | anlik_intent_dogruluk=%.1f%% | hata=%d",
                    idx,
                    len(cases),
                    accuracy_so_far,
                    sum(1 for row in summary.results if row.get("error") is not None),
                )

        except Exception as exc:
            summary.results.append(
                asdict(
                    CaseResult(
                        input_text=case.input_text,
                        locale=_case_locale(case),
                        expected=case.expected_intent.value,
                        actual="",
                        confidence=0.0,
                        keyword_suggestion=kw_suggest.value if kw_suggest else None,
                        correct=False,
                        latency_ms=0.0,
                        error=str(exc),
                        expected_category=case.expected_category.value,
                        expected_target=case.expected_target,
                        expected_params=case.expected_params,
                        expected_needs_clarification=case.expected_needs_clarification,
                    )
                )
            )
            logger.error("    HATA: %s", exc)

    return finalize_summary(summary)


# =============================================================================
# REPORTING
# =============================================================================


def print_summary(summary: BenchmarkSummary) -> None:
    print("\n" + "=" * 76)
    print(f"  INTENT / PROMPT BENCHMARK SONUCLARI ({summary.mode.upper()})")
    print("=" * 76)
    print(f"  Model                     : {summary.model}")
    if summary.category_model:
        print(f"  Category Model            : {summary.category_model}")
    print(f"  Dataset                   : {summary.dataset_name}")
    print(f"  Toplam Test               : {summary.total}")
    print(f"  Cozulen Test              : {summary.resolved}")
    print(f"  Hata                      : {summary.errors}")
    print(f"  Intent Dogruluk           : {summary.accuracy_pct}%")
    print(f"  Exact Match               : {summary.exact_match_pct}%")
    print(f"  Target Dogruluk           : {summary.target_accuracy_pct}%")
    print(f"  Params Dogruluk           : {summary.params_accuracy_pct}%")
    print(f"  Clarification Dogruluk    : {summary.clarification_accuracy_pct}%")
    print(f"  Prompt Quality Skoru      : {summary.prompt_quality_pct}%")
    print(f"  Ort. Latency              : {summary.avg_latency_ms} ms")
    print(f"  Min / Max Latency         : {summary.min_latency_ms} / {summary.max_latency_ms} ms")
    print(f"  Stage1 Ort. Latency       : {summary.avg_category_latency_ms} ms")
    print(f"  Stage2 Ort. Latency       : {summary.avg_sub_intent_latency_ms} ms")
    print(f"  Kategori Dogruluk         : {summary.category_accuracy_pct}%")
    print(f"  Keyword Bypass            : {summary.keyword_bypass_count}")
    print(f"  Ort. Confidence           : {summary.avg_confidence_pct}%")
    print(f"  Confidence Gap            : {summary.confidence_calibration_gap_pct}%")
    print("=" * 76)

    if summary.prompt_signatures:
        print("\n  PROMPT FINGERPRINTS:")
        for name, sig in summary.prompt_signatures.items():
            print(
                f"    - {name}: sha={sig['sha256_12']} chars={sig['chars']} lines={sig['lines']}"
            )

    incorrect = [row for row in summary.results if row.get("error") is None and not row["correct"]]
    if incorrect:
        print("\n  YANLIS INTENT SONUCLARI:")
        for row in incorrect[:10]:
            print(
                f"    - [{row['expected']}] -> [{row['actual']}] "
                f"target_ok={row['target_correct']} params_ok={row['params_correct']} "
                f"clar_ok={row['clarification_correct']} conf={row['confidence']:.2f} :: "
                f"{row['input_text'][:70]}"
            )

    non_exact = [row for row in summary.results if row.get("error") is None and not row["exact_match"]]
    if non_exact:
        print("\n  EXACT-MATCH KACAKLARI:")
        for row in non_exact[:10]:
            print(
                f"    - {row['input_text'][:70]} | intent={row['correct']} target={row['target_correct']} "
                f"params={row['params_correct']} clar={row['clarification_correct']} score={row['score_pct']}"
            )

    if summary.label_metrics:
        print("\n  PER-INTENT METRICS:")
        for row in summary.label_metrics:
            print(
                f"    - {row['label']}: P={row['precision_pct']}% "
                f"R={row['recall_pct']}% F1={row['f1_pct']}% support={row['support']}"
            )

    errors = [row for row in summary.results if row.get("error") is not None]
    if errors:
        print("\n  HATALAR:")
        for row in errors:
            print(f"    - {row['error']}: {row['input_text'][:70]}")

# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Hierarchical intent / prompt benchmark runner")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama Stage 2 model adi")
    parser.add_argument(
        "--category-model",
        default=None,
        help="Hierarchical Stage 1 modeli (default: ana model veya env)",
    )
    parser.add_argument("--dataset", default=None, help="Opsiyonel benchmark dataset JSON yolu")
    parser.add_argument("--output", default=None, help="JSON cikti yolu")
    parser.add_argument("--comparisons-output", default=None, help="Vaka bazli CSV karsilastirma cikti yolu")
    parser.add_argument("--log-file", default=None, help="Benchmark log dosyasi yolu")
    parser.add_argument("--progress-every", type=int, default=10, help="Her N vakada bir ara ilerleme logu bas")
    args = parser.parse_args()

    log_file_path = configure_file_logging(args.log_file)
    if log_file_path:
        logger.info("Benchmark log dosyasi: %s", log_file_path)

    summary = run_benchmark(
        model=args.model,
        category_model=args.category_model,
        dataset_path=args.dataset,
        progress_every=max(0, int(args.progress_every)),
    )
    print_summary(summary)

    output_path = args.output or f"temp/prompt_benchmark_hier_{int(time.time())}.json"
    output_file = PROJECT_ROOT / output_path
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Sonuclar yazildi: %s", output_file)

    comparisons_path = args.comparisons_output or f"temp/{output_file.stem}_comparisons.csv"
    comparisons_file = PROJECT_ROOT / comparisons_path
    _write_comparison_csv(summary, comparisons_file)
    logger.info("CSV karsilastirma yazildi: %s", comparisons_file)


if __name__ == "__main__":
    main()
