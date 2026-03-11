# Hierarchical Intent Design — Hiyerarsik Niyet Cozumleme

> Guncel Not (4 Mart 2026): Hiyerarsik intent cozumleme aktif kullanimdadir. Benchmark raporlama politikasi hierarchical-only olarak surdurulur.

> **Durum**: Forward-Reference (Tasarim belgesi, uygulama Sprint 4+)
> **Sprint**: 3.6 Track C6
> **Yazar**: SENTINEL AI Dev Team

---

## 1. Motivasyon

Mevcut Action Planner v2.1, tek-katmanli (flat) bir IntentType enum'u kullanir
(17 intent). Kullanici girdileri arttikca bu yaklasim sunlari zorlastirir:

| Sorun | Ornek |
|-------|-------|
| LLM karar alani buyur | 17 secenekten dogruyu bulmak 5 kategoriden secmekten zor |
| Ince anlamsal farklar | `vuln_scan` vs `web_vuln_scan` karismasi |
| Yeni intent eklemek riskli | Her yeni intent accuracy dusurur |
| Prompt boyutu buyur | Tum intent'ler tek prompt'a gomulur |

## 2. Onerilen Mimari: 2-Asamali Intent Resolution

```
Kullanici Girdisi
        |
        v
  +-----------+
  | Stage 1   |  Kategori siniflandirma (5 secenekten 1)
  | Category  |  Hizli, az token, yuksek dogruluk
  +-----------+
        |
        v
  +-----------+
  | Stage 2   |  Kategori icinde spesifik intent (max 4-5 secenek)
  | Sub-Intent|  Daraltilmis karar alani
  +-----------+
        |
        v
   Intent + confidence
```

### 2.1 Kategori Taksonomisi

```
SENTINEL_CATEGORIES = {
    "scanning": [
        "host_discovery",
        "port_scan",
        "service_detection",
        "os_detection",
        "vuln_scan",
        "ssl_scan"
    ],
    "web": [
        "web_dir_enum",
        "web_vuln_scan"
    ],
    "recon": [
        "dns_lookup",
        "whois_lookup",
        "subdomain_enum"
    ],
    "attack": [
        "brute_force_ssh",
        "brute_force_http",
        "sql_injection"
    ],
    "info": [
        "info_query",
        "unknown"
    ]
}
```

### 2.2 Calisma Akisi

1. **Stage 1 — Category Resolver**
   - Prompt sadece 5 kategori icerir
   - Model: Hafif model (orn. phi3.5, ~1-2s)
   - Cikti: `{ "category": "scanning", "confidence": 0.95 }`

2. **Stage 2 — Sub-Intent Resolver**
   - Prompt sadece secilen kategorinin intent'lerini icerir
   - Model: Ana model (Qwen 2.5 3B)
   - Cikti: `{ "intent": "port_scan", "target": "...", "confidence": 0.92 }`

3. **Keyword Pre-Filter Integration**
   - C2'deki `KeywordPreFilter` Stage 1'i bypass edebilir
   - Yuksek confidence keyword eslesmesi dogrudan Stage 2'ye yonlendirir

## 3. Arayuz Tasarimi (Interface)

### 3.1 HierarchicalResolver

```python
from abc import ABC, abstractmethod
from typing import Optional

class CategoryResult:
    """Stage 1 sonucu."""
    category: str          # "scanning" | "web" | "recon" | "attack" | "info"
    confidence: float      # 0.0 - 1.0
    raw_response: dict

class HierarchicalResolver(ABC):
    """2-asamali intent cozumleme arayuzu."""

    @abstractmethod
    def resolve_category(self, user_input: str) -> CategoryResult:
        """Stage 1: Kullanici girdisini kategoriye siniflandir."""
        ...

    @abstractmethod
    def resolve_sub_intent(
        self,
        user_input: str,
        category: str,
    ) -> "Intent":
        """Stage 2: Kategori icindeki spesifik intent'i coz."""
        ...

    def resolve(self, user_input: str) -> "Intent":
        """Tam pipeline: Category -> Sub-Intent."""
        cat = self.resolve_category(user_input)
        return self.resolve_sub_intent(user_input, cat.category)
```

### 3.2 Prompt Sablonlari

**Stage 1 (Category) Prompt:**
```
Kullanicinin niyetini asagidaki 5 kategoriden birine siniflandir:
- scanning: Ag tarama (port, host, servis, OS, zafiyet, SSL)
- web: Web uygulamasi testi (dizin, web zafiyet)
- recon: Bilgi toplama (DNS, WHOIS, subdomain)
- attack: Saldiri (brute force, SQL injection)
- info: Bilgi sorusu veya belirsiz

JSON ciktisi: { "category": "...", "confidence": 0.X }
```

**Stage 2 (Sub-Intent) Prompt:**
```
Kategori: {category}
Mevcut intent'ler: {intent_list}
Kullanici girdisi: {user_input}

JSON ciktisi: { "intent": "...", "target": "...", "options": {...}, "confidence": 0.X }
```

## 4. Beklenen Kazanimlar

| Metrik | Mevcut (Flat) | Hiyerarsik (Tahmini) |
|--------|---------------|----------------------|
| Stage 1 Dogruluk | - | ~98% (5 sinif) |
| Genel Dogruluk | ~85-90% | ~93-96% |
| Prompt Token | ~500 | Stage1: ~100, Stage2: ~200 |
| Toplam Latency | ~3-5s | ~2-4s (paralel mumkun) |
| Yeni Intent Ekleme | Tum prompt guncelle | Sadece ilgili kategori |

## 5. Migration Stratejisi

1. `HierarchicalResolver` sinifi `src/ai/` altinda implement edilir
2. Mevcut `IntentResolver` adapter olarak kalmaya devam eder (backward compat)
3. `AIOrchestrator` bir feature flag ile hiyerarsik modu aktive eder
4. Benchmark (C4) ile flat vs hierarchical karsilastirilir
5. Full migration sadece dogruluk artisi onaylandiktan sonra yapilir

## 6. Uygulama Zamanlama

- **Sprint 3.3**: Prototip (HierarchicalResolver + Category/Sub-Intent prompt + benchmark)
- **Sprint 3.3+**: Prompt optimizasyonu + full migration (feature flag ile gecis)

## 7. Riskler ve Azaltmalar

| Risk | Etki | Azaltma |
|------|------|---------|
| 2 LLM call = 2x latency | UX bozulabilir | Keyword bypass, cache, hafif model Stage 1 |
| Category hatasi zincirleme | Yanlis sub-intent | Confidence threshold + fallback flat resolve |
| Prompt senkronizasyonu | Bakım yukü | Kategori taksonomisi tek diktte tutulur |

---

> **Not**: Bu belge tasarim + tarihsel gecis referansi olarak korunur.
> Mevcut kod tabaninda hiyerarsik akis aktif, `IntentResolver` kontrollu fallback rolunde kullanilabilir.
