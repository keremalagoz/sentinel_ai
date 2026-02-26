#!/usr/bin/env python3
"""Intent Benchmark Script — Sprint 3.6 Track C4

30 ornek girdi ile IntentResolver dogruluk ve latency olcumu yapar.
Sonuclari JSON ve ozet tablo olarak yazar.

Kullanim:
    python scripts/intent_benchmark.py               # Varsayilan model (model2)
    python scripts/intent_benchmark.py --model model1 # Farkli model
    python scripts/intent_benchmark.py --output results.json
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# Proje kokunu path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.intent_resolver import IntentResolver
from src.ai.keyword_filter import KeywordPreFilter
from src.ai.schemas import IntentType

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# TEST CASES — 30 ornek
# =============================================================================
# (kullanici_girdisi, beklenen_intent)[

TEST_CASES: list[tuple[str, IntentType]] = [
    # Host Discovery (3)
    ("192.168.1.0/24 agindaki aktif cihazlari bul", IntentType.HOST_DISCOVERY),
    ("yerel agda ping sweep yap", IntentType.HOST_DISCOVERY),
    ("10.0.0.0/16 agindaki canli hostlari kesfet", IntentType.HOST_DISCOVERY),

    # Port Scan (3)
    ("192.168.1.5 uzerinde acik portlari tara", IntentType.PORT_SCAN),
    ("hedef sunucunun port 1-1024 arasini tara", IntentType.PORT_SCAN),
    ("SYN scan yap 10.0.0.1 adresine", IntentType.PORT_SCAN),

    # Service Detection (2)
    ("192.168.1.1 uzerindeki servislerin versiyonlarini tespit et", IntentType.SERVICE_DETECTION),
    ("banner grab yap hedef sunucuya", IntentType.SERVICE_DETECTION),

    # OS Detection (2)
    ("hedef makinenin isletim sistemini tespit et", IntentType.OS_DETECTION),
    ("OS fingerprint yap 192.168.1.100 icin", IntentType.OS_DETECTION),

    # Vuln Scan (3)
    ("192.168.1.1 uzerinde zafiyet taramasi yap", IntentType.VULN_SCAN),
    ("nmap nse scriptleriyle vulnerability scan baslat", IntentType.VULN_SCAN),
    ("hedef sunucudaki guvenlik aciklarini tara", IntentType.VULN_SCAN),

    # SSL Scan (2)
    ("example.com icin SSL sertifika analizi yap", IntentType.SSL_SCAN),
    ("TLS cipher konfigurasyonunu kontrol et", IntentType.SSL_SCAN),

    # Web Dir Enum (2)
    ("http://target.com uzerinde dizin taramasi yap", IntentType.WEB_DIR_ENUM),
    ("gobuster ile gizli path ara", IntentType.WEB_DIR_ENUM),

    # Web Vuln Scan (2)
    ("nikto ile web zafiyet taramasi yap", IntentType.WEB_VULN_SCAN),
    ("web sunucusundaki zafiyetleri tara", IntentType.WEB_VULN_SCAN),

    # DNS Lookup (2)
    ("example.com icin DNS sorgulama yap", IntentType.DNS_LOOKUP),
    ("MX record kayitlarini sorgula", IntentType.DNS_LOOKUP),

    # Whois (1)
    ("example.com domain bilgilerini getir", IntentType.WHOIS_LOOKUP),

    # Subdomain Enum (2)
    ("example.com alt alanlarini kesfet", IntentType.SUBDOMAIN_ENUM),
    ("subdomain enumeration yap hedef icin", IntentType.SUBDOMAIN_ENUM),

    # Brute Force SSH (1)
    ("SSH brute force saldirisi yap hedef sunucuya", IntentType.BRUTE_FORCE_SSH),

    # Brute Force HTTP (1)
    ("HTTP login formunu brute force ile test et", IntentType.BRUTE_FORCE_HTTP),

    # SQL Injection (1)
    ("hedef URL uzerinde sqlmap ile SQL injection testi yap", IntentType.SQL_INJECTION),

    # Info Query (2)
    ("nmap nedir ne ise yarar", IntentType.INFO_QUERY),
    ("port tarama nasil calisir acikla", IntentType.INFO_QUERY),

    # Unknown / Ambiguous (1)
    ("merhaba bugun hava nasil", IntentType.UNKNOWN),
]


# =============================================================================
# RESULT DATA
# =============================================================================

@dataclass
class CaseResult:
    """Tek bir test case sonucu."""
    input_text: str
    expected: str
    actual: str
    confidence: float
    keyword_suggestion: Optional[str]
    correct: bool
    latency_ms: float
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Genel benchmark ozet metrikleri."""
    total: int = 0
    correct: int = 0
    incorrect: int = 0
    errors: int = 0
    accuracy_pct: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    model: str = ""
    results: list[dict] = field(default_factory=list)


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

def run_benchmark(model: str = "model2") -> BenchmarkSummary:
    """Benchmark'i calistir ve sonuclari dondur."""

    resolver = IntentResolver(model=model)
    kf = KeywordPreFilter()
    summary = BenchmarkSummary(model=model, total=len(TEST_CASES))

    latencies: list[float] = []

    for idx, (input_text, expected) in enumerate(TEST_CASES, 1):
        logger.info("  [%02d/%02d] %s", idx, summary.total, input_text[:60])

        result = CaseResult(
            input_text=input_text,
            expected=expected.value,
            actual="",
            confidence=0.0,
            keyword_suggestion=None,
            correct=False,
            latency_ms=0.0,
        )

        # Keyword pre-filter
        kw_suggest = kf.suggest(input_text)
        result.keyword_suggestion = kw_suggest.value if kw_suggest else None

        try:
            t0 = time.monotonic()
            intent = resolver.resolve(input_text)
            elapsed_ms = (time.monotonic() - t0) * 1000

            result.actual = intent.intent_type.value
            result.confidence = intent.confidence
            result.latency_ms = round(elapsed_ms, 1)
            result.correct = (intent.intent_type == expected)

            latencies.append(elapsed_ms)

            if result.correct:
                summary.correct += 1
            else:
                summary.incorrect += 1
                logger.warning(
                    "    YANLIS: beklenen=%s, gerceklesen=%s (conf=%.2f)",
                    expected.value, intent.intent_type.value, intent.confidence,
                )

        except Exception as exc:
            result.error = str(exc)
            summary.errors += 1
            logger.error("    HATA: %s", exc)

        summary.results.append(asdict(result))

    # Ozet metrikleri hesapla
    if latencies:
        summary.avg_latency_ms = round(sum(latencies) / len(latencies), 1)
        summary.max_latency_ms = round(max(latencies), 1)
        summary.min_latency_ms = round(min(latencies), 1)

    assessed = summary.correct + summary.incorrect
    summary.accuracy_pct = round(
        (summary.correct / assessed * 100) if assessed > 0 else 0.0, 1,
    )

    return summary


def print_summary(s: BenchmarkSummary) -> None:
    """Tablo formatinda ozet yazdir."""
    print("\n" + "=" * 60)
    print("  INTENT BENCHMARK SONUCLARI")
    print("=" * 60)
    print(f"  Model          : {s.model}")
    print(f"  Toplam Test    : {s.total}")
    print(f"  Dogru          : {s.correct}")
    print(f"  Yanlis         : {s.incorrect}")
    print(f"  Hata           : {s.errors}")
    print(f"  Dogruluk       : {s.accuracy_pct}%")
    print(f"  Ort. Latency   : {s.avg_latency_ms} ms")
    print(f"  Min Latency    : {s.min_latency_ms} ms")
    print(f"  Max Latency    : {s.max_latency_ms} ms")
    print("=" * 60)

    # Yanlis sonuclari listele
    incorrect = [r for r in s.results if not r["correct"] and r["error"] is None]
    if incorrect:
        print("\n  YANLIS SONUCLAR:")
        for r in incorrect:
            print(f"    - [{r['expected']}] -> [{r['actual']}] "
                  f"(conf={r['confidence']:.2f}): {r['input_text'][:50]}")

    errors = [r for r in s.results if r["error"] is not None]
    if errors:
        print("\n  HATALAR:")
        for r in errors:
            print(f"    - {r['error']}: {r['input_text'][:50]}")


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Intent Benchmark Runner")
    parser.add_argument("--model", default="model2", help="Ollama model adi")
    parser.add_argument("--output", default=None, help="Sonuc JSON dosya yolu")
    args = parser.parse_args()

    logger.info("Benchmark baslatiliyor (model=%s, %d test)...", args.model, len(TEST_CASES))

    summary = run_benchmark(model=args.model)
    print_summary(summary)

    # JSON cikti
    output_path = args.output or f"temp/benchmark_{args.model}_{int(time.time())}.json"
    out = Path(PROJECT_ROOT) / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Sonuclar yazildi: %s", out)


if __name__ == "__main__":
    main()
