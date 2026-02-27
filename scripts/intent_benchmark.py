#!/usr/bin/env python3
"""Intent Benchmark Script — Sprint 3.6 Track C4 + Sprint 3.7 Hierarchical

30 ornek girdi ile IntentResolver / HierarchicalResolver dogruluk ve latency
olcumu yapar. Sonuclari JSON ve ozet tablo olarak yazar.

Kullanim:
    python scripts/intent_benchmark.py                          # Flat (varsayilan)
    python scripts/intent_benchmark.py --model whiterabbitneo   # Farkli model
    python scripts/intent_benchmark.py --hierarchical           # 2-asamali
    python scripts/intent_benchmark.py --hierarchical --compare # Flat vs Hierarchical
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
from src.ai.schemas import IntentType, CategoryType, get_category_for_intent
from src.ai.hierarchical_resolver import HierarchicalResolver

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# TEST CASES — 30 ornek
# =============================================================================
# (kullanici_girdisi, beklenen_intent, beklenen_kategori)

TEST_CASES: list[tuple[str, IntentType, CategoryType]] = [
    # Host Discovery (3)
    ("192.168.1.0/24 agindaki aktif cihazlari bul", IntentType.HOST_DISCOVERY, CategoryType.SCANNING),
    ("yerel agda ping sweep yap", IntentType.HOST_DISCOVERY, CategoryType.SCANNING),
    ("10.0.0.0/16 agindaki canli hostlari kesfet", IntentType.HOST_DISCOVERY, CategoryType.SCANNING),

    # Port Scan (3)
    ("192.168.1.5 uzerinde acik portlari tara", IntentType.PORT_SCAN, CategoryType.SCANNING),
    ("hedef sunucunun port 1-1024 arasini tara", IntentType.PORT_SCAN, CategoryType.SCANNING),
    ("SYN scan yap 10.0.0.1 adresine", IntentType.PORT_SCAN, CategoryType.SCANNING),

    # Service Detection (2)
    ("192.168.1.1 uzerindeki servislerin versiyonlarini tespit et", IntentType.SERVICE_DETECTION, CategoryType.SCANNING),
    ("banner grab yap hedef sunucuya", IntentType.SERVICE_DETECTION, CategoryType.SCANNING),

    # OS Detection (2)
    ("hedef makinenin isletim sistemini tespit et", IntentType.OS_DETECTION, CategoryType.SCANNING),
    ("OS fingerprint yap 192.168.1.100 icin", IntentType.OS_DETECTION, CategoryType.SCANNING),

    # Vuln Scan (3)
    ("192.168.1.1 uzerinde zafiyet taramasi yap", IntentType.VULN_SCAN, CategoryType.SCANNING),
    ("nmap nse scriptleriyle vulnerability scan baslat", IntentType.VULN_SCAN, CategoryType.SCANNING),
    ("hedef sunucudaki guvenlik aciklarini tara", IntentType.VULN_SCAN, CategoryType.SCANNING),

    # SSL Scan (2)
    ("example.com icin SSL sertifika analizi yap", IntentType.SSL_SCAN, CategoryType.SCANNING),
    ("TLS cipher konfigurasyonunu kontrol et", IntentType.SSL_SCAN, CategoryType.SCANNING),

    # Web Dir Enum (2)
    ("http://target.com uzerinde dizin taramasi yap", IntentType.WEB_DIR_ENUM, CategoryType.WEB),
    ("gobuster ile gizli path ara", IntentType.WEB_DIR_ENUM, CategoryType.WEB),

    # Web Vuln Scan (2)
    ("nikto ile web zafiyet taramasi yap", IntentType.WEB_VULN_SCAN, CategoryType.WEB),
    ("web sunucusundaki zafiyetleri tara", IntentType.WEB_VULN_SCAN, CategoryType.WEB),

    # DNS Lookup (2)
    ("example.com icin DNS sorgulama yap", IntentType.DNS_LOOKUP, CategoryType.RECON),
    ("MX record kayitlarini sorgula", IntentType.DNS_LOOKUP, CategoryType.RECON),

    # Whois (1)
    ("example.com domain bilgilerini getir", IntentType.WHOIS_LOOKUP, CategoryType.RECON),

    # Subdomain Enum (2)
    ("example.com alt alanlarini kesfet", IntentType.SUBDOMAIN_ENUM, CategoryType.RECON),
    ("subdomain enumeration yap hedef icin", IntentType.SUBDOMAIN_ENUM, CategoryType.RECON),

    # Brute Force SSH (1)
    ("SSH brute force saldirisi yap hedef sunucuya", IntentType.BRUTE_FORCE_SSH, CategoryType.ATTACK),

    # Brute Force HTTP (1)
    ("HTTP login formunu brute force ile test et", IntentType.BRUTE_FORCE_HTTP, CategoryType.ATTACK),

    # SQL Injection (1)
    ("hedef URL uzerinde sqlmap ile SQL injection testi yap", IntentType.SQL_INJECTION, CategoryType.ATTACK),

    # Info Query (2)
    ("nmap nedir ne ise yarar", IntentType.INFO_QUERY, CategoryType.INFO),
    ("port tarama nasil calisir acikla", IntentType.INFO_QUERY, CategoryType.INFO),

    # Unknown / Ambiguous (1)
    ("merhaba bugun hava nasil", IntentType.UNKNOWN, CategoryType.INFO),
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
    # Sprint 3.7: Hierarchical ek alanlari
    expected_category: Optional[str] = None
    actual_category: Optional[str] = None
    category_correct: Optional[bool] = None
    category_confidence: Optional[float] = None
    keyword_bypassed: bool = False


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
    mode: str = "flat"  # "flat" | "hierarchical"
    # Sprint 3.7: Hierarchical ek metrikleri
    category_correct: int = 0
    category_accuracy_pct: float = 0.0
    keyword_bypass_count: int = 0
    results: list[dict] = field(default_factory=list)


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

def run_benchmark(model: str = "model2", hierarchical: bool = False,
                   category_model: str = "whiterabbitneo") -> BenchmarkSummary:
    """Benchmark'i calistir ve sonuclari dondur.
    
    Args:
        model: Ana LLM model (flat mod icin ve hierarchical Stage 2 icin)
        hierarchical: True ise HierarchicalResolver kullanilir
        category_model: Hierarchical Stage 1 icin hafif model
    """

    kf = KeywordPreFilter()
    mode = "hierarchical" if hierarchical else "flat"
    summary = BenchmarkSummary(model=model, total=len(TEST_CASES), mode=mode)

    if hierarchical:
        resolver = HierarchicalResolver(
            category_model=category_model,
            sub_intent_model=model,
        )
        logger.info("Mod: HIERARCHICAL (Stage1=%s, Stage2=%s)", category_model, model)
    else:
        resolver = IntentResolver(model=model)
        logger.info("Mod: FLAT (model=%s)", model)

    latencies: list[float] = []

    for idx, (input_text, expected, expected_cat) in enumerate(TEST_CASES, 1):
        logger.info("  [%02d/%02d] %s", idx, summary.total, input_text[:60])

        result = CaseResult(
            input_text=input_text,
            expected=expected.value,
            actual="",
            confidence=0.0,
            keyword_suggestion=None,
            correct=False,
            latency_ms=0.0,
            expected_category=expected_cat.value,
        )

        # Keyword pre-filter
        kw_suggest = kf.suggest(input_text)
        result.keyword_suggestion = kw_suggest.value if kw_suggest else None

        try:
            t0 = time.monotonic()

            if hierarchical:
                # Stage 1 — category
                kw_bypass = kw_suggest is not None
                result.keyword_bypassed = kw_bypass

                if kw_bypass:
                    actual_cat = get_category_for_intent(kw_suggest)
                    result.category_confidence = 1.0
                    summary.keyword_bypass_count += 1
                else:
                    cat_result = resolver.resolve_category(input_text)
                    actual_cat = cat_result.category
                    result.category_confidence = cat_result.confidence

                result.actual_category = actual_cat.value
                result.category_correct = (actual_cat == expected_cat)
                if result.category_correct:
                    summary.category_correct += 1

                # Full pipeline
                intent = resolver.resolve(input_text)
            else:
                intent = resolver.resolve(input_text)
                # Flat modda da kategori bilgisi turet
                result.actual_category = get_category_for_intent(intent.intent_type).value
                result.category_correct = (result.actual_category == expected_cat.value)

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
    summary.category_accuracy_pct = round(
        (summary.category_correct / summary.total * 100) if summary.total > 0 else 0.0, 1,
    )

    return summary


def print_summary(s: BenchmarkSummary) -> None:
    """Tablo formatinda ozet yazdir."""
    print("\n" + "=" * 60)
    print(f"  INTENT BENCHMARK SONUCLARI ({s.mode.upper()})")
    print("=" * 60)
    print(f"  Model          : {s.model}")
    print(f"  Mod            : {s.mode}")
    print(f"  Toplam Test    : {s.total}")
    print(f"  Dogru          : {s.correct}")
    print(f"  Yanlis         : {s.incorrect}")
    print(f"  Hata           : {s.errors}")
    print(f"  Dogruluk       : {s.accuracy_pct}%")
    print(f"  Ort. Latency   : {s.avg_latency_ms} ms")
    print(f"  Min Latency    : {s.min_latency_ms} ms")
    print(f"  Max Latency    : {s.max_latency_ms} ms")

    if s.mode == "hierarchical":
        print(f"  --- Stage 1 (Category) ---")
        print(f"  Kategori Dogru : {s.category_correct}/{s.total}")
        print(f"  Kategori Dogruluk: {s.category_accuracy_pct}%")
        print(f"  Keyword Bypass : {s.keyword_bypass_count}/{s.total}")

    print("=" * 60)

    # Yanlis sonuclari listele
    incorrect = [r for r in s.results if not r["correct"] and r["error"] is None]
    if incorrect:
        print("\n  YANLIS SONUCLAR:")
        for r in incorrect:
            cat_info = ""
            if r.get("actual_category"):
                cat_ok = "OK" if r.get("category_correct") else "MISS"
                cat_info = f" [cat:{r['actual_category']}({cat_ok})]"
            print(f"    - [{r['expected']}] -> [{r['actual']}] "
                  f"(conf={r['confidence']:.2f}){cat_info}: {r['input_text'][:50]}")

    errors = [r for r in s.results if r["error"] is not None]
    if errors:
        print("\n  HATALAR:")
        for r in errors:
            print(f"    - {r['error']}: {r['input_text'][:50]}")


def print_comparison(flat: BenchmarkSummary, hier: BenchmarkSummary) -> None:
    """Flat vs Hierarchical karsilastirma tablosu."""
    print("\n" + "=" * 70)
    print("  FLAT vs HIERARCHICAL KARSILASTIRMA")
    print("=" * 70)
    print(f"  {'Metrik':<28} {'Flat':>15} {'Hierarchical':>15}")
    print(f"  {'-' * 28} {'-' * 15} {'-' * 15}")
    print(f"  {'Model':<28} {flat.model:>15} {hier.model:>15}")
    print(f"  {'Dogruluk (%)':<28} {flat.accuracy_pct:>14.1f}% {hier.accuracy_pct:>14.1f}%")
    print(f"  {'Dogru / Toplam':<28} {flat.correct:>10}/{flat.total:<4} {hier.correct:>10}/{hier.total:<4}")
    print(f"  {'Ort. Latency (ms)':<28} {flat.avg_latency_ms:>15.1f} {hier.avg_latency_ms:>15.1f}")
    print(f"  {'Min Latency (ms)':<28} {flat.min_latency_ms:>15.1f} {hier.min_latency_ms:>15.1f}")
    print(f"  {'Max Latency (ms)':<28} {flat.max_latency_ms:>15.1f} {hier.max_latency_ms:>15.1f}")
    print(f"  {'Kategori Dogruluk (%)':<28} {'N/A':>15} {hier.category_accuracy_pct:>14.1f}%")
    print(f"  {'Keyword Bypass':<28} {'N/A':>15} {hier.keyword_bypass_count:>15}")
    print("=" * 70)

    delta = hier.accuracy_pct - flat.accuracy_pct
    sign = "+" if delta >= 0 else ""
    print(f"\n  Dogruluk farki: {sign}{delta:.1f}%")

    if flat.avg_latency_ms > 0:
        speed = hier.avg_latency_ms / flat.avg_latency_ms
        print(f"  Latency orani: {speed:.2f}x ({'yavas' if speed > 1 else 'hizli'})")


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Intent Benchmark Runner")
    parser.add_argument("--model", default="model2", help="Ollama model adi (flat & Stage 2)")
    parser.add_argument("--category-model", default=None,
                        help="Hierarchical Stage 1 icin model (default: SENTINEL_CATEGORY_MODEL env veya whiterabbitneo)")
    parser.add_argument("--hierarchical", action="store_true",
                        help="2-asamali HierarchicalResolver kullan")
    parser.add_argument("--compare", action="store_true",
                        help="Flat ve Hierarchical sonuclarini karsilastir")
    parser.add_argument("--output", default=None, help="Sonuc JSON dosya yolu")
    args = parser.parse_args()

    logger.info("Benchmark baslatiliyor (model=%s, %d test)...", args.model, len(TEST_CASES))

    if args.compare:
        logger.info(">>> FLAT mod calistiriliyor...")
        flat_summary = run_benchmark(model=args.model, hierarchical=False)
        print_summary(flat_summary)

        logger.info(">>> HIERARCHICAL mod calistiriliyor...")
        hier_summary = run_benchmark(
            model=args.model,
            hierarchical=True,
            category_model=args.category_model,
        )
        print_summary(hier_summary)

        print_comparison(flat_summary, hier_summary)

        # JSON cikti (her ikisini de kaydet)
        output_path = args.output or f"temp/benchmark_compare_{int(time.time())}.json"
        out = Path(PROJECT_ROOT) / output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        combined = {
            "flat": asdict(flat_summary),
            "hierarchical": asdict(hier_summary),
        }
        out.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Sonuclar yazildi: %s", out)

    else:
        summary = run_benchmark(
            model=args.model,
            hierarchical=args.hierarchical,
            category_model=args.category_model,
        )
        print_summary(summary)

        mode_tag = "hier" if args.hierarchical else "flat"
        output_path = args.output or f"temp/benchmark_{mode_tag}_{args.model}_{int(time.time())}.json"
        out = Path(PROJECT_ROOT) / output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Sonuclar yazildi: %s", out)


if __name__ == "__main__":
    main()
