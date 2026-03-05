# Sprint 3.5 Hotfix Changelog

**Tarih:** 5 Mart 2026  
**Kapsam:** Develop branch'ten çekilmesinin ardından yapılan tüm değişiklikler  
**Tetikleyen:** Manuel test sırasında tespit edilen 2 bug + yeni doğruluk benchmark testi talebi

---

## Özet

| # | Değişiklik | Dosya | Tür |
|---|-----------|-------|-----|
| 1 | Yüksek riskli komutlarda onay mekanizması düzeltmesi | `src/ui/main_window.py` | Bug Fix |
| 2 | LLM parse başarısızlığında keyword fallback mekanizması | `src/ai/orchestrator.py` | Bug Fix |
| 3 | Uçtan uca komut üretim doğruluk benchmark testi | `src/tests/test_command_accuracy.py` | Yeni Test |

---

## 1. BUG FIX — Yüksek Riskli Komut Onay Mekanizması

**Dosya:** `src/ui/main_window.py`  
**Sorun:** Ayarlar panelinde (BL-2) "Root komutları için onay iste" ve "Yüksek riskli komutlarda uyar" seçenekleri açık olmasına rağmen, komutlar onay almadan doğrudan çalıştırılıyordu.

### Kök Neden

1. `_load_security_settings()` ve `_apply_security_settings()` metotları sadece 4 anahtarı (`cleanup_days`, `secure_delete`, `font_size`, `language`) yüklüyor/kaydediyordu. Sprint 3.5'te eklenen 3 yeni güvenlik anahtarı (`confirm_root`, `warn_high_risk`, `auto_cleanup`) hiç persist edilmiyordu.

2. `_execute_command()` ve `_execute_command_from_terminal()` metotları sadece `requires_root` flag'ine bakıyordu. Ayarlar panelindeki kullanıcı tercihleri hiçbir zaman kontrol edilmiyordu.

### Uygulanan Değişiklikler

#### 1a. `_load_security_settings()` (satır ~584)

Defaults dict'ine 3 yeni anahtar eklendi ve JSON'dan okunması sağlandı:

```python
defaults = {
    "cleanup_days": 7,
    "secure_delete": True,
    "font_size": 13,
    "language": "en",
    "confirm_root": True,       # YENİ
    "warn_high_risk": True,     # YENİ
    "auto_cleanup": "off",      # YENİ
}
```

JSON okuma bloğuna da aynı 3 anahtar eklendi:

```python
"confirm_root": bool(data.get("confirm_root", defaults["confirm_root"])),
"warn_high_risk": bool(data.get("warn_high_risk", defaults["warn_high_risk"])),
"auto_cleanup": str(data.get("auto_cleanup", defaults["auto_cleanup"])),
```

#### 1b. `_apply_security_settings()` (satır ~619)

Settings dialog'dan gelen yeni ayarların da persist edilmesi sağlandı:

```python
"confirm_root": bool(settings.get("confirm_root", True)),
"warn_high_risk": bool(settings.get("warn_high_risk", True)),
"auto_cleanup": str(settings.get("auto_cleanup", "off")),
```

#### 1c. Yeni metot: `_needs_confirmation()` (satır ~440)

Komut çalıştırma öncesi onay gerekip gerekmediğini belirleyen merkezi kontrol noktası:

```python
def _needs_confirmation(self, requires_root: bool, risk_level: str) -> bool:
    """Check if current security settings require user confirmation."""
    if requires_root:
        return bool(self._security_settings.get("confirm_root", True))
    normalized = self._normalize_risk(risk_level)
    if normalized in ("high", "medium") and self._security_settings.get("warn_high_risk", True):
        return True
    return False
```

**Mantık:**
- `requires_root=True` ise → `confirm_root` ayarına bakar
- Risk seviyesi `high` veya `medium` ise → `warn_high_risk` ayarına bakar
- Her iki ayar da kapalıysa → onay sorulmaz

#### 1d. `_execute_command()` ve `_execute_command_from_terminal()` güncellendi

Eski kod:
```python
if requires_root:
    self._request_root_confirmation(...)
```

Yeni kod:
```python
if self._needs_confirmation(requires_root, risk_level):
    self._request_root_confirmation(...)
```

Ayrıca `start_command()` çağrısındaki `requires_root` parametresi, hardcoded `False` yerine gerçek `requires_root` değerini iletecek şekilde düzeltildi.

---

## 2. BUG FIX — LLM Parse Başarısızlığında Keyword Fallback

**Dosya:** `src/ai/orchestrator.py`  
**Sorun:** Kullanıcı "192.168.1.1 üzerinde zafiyet taraması yap" yazdığında AI yanıtı parse edilemedi hatası veriyordu. Komut üretilmiyordu.

### Kök Neden

1. LLM (Qwen 2.5 3B) parse edilemeyen JSON döndürdü → `IntentResolver` intent'i `UNKNOWN` olarak belirledi ve `needs_clarification=True`, `clarification_reason="AI yanıtı parse edilemedi"` set etti.

2. `KeywordPreFilter` "zafiyet" kelimesini doğru şekilde `VULN_SCAN` olarak eşliyordu, ancak `cross_validate()` sadece loglama yapıyor, keyword önerisini fallback olarak kullanmıyordu.

3. Orchestrator `process_v2()` doğrudan netleştirme mesajı döndürüyordu — keyword filter'ın başarılı eşleşmesini hiç değerlendirmiyordu.

### Uygulanan Değişiklikler

#### 2a. `import re` eklendi (satır 12)

Hedef çıkarma regex'i için gerekli.

#### 2b. Yeni class-level regex + helper metot (satır ~105-120)

```python
_IP_OR_HOST_RE = re.compile(
    r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)"
    r"|"
    r"((?:https?://)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})"
)

def _extract_target_from_input(self, user_input: str) -> Optional[str]:
    """Try to extract an IP address or hostname from raw user text."""
    m = self._IP_OR_HOST_RE.search(user_input)
    if m:
        return m.group(0)
    return None
```

Kullanıcı metninden IP adresi (CIDR destekli) veya domain adını regex ile çıkarır.

#### 2c. Keyword fallback bloğu (satır ~215-239)

`process_v2()` içinde, LLM intent resolution'dan sonra ve netleştirme kontrolünden **önce** eklendi:

```python
# Keyword pre-filter cross-validation (C2)
kf_suggestion = self._keyword_filter.suggest(user_input)
kf_ok, kf_msg = self._keyword_filter.cross_validate(intent.intent_type, user_input)
if not kf_ok:
    logger.info("Keyword cross-validation mismatch: %s", kf_msg)

# ── Keyword fallback: LLM parse başarısızsa keyword önerisini kullan ──
if (
    intent.intent_type == IntentType.UNKNOWN
    and intent.needs_clarification
    and kf_suggestion is not None
    and kf_suggestion != IntentType.UNKNOWN
):
    logger.info(
        "LLM failed (%s), keyword fallback to %s",
        intent.clarification_reason,
        kf_suggestion.value,
    )
    fallback_target = target or intent.target or intent.params.get("target")
    if not fallback_target:
        fallback_target = self._extract_target_from_input(user_input)
    intent = Intent(
        intent_type=kf_suggestion,
        target=fallback_target,
        params=intent.params,
        needs_clarification=False,
        confidence=0.75,
    )
    result["intent"] = intent
    result["agent_observation"] = "keyword_fallback"
```

**Fallback Koşulları (hepsi aynı anda sağlanmalı):**
1. LLM intent'i `UNKNOWN` döndürdü
2. `needs_clarification=True` (parse hatası vs.)
3. Keyword filter'ın önerisi `None` değil
4. Keyword filter'ın önerisi `UNKNOWN` değil

**Davranış:**
- Yeni `Intent` nesnesi oluşturulur: keyword'den gelen intent tipi, 0.75 sabit confidence
- Target: önce mevcut `target` parametresi, yoksa `_extract_target_from_input()` ile metinden çıkarılır
- `agent_observation="keyword_fallback"` ile işaretlenir (loglama/audit amaçlı)
- Pipeline normal akışına devam eder (ToolRegistry → build_command)

---

## 3. YENİ TEST — Komut Üretim Doğruluk Benchmark'ı

**Dosya:** `src/tests/test_command_accuracy.py` (711 satır, yeni oluşturuldu)  
**Amaç:** Deterministik pipeline'ın uçtan uca doğruluk oranını ölçmek. LLM gerektirmez.

### Mimari

```
Pipeline: user_input → KeywordPreFilter → ToolRegistry → IntegratedTool.build_command → FinalCommand
```

### Test Yapısı

- **`AccuracyCase` dataclass:** Her senaryo için prompt, beklenen intent, executable, must_contain, must_not_contain, expected_risk, expected_root, no_command, extra_params alanları
- **75 test senaryosu** — 15 tool kategorisinin tamamını kapsar
- **`_run_pipeline()` helper:** Tek bir case'i pipeline'dan geçirir, her adımı kontrol eder
- **`test_overall_accuracy`:** Tüm case'leri çalıştırıp ASCII-safe rapor yazdırır, %70 minimum eşik
- **`test_individual_case`:** Her senaryoyu parametrize olarak ayrı ayrı test eder

### Kapsanan Tool Kategorileri ve Senaryo Sayıları

| Tool Kategorisi | Senaryo | Beklenen Executable |
|----------------|---------|---------------------|
| HOST_DISCOVERY | 8 | `nmap` (-sn) |
| PORT_SCAN | 8 | `nmap` (-sT) |
| SERVICE_DETECTION | 5 | `nmap` (-sV) |
| OS_DETECTION | 4 | `nmap` (-O) |
| VULN_SCAN | 6 | `nmap` (--script vuln) |
| SSL_SCAN | 5 | `openssl` (s_client) |
| WEB_DIR_ENUM | 5 | `gobuster` (dir) |
| WEB_VULN_SCAN | 5 | powershell.exe |
| DNS_LOOKUP | 5 | `nslookup` |
| WHOIS_LOOKUP | 3 | `whois` |
| SUBDOMAIN_ENUM | 3 | `bash` |
| BRUTE_FORCE_SSH | 3 | `hydra` |
| BRUTE_FORCE_HTTP | 3 | `hydra` |
| SQL_INJECTION | 3 | `sqlmap` |
| INFO_QUERY | 5 | (komut üretmemeli) |
| UNKNOWN | 4 | (komut üretmemeli) |

### Doğrulama Kontrolleri

Her pipeline çalıştırmasında 7 kriter kontrol edilir:

1. **intent_ok** — Keyword filter doğru intent'i döndürdü mü? (uyumlu gruplar kabul edilir: PORT_SCAN↔HOST_DISCOVERY↔SERVICE_DETECTION, WEB_DIR_ENUM↔WEB_VULN_SCAN, BRUTE_FORCE_SSH↔BRUTE_FORCE_HTTP)
2. **command_ok** — `build_command()` başarılı bir komut listesi döndürdü mü?
3. **executable_ok** — Komutun ilk elemanı beklenen executable mı?
4. **contains_ok** — Komut string'inde olması gereken tüm tokenlar var mı?
5. **not_contains_ok** — Komut string'inde olmaması gereken tokenlar yok mu?
6. **risk_ok** — Tool metadata'sındaki risk seviyesi beklenenle eşleşiyor mu?
7. **root_ok** — Komut root flag'leri (-sS, -sU, -O, -A, --privileged) içeriyor/içermiyor mu?

### Rapor Çıktısı

```
========================================================================
  KOMUT URETIM DOGRULUK RAPORU
========================================================================
  Toplam senaryo : 75
  Basarili       : 71
  Basarisiz      : 4
  DOGRULUK ORANI : 94.7%
========================================================================
```

### Teknik Kararlar

- **Windows cp1254 uyumluluğu:** Rapor çıktısı `encode("ascii", errors="replace").decode("ascii")` ile yazılır; Türkçe karakterlerin pytest stdout'ta bozulması önlenir.
- **Brute-force extra_params:** Hydra araçları `username`, `wordlist` gibi zorunlu parametreler gerektirir; bunlar `extra_params` dict ile sağlanır.
- **Web intent fallback target:** URL gerektiren araçlar (WEB_DIR_ENUM, WEB_VULN_SCAN, SQL_INJECTION, BRUTE_FORCE_HTTP) için prompt'ta URL yoksa `http://10.0.0.1` kullanılır.
- **Compatible intent grupları:** Port tarama ailesindeki (HOST_DISCOVERY, PORT_SCAN, SERVICE_DETECTION) yakın eşleşmeler başarılı kabul edilir.

---

## Test Sonuçları

### Doğruluk Benchmark (yeni)

```
75 senaryo → 71 başarılı → %94.7 doğruluk
```

Başarısız 4 senaryo (bilinen keyword filter gap'leri):

| # | Prompt | Neden |
|---|--------|-------|
| 15 | "hedefin portlarini tara" | Keyword filter eşleşmedi (pattern gap) |
| 23 | "OS fingerprint yap 192.168.1.100" | Keyword filter eşleşmedi (pattern gap) |
| 26 | "zafiyet taramasi yap 192.168.1.1" | Komut üretildi ama root flag beklentisi tutmadı |
| 36 | "openssl ile ssl scan yap" | "scan" kelimesi PORT_SCAN olarak eşleşti |

### Mevcut Test Suite

```
1369 test → tamamı passed (2 warning, deprecation)
```

Her iki bug fix'ten sonra mevcut testlerin hiçbiri kırılmadı.

---

## Etkilenen Dosya Özeti

```
src/ui/main_window.py          — 4 bölümde değişiklik (load/apply/needs_confirmation/execute)
src/ai/orchestrator.py          — 3 bölümde değişiklik (import/helper/fallback blok)
src/tests/test_command_accuracy.py — Yeni dosya (711 satır, 75 senaryo)
```
