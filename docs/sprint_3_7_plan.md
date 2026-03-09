# Sprint 3.7 — AI Doğruluk Acil Düzeltmeleri

**Başlangıç:** 9 Mart 2026  
**Tetikleyen:** Kapsamlı Audit Raporu + 200 Vakalık Bilingual Benchmark  
**Öncelik:** P0/P1 — Sprint 4'e geçiş ön koşulu

---

## 1) Motivasyon

9 Mart 2026 tarihli kapsamlı audit raporunda, 200 vakalık bilingual benchmark'ın (100 TR + 100 EN) ortaya koyduğu kritik darboğazlar tespit edilmiştir:

| Metrik | Mevcut | Hedef | Gap |
|--------|--------|-------|-----|
| Intent Doğruluğu | %90.0 | ≥%90 | ✅ Yeterli |
| Kategori Doğruluğu | %95.0 | ≥%90 | ✅ Yeterli |
| **Params Çıkarma** | **%32.0** | **≥%55** | 🔴 -23 pp |
| **Target Çıkarma** | **%70.0** | **≥%80** | 🔴 -10 pp |
| **Exact Match** | **%23.0** | **≥%40** | 🔴 -17 pp |
| Clarification | %98.5 | ≥%95 | ✅ Yeterli |
| Ortalama Latency | 1257ms | ≤2000ms | ✅ Yeterli |

**Temel sorun:** Model intent'i doğru buluyor (%90) ama kullanıcının belirttiği parametreleri (port, timing, scripts) ve hedef bilgisini (IP, domain) tutarlı biçimde çıkaramıyor.

### 1.1) 9 Mart 2026 Uygulama Sonrasi Durum (Guncel)

- Prompt formatting kirigi (KeyError: `"intent_type"`) giderildi.
- Track A/B/C kapsamindaki iyilestirmeler kod tabanina uygulandi.
- Son benchmark (post-fix+tuning):
    - Intent: **%87.0**
    - Params: **%52.5**
    - Target: **%78.5**
    - Exact Match: **%37.0**
- Sprint 3.7 hedeflerine kalan gap:
    - Intent: -3.0 puan
    - Params: -2.5 puan
    - Target: -1.5 puan
    - Exact Match: -3.0 puan
- Latency su an oncelik degil; latency hotfixleri sprint kapanisi sonrasi ele alinacak.

---

## 2) Kapsam Dışı

- UI değişiklikleri (Sprint 4'e kalır)
- Yeni tool ekleme
- Pydantic model dönüşümü (Sprint 4)
- Multi-agent yapı (Sprint 5)

---

## 3) Track A — Parametre Çıkarma İyileştirmesi (P0)

**Problem:** 200 vakadan yalnızca 64'ünde params doğru çıkarılıyor (%32). Özellikle:
- `vuln_scan`, `ssl_scan`, `sql_injection` params: **%0**
- `port_scan` params: zayıf (timing, scan_type kaçırılıyor)
- `dns_lookup` params: record_type genellikle eksik

### A1 — Stage 2 Prompt Parametre Örnekleri

**Durum:** ✅ Tamamlandi

**Dosya:** `src/ai/hierarchical_resolver.py` → `SUB_INTENT_PROMPT_TEMPLATE`

Her intent için params-rich few-shot örnekler eklenmeli. Örnek:

```
Girdi: "192.168.1.1 portlarını T4 hızında SYN taraması ile tara"
Çıktı: {"intent_type": "port_scan", "target": "192.168.1.1", 
        "params": {"timing": 4, "scan_type": "sS"}, "confidence": 0.95}

Girdi: "example.com MX kayıtlarını sorgula"
Çıktı: {"intent_type": "dns_lookup", "target": "example.com",
        "params": {"record_type": "MX"}, "confidence": 0.95}
```

### A2 — Regex Tabanlı ParamExtractor

**Durum:** ✅ Tamamlandi

**Yeni dosya:** `src/ai/param_extractor.py`

LLM'den bağımsız olarak user input'tan parametreleri çıkaran deterministik modül:

```python
class ParamExtractor:
    def extract(user_input: str) -> Dict[str, Any]:
        # Regex patterns:
        # - Port: r"(?:port|ports?)\s*[:=]?\s*([\d,\-]+)"
        # - Timing: r"[Tt](\d)\s|timing\s*[:=]?\s*(\d)"
        # - Scan type: r"(?:SYN|sS|sT|sU|TCP|UDP)\s*(?:tara|scan)"
        # - Record type: r"(MX|A|AAAA|NS|TXT|SOA|CNAME)\s*(?:kayıt|record)"
        # - Extensions: r"(?:uzantı|ext)\w*\s*[:=]?\s*([\w,]+)"
        # - Threads: r"(\d+)\s*thread"
        # - Scripts: r"(?:script|nse)\s*[:=]?\s*([\w,]+)"
```

### A3 — Orchestrator Param Merge

**Durum:** ✅ Tamamlandi

**Dosya:** `src/ai/orchestrator.py` → `process_v2()`

```
LLM params ∪ ParamExtractor params
Kural: LLM'in döndüğü param varsa onu kullan, yoksa regex'ten doldur
```

### A4 — Sıfır-Doğruluk Intent Param Testleri

**Durum:** ✅ Tamamlandi

`vuln_scan`, `ssl_scan`, `sql_injection` için özel test vakaları:

```python
# Test: "192.168.1.1 zafiyet taraması yap vuln scriptleri ile"
# Expected params: {"scripts": "vuln"}

# Test: "example.com SSL sertifikasını kontrol et port 8443"
# Expected params: {"port": 8443}

# Test: "http://target.com/login SQL injection testi level 3 risk 2"  
# Expected params: {"level": 3, "risk": 2}
```

---

## 4) Track B — Target Çıkarma İyileştirmesi (P0)

**Problem:** 200 vakadan yalnızca 140'ında target doğru (%70).

### B1 — Target Pre-Extraction

**Durum:** ✅ Tamamlandi

**Dosya:** `src/ai/param_extractor.py` (ParamExtractor'a eklenir)

```python
def extract_target(user_input: str) -> Optional[str]:
    # IPv4: r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b"
    # Domain: r"\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})\b"
    # URL: r"(https?://[^\s]+)"
```

### B2 — Target Hint Prompt Enjeksiyonu

**Durum:** ✅ Tamamlandi

Stage 2 prompt'a: `"Kullanıcının hedef bilgisi: {target_hint}"` satırı eklenmeli (eğer UI'dan target_hint geliyorsa).

### B3 — Target Fallback Zinciri

**Durum:** ✅ Tamamlandi

```
1. LLM target → varsa kullan
2. Regex extract target → varsa kullan  
3. UI target_hint → varsa kullan
4. null
```

---

## 5) Track C — Intent Sınır Netleştirme (P1)

### C1 — info_query Keyword Filter

**Durum:** ✅ Tamamlandi

**Problem:** info_query recall %50 (12 vakadan 6'sı kaçırılıyor → ssl_scan, service_detection, sql_injection'a gidiyor)

**Çözüm:** `keyword_filter.py`'daki info_query pattern'larını genişlet:
- "ne işe yarar", "farkı nedir", "arasındaki fark", "avantajı", "dezavantajı"
- "how does X work", "difference between", "what is the purpose"
- "explain", "describe", "compare"

### C2 — Web Intent Sınırları

**Durum:** ✅ Tamamlandi

**Problem:** `web_dir_enum` recall %64.3 (14 vakadan 5'i → brute_force_http (2) + web_vuln_scan (3))

**Çözüm:**
- Keyword filter'da: "dizin ara/bul/keşfet", "directory", "gobuster", "dirb" → `web_dir_enum`
- Stage 2 prompt'ta: "web_dir_enum = dizin/dosya keşfi, web_vuln_scan = sunucu zafiyet taraması (nikto)" açıkça belirt

### C3 — Hard Override'ları Kural Motoruna Taşı

**Durum:** ✅ Tamamlandi (minimal kural motoru)

**Problem:** Orchestrator'da `kayıt` kelimesine özel hard-coded override

**Çözüm:** Configurable rule dict:
```python
INTENT_OVERRIDE_RULES = [
    {"pattern": r"(kayıt|record)", "from": "whois_lookup", "to": "dns_lookup", 
     "condition": lambda params: params.get("record_type") is not None},
]
```

### C4 — unknown Routing

**Durum:** ✅ Tamamlandi

**Problem:** 4 `unknown` vakası var ama hepsi `info_query` olarak çözümleniyor (confusion matrix)

**Çözüm:** unknown intent prompt tanımını netleştir: "Eğer kullanıcı siber güvenlikle ilgisiz, anlamsız veya çok belirsiz bir şey soruyorsa → unknown"

---

## 6) Track D — Altyapı ve JSON Güvenilirlik (P1)

### D1 — Hierarchical Resolver JSON Mode ✅

`response_format={"type": "json_object"}` Stage 2'ye eklendi (9 Mart 2026).

### D2 — Modelfile System Prompt ✅

Intent türleri listesi, param talimatı ve multi-param örnek eklendi (9 Mart 2026).

### D3 — LLM Flaky Test İzolasyonu

**Durum:** ✅ Tamamlandi

- `pytest.ini` marker kaydi eklendi
- `src/tests/conftest.py` icinde `--run-llm` / `RUN_LLM_TESTS=1` opt-in mekanizmasi eklendi
- Varsayilan test kosulari LLM testlerini skip ediyor, CI tarafinda `-m "not llm"` kullaniliyor
- Live smoke testi `src/tests/test_llm_integration_smoke.py` ile `@pytest.mark.llm` olarak ayrildi

### D4 — Benchmark Regression Gate

**Durum:** ✅ Tamamlandi

- `scripts/benchmark_gate.py` eklendi (gate orchestrator)
- `scripts/auto_benchmark.py` ile rapor uretip gate sonucunu non-zero exit ile fail ediyor
- CI entegrasyonu `.github/workflows/ci.yml` altinda `benchmark-gate` job'i ile eklendi
- Aktivasyon: `BENCHMARK_GATE_ENABLED=true` repo variable ile kontrollu acilis
- Gate kriterleri: accuracy ≥ %85, latency p95 ≤ 2000ms, errors == 0

---

## 7) Başarı Kriterleri

| Metrik | Sprint 3.7 Öncesi | Hedef |
|--------|-------------------|-------|
| Intent Doğruluğu | %90.0 | ≥%90 (koru) |
| Params Çıkarma | %32.0 | **≥%55** |
| Target Çıkarma | %70.0 | **≥%80** |
| Exact Match | %23.0 | **≥%40** |
| info_query Recall | %50.0 | **≥%75** |
| web_dir_enum Recall | %64.3 | **≥%80** |
| Latency (ort.) | 1257ms | ≤2000ms (koru) |

---

## 8) Risk ve Bağımlılıklar

| Risk | Etki | Azaltma |
|------|------|---------|
| ParamExtractor regex'leri edge case'lerde bozulabilir | Orta | Kapsamlı test seti + benchmark doğrulama |
| Prompt değişiklikleri intent doğruluğunu düşürebilir | Yüksek | Her değişiklik sonrası 200 vakalık benchmark koş |
| num_ctx 4096 sınırı prompt uzunluğunu kısıtlıyor | Düşük | Few-shot örnekleri kısa ve öz tut |

---

## 9) Definition of Done

1. 200 vakalık bilingual benchmark koşulmuş ve hedefler karşılanmış
2. Mevcut test suite'i kırılmamış (76 passed baseline)
3. Yeni modüller (ParamExtractor) için unit testler yazılmış
4. sprint_roadmap.md güncellenmiş

---

## 10) Mevcut Kapanis Durumu

- Tamamlanan gorev: **15/15**
- Kalan gorev: **0** (Sprint 3.7 task listesi acisindan)
- Not: Basari metriklerinin hedefe tam ulasmasi icin ek kalite iterasyonu devam edecek.
