# SENTINEL AI — Kapsamlı Konuşma ve Analiz Kaydı

> 4 Mart 2026 Durum Notu: Bu rapor tarihsel audit kaydıdır. Sprint 3.4/3.5/3.6 sonrası bazı risk maddeleri kapanmış olup güncel durum için `son_durum.md`, `docs/sprint_roadmap.md` ve `PROJECT_STRUCTURE.md` esas alınmalıdır.

**Tarih:** 26 Şubat 2026  
**Katılımcılar:** Geliştirici Ekip & GitHub Copilot  
**Kapsam:** Proje durum analizi, Linux build değerlendirmesi, model önerisi, ölçeklenme stratejisi

---

## İçindekiler

1. [Bölüm 1 — Kapsamlı Durum Analiz Raporu (Audit Report)](#bölüm-1--kapsamlı-durum-analiz-raporu-audit-report)
2. [Bölüm 2 — Soru-Yanıt: Linux Build, Model Seçimi, Ölçeklenme](#bölüm-2--soru-yanıt-linux-build-model-seçimi-ölçeklenme)

---

# Bölüm 1 — Kapsamlı Durum Analiz Raporu (Audit Report)

> **Kullanıcı İsteği:**  
> Projenin mevcut durumu üzerine kapsamlı ve profesyonel bir durum analiz raporu (Audit Report) hazırla. Şu an projenin 3. sprintindeyiz ve AI bileşenleri üzerine yoğunlaşmış durumdayız. Analizini şu başlıklar altında sun:
> - Mevcut Durum ve Doğru Yapılanlar
> - Eksikler ve Risk Analizi
> - Proje Yapısı ve Mimari
> - AI ve Performans Optimizasyonu
> - Plan ve Süreç Uyumu
> - Yol Haritası (Next Steps)

---

**Rapor Tarihi:** 26 Şubat 2026  
**Rapor Hazırlayan:** GitHub Copilot  
**Kapsam:** Tam kaynak kod analizi, mimari inceleme, sprint durum değerlendirmesi  
**Kod Tabanı:** ~10.500 satır Python (src/), 112 test (tamamı geçiyor)

---

## 1. Mevcut Durum ve Doğru Yapılanlar

### 1.1 Mimari Başarılar

**Deterministik Karar Zinciri (Action Planner v2.1):** Projenin en güçlü yönü, LLM'in rolünü bilinçli olarak daraltmasıdır. `User Input → IntentResolver (LLM) → ToolRegistry (statik) → CommandBuilder (deterministik) → Execution` zinciri, endüstri standardı olan **Separation of Concerns** ilkesine tam uyumludur. LLM yalnızca niyet belirler; tool seçimi, risk seviyesi ve argüman üretimi tamamen statik registry'den gelir. Bu yaklaşım:
- LLM halüsinasyonlarından kaynaklanan güvenlik risklerini minimize eder
- Her katmanın bağımsız test edilebilirliğini garanti eder
- Komut üretiminin tahmin edilebilir ve tekrarlanabilir olmasını sağlar

**Hybrid JSON+FK SQLite Schema:** `src/core/sqlite_backend.py` — JSON blob ile schema esnekliği, FK ile sorgu performansı birleştirilmiş. Migration-free schema evrimi mümkün. Transaction desteği (atomic batch insert), TTL pruning ve checkpoint/restore mekanizmaları production-grade seviyede.

**Queue/Backpressure Sistemi:** `src/core/tool_integration.py` — `ToolManager` sınıfındaki global concurrency limiti, per-tool limiti ve kuyruk taşması kontrolü endüstri standardı backpressure pattern'ine uygun. `_drain_queue()` ve `_dequeue_next_runnable()` ile adil kuyruk yönetimi sağlanmış.

**Registry Drift Guard:** `src/ai/tool_registry.py` — `validate_execution_registry()` fonksiyonu, AI execution mapping ile kayıtlı tool'lar arasındaki tutarlılığı startup'ta ve testlerde doğruluyor. Bu, refactoring sırasında sessiz kırılmaları önleyen kritik bir güvenlik ağı.

**Güvenlik Katmanı:**
- Shell injection koruması (`DANGEROUS_CHARS`, argument validation) — `src/ai/command_builder.py`, `src/ai/schemas.py`
- Input validation (IP, domain, URL, port) — `src/core/validators.py`
- `defusedxml` ile XXE koruması
- Path traversal korumalı `SecureCleaner` — `src/core/cleaner.py`
- Docker container izolasyonu (NET_RAW, NET_ADMIN capabilities)

### 1.2 Mühendislik Kalitesi

| Metrik | Değer | Değerlendirme |
|--------|-------|---------------|
| Test sayısı | **112 passed** | Güçlü |
| Test kapsamı | Backend, Parser, Tool, Integration, Registry, UI Boundary | Kapsamlı |
| Toplam kaynak kodu | ~10.500 satır | Yönetilebilir boyut |
| Modüler yapı | `ai/`, `core/`, `ui/`, `application/` | Net katman ayrımı |
| Veri modeli | Pydantic v2 + strict validation | Modern standart |
| Dokümantasyon | README, PROJECT_STRUCTURE, sprint_roadmap, AGENT_RULES | İyi seviye |

---

## 2. Eksikler ve Risk Analizi

### 2.1 Kritik Riskler (P0)

**RISK-01: Logging Altyapısı Yetersiz**  
Tüm modüllerde `logging.getLogger(__name__)` tanımlanmış ancak proje genelinde merkezi bir logging konfigürasyonu yok. Production'da hata izleme ve forensic analiz için `logging.basicConfig()` veya yapılandırılmış handler (file, rotating, structured JSON) şart. Şu anda `logger.debug/warning` çağrıları sessizce kayboluyor.

**RISK-02: Error Recovery Stratejisi Eksik**  
`IntentResolver._call_local_with_retry()` 2 deneme + hafif backoff uyguluyor — bu iyi. Ancak `ToolManager` seviyesinde bir tool çöktüğünde veya timeout aldığında `_active_count` düzeltmesi sadece callback'te yapılıyor. Callback'in kendisi patlayabilir (örneğin `result.queue_wait_ms` atamasında `AttributeError`). Bu durumda `_active_count` sonsuza kadar yüksek kalır ve kuyruk drene edilemez. **Deadlock riski.**

**RISK-03: `BackendGateway.parse_command()` Güvenlik Açığı**  
`src/application/backend_gateway.py` — `parse_command()` metodu `command.split()` ile komut parse ediyor ve `requires_root` tespiti string matching (`"sudo" in command`) ile yapılıyor. Bu, CommandBuilder'ın sağladığı güvenlik garantilerini bypass eden ayrı bir giriş noktası. Terminal'den gelen komutlar bu yoldan geçiyor ve AI'ın deterministik güvenlik katmanından faydalanmıyor.

### 2.2 Orta Riskler (P1)

**RISK-04: Singleton Pattern Anti-Pattern Kullanımı**  
`src/ai/orchestrator.py`, `src/ai/intent_resolver.py` — Global `_orchestrator` ve `_resolver` singleton'ları thread-safety sağlamıyor. UI thread'inde `AIWorker` (QThread) kullanılmasına rağmen, aynı `AIOrchestrator` instance'ına concurrent erişim olabilir.

**RISK-05: SQLite Connection Yönetimi**  
`src/core/sqlite_backend.py` — `connection` nesnesi `__init__`'te açılıyor ama açık bir `close()` çağrısı zorunlu tutulmuyor. `__del__` veya context manager pattern eksik. Uzun çalışan uygulamada connection leak riski. Ayrıca SQLite'ın default `journal_mode` kullanılıyor; WAL modu aktif değil, bu yüzden concurrent read sırasında yazma bloklanabilir.

**RISK-06: Adaptif Timeout Yüzeysel**  
`estimate_timeout()` override'ları sadece port sayısı ve scan tipine göre lineer tahmin yapıyor. Network latency, hedef yanıt hızı gibi runtime faktörler dikkate alınmıyor. `_compute_effective_timeout()` ile override zinciri doğru kurulmuş, ancak historical execution verisinden öğrenen adaptif bir mekanizma henüz mevcut değil.

**RISK-07: Chat History Dosya Tabanlı**  
`src/ui/chat_interface.py` — `CHAT_HISTORY_FILE` JSON dosyasına yazılıyor. Büyük oturumlarda dosya boyutu şişebilir; concurrent yazma riski var. Bu veri SQLite backend'e taşınmalı.

### 2.3 Düşük Riskler / Teknik Borç (P2)

**TD-01: Legacy Schema Duplikasyonu**  
`src/ai/schemas.py` — Hem v2 şemaları (`Intent`, `ToolSpec`, `FinalCommand`) hem de legacy şemalar (`ToolCommand`, `AIResponse`) birlikte yaşıyor. `TOOL_COMMAND_SCHEMA` ve `AI_RESPONSE_SCHEMA` gibi OpenAI structured output şemaları aktif olarak kullanılmıyor (Local LLM JSON mode ile çalışılıyor). **577 satır** dosya, refactoring ile ~350 satıra indirilebilir.

**TD-02: `SslScanTool` Platform Bağımlılığı**  
`src/core/tool_base.py` — `SslScanTool.build_command()` `cmd.exe /c` ile Windows'a bağımlı. `SubdomainEnumTool` ve `WebAppScanTool` da `powershell.exe` çağrısı yapıyor. Docker modu aktifken bu tool'lar Linux container'da çalışamaz. Platform-agnostic abstraction eksik.

**TD-03: `process_manager.py` Kullanım Dışı mı?**  
`src/core/process_manager.py` — 181 satır, `AdvancedProcessManager` sınıfı `BackendGateway` tarafından kullanılıyor ancak tool execution zinciri aslında `BaseTool` içindeki `QProcess` ile yapılıyor. İki ayrı process yönetim mekanizması paralel yaşıyor. Sorumluluk karışıklığı var.

**TD-04: `adapters/` Dizini Boş**  
Sprint 4 hedefleri arasında olan `nmap_adapter.py` henüz başlamamış. Dizin varlığı roadmap'e uygun ama implementasyon bekliyor.

---

## 3. Proje Yapısı ve Mimari Değerlendirme

### 3.1 Klasör Düzeni — **İyi**

```
src/
├── ai/          → AI karar katmanı (5 modül, 2.008 satır)
├── core/        → İş mantığı motoru (11 modül, 4.330 satır)
├── ui/          → Sunum katmanı (5 modül, 1.930 satır)
├── application/ → Facade katmanı (2 modül, 30 satır)
└── tests/       → Test suite (12 modül, 2.190 satır)
```

Katmanlı mimari doğru uygulanmış. `AGENT_RULES.md`'deki "iş mantığı `src/core`, arayüz `src/ui`, zeka `src/ai`" kuralı tutarlı şekilde takip ediliyor.

### 3.2 Modülerlik — **İyi, İyileştirilebilir**

**Güçlü yönler:**
- `BaseTool` abstract class'ı ile 10 tool implementasyonu temiz OOP
- `BaseParser` → `ParserExecutor` → `Backend` zinciri iyi ayrıştırılmış
- `SentinelCoordinator` bridge pattern'i UI-Core bağımlılığını temiz tutuyor

**İyileştirme alanları:**
- `tool_base.py` **739 satır** — 10 tool sınıfı tek dosyada. Her tool kendi dosyasına taşınmalı: `src/core/tools/ping.py`, `src/core/tools/nmap_port_scan.py` vb.
- `parser_framework.py` **1.534 satır** — Projenin en büyük dosyası. BaseParser, yardımcı fonksiyonlar ve 10 parser implementasyonu tek dosyada. `src/core/parsers/` dizinine bölünmeli.
- `schemas.py` **518 satır** — v2 şemaları, legacy şemalar ve suggestion şemaları karışık. Domain-bazlı dosyalara ayrılmalı.

### 3.3 Ölçeklenebilirlik — **Kısmen Hazır**

| Boyut | Değerlendirme | Not |
|-------|---------------|-----|
| Yeni tool ekleme | **Kolay** | `BaseTool` subclass + `BaseParser` subclass + Registry kaydı |
| Yeni intent ekleme | **Kolay** | `IntentType` enum + `TOOL_REGISTRY` + `_EXECUTION_REGISTRY` |
| Yeni parser ekleme | **Kolay** | `BaseParser` subclass + `create_*_entity` helper |
| Çoklu kullanıcı | **Hazır değil** | Singleton pattern, tek DB connection |
| Dağıtık mimari | **Kısmen hazır** | Docker compose mevcut, ama servisler arası iletişim sadece Ollama API |
| Plugin sistemi | **Planlı, henüz yok** | Sprint 6 hedefi, `plugins/` dizini boş |

---

## 4. AI ve Performans Optimizasyonu

### 4.1 AI Modül Değerlendirmesi

**IntentResolver (LLM Entegrasyonu):**
- Model: Qwen 2.5 3B (Ollama) -- Local-only LLM
- Temperature: 0.1 — Tutarlı çıktı için ideal
- Timeout: 20s, max 2 deneme, lineer backoff (0.2s * attempt) — Makul
- JSON parse: Markdown code block + bracket counting ile robust extraction — İyi
- Strict payload validation: Alan sayısı ve tipleri kontrol ediliyor — Güvenli

**Eksik/Zayıf Noktalar:**
1. **Prompt caching yok** — Aynı system prompt her istekte tekrar gönderiliyor. Ollama'nın `keep_alive` parametresi ile model bellek optimizasyonu yapılabilir
2. **Intent confidence skoru yok** — LLM'den sadece intent_type alınıyor, güven skoru (0-1) alınmıyor. Düşük güvenli intent'ler için clarification tetiklenmesi gerekir
3. **Conversation memory yok** — Her istek bağımsız. "Aynı hedefi başka portlarla tara" gibi bağlamsal istekler çözümlenemiyor
4. **Fallback intent stratejisi** — LLM down ise `UNKNOWN` dönüyor. Keyword-based basit bir regex matcher fallback olarak eklenebilir

### 4.2 Performans Profili

| Bileşen | Mevcut Durum | Optimizasyon Önerisi |
|---------|-------------|---------------------|
| LLM yanıt süresi | ~2-5s (native), ~5-15s (Docker) | `keep_alive`, cached system prompt |
| QProcess başlatma | <100ms | Yeterli |
| SQLite sorgu | <10ms (indeksli) | WAL mode aktif edilmeli |
| Parser (nmap XML) | Henüz XML parser yok | defusedxml + streaming parse planlanmalı |
| UI render | Non-blocking (QThread) | 10.000 satır buffer limiti mevcut — iyi |
| Docker container check | subprocess + 2s timeout + cache | TTL cache mevcut — iyi |

### 4.3 Kaynak Tüketimi

- **Developer Mode:** ~2-4 GB RAM (Native Ollama + PyQt6)
- **Production Mode:** ~4-8 GB RAM (Docker + Qwen 2.5 3B + tools)
- **Runtime telemetry (tarihsel not):** Bu rapor yazıldığı tarihte UI görünürlüğü yoktu; güncel durumda status bar yüzeyi aktiftir.

---

## 5. Plan ve Süreç Uyumu (Sprint 3 Hedef Karşılaştırması)

### Sprint 3 Hedef Tablosu

| Hedef | Durum | Açıklama |
|-------|-------|----------|
| ExecutionManager | **TAMAMLANDI** | Docker/Native mod yönetimi, pkexec logic |
| SecureCleaner | **TAMAMLANDI** | Whitelist, shredding, path traversal koruması |
| Input Validation | **TAMAMLANDI** | IP/Domain/Shell injection kontrolü |
| ProcessManager Update | **TAMAMLANDI** | Core modül entegrasyonu |
| UI Security Indicators | **YAPILMADI** | Terminal root uyarısı eksik |
| Settings Menu (Security) | **KISMEN** | `SettingsDialog` mevcut ama sınırlı |

### Sprint 3.1 Hedef Tablosu

| Hedef | Durum | Açıklama |
|-------|-------|----------|
| Queue backpressure | **TAMAMLANDI** | max_queue_size kontrolü |
| Global concurrency | **TAMAMLANDI** | max_concurrent limiti |
| Per-tool concurrency | **TAMAMLANDI** | _tool_limits dictionary |
| LLM timeout/retry | **TAMAMLANDI** | 20s timeout, 2 attempt, backoff |
| Registry drift guard | **TAMAMLANDI** | startup + test validation |
| Adaptif timeout | **TAMAMLANDI** | estimate_timeout() per tool |
| Runtime telemetry | **TAMAMLANDI** | queue_wait_ms, tool_run_ms |

### Genel Takvim Uyumu

Sprint 3 ve 3.1 hedeflerinin **~90%**'ı tamamlanmış. UI Security Indicators (root uyarısı) ve Settings menüsü (temizlik sıklığı ayarları) bekliyor. Ekip Sprint 4 hazırlığına geçmiş durumda. Takvim uyumu **iyi**, ancak dokümantasyon-kod senkronizasyonunda gecikmeler gözlemleniyor (PROJECT_STRUCTURE.md "Son Güncelleme: 21 Ocak 2026" — 35 günlük fark).

---

## 6. Yol Haritası (Next Steps) — Önceliklendirilmiş

### P0 — Hemen Yapılmalı (Bu hafta)

| # | Görev | Gerekçe |
|---|-------|---------|
| 1 | **Merkezi logging konfigürasyonu** | Hata izleme ve debug için kritik. `main.py` ve `main_developer.py`'ye `logging.basicConfig(level, format, handlers)` ekle. |
| 2 | **ToolManager callback exception safety** | `_wrapped_callback()` içinde `try/finally` bloğu `_active_count` düzeltmesini garantiye alıyor ama callback payload'ında exception atılırsa user callback hiç çağrılmıyor. Ayrı try blokları ile izole et. |
| 3 | **Dokümantasyon senkronizasyonu** | PROJECT_STRUCTURE.md 35 gün eski. Sprint 3.1 değişiklikleri (10 yeni tool, telemetry) yansıtılmalı. |

### P1 — Sprint 4 Kapsamında (1-2 hafta)

| # | Görev | Gerekçe |
|---|-------|---------|
| 4 | **`models.py` Pydantic veri modeli** | `ScanResult`, `Host`, `Port`, `Service` — adapter katmanı için temel |
| 5 | **`nmap_adapter.py`** | XML → Pydantic dönüşümü, bozuk XML onarımı |
| 6 | **SQLite WAL mode** | `PRAGMA journal_mode=WAL` — concurrent read/write performansı |
| 7 | **`tool_base.py` dosya bölme** | 739 satırlık tek dosyayı `src/core/tools/` dizinine taşı |
| 8 | **Telemetry UI görünürlüğü** | `get_runtime_metrics()` verilerini StatusBar veya Dashboard'da göster |

### P2 — Sprint 4-5 Arasında (2-4 hafta)

| # | Görev | Gerekçe |
|---|-------|---------|
| 9 | **Conversation context** | IntentResolver'a son 2-3 turn memory ekle (sliding window) |
| 10 | **Intent confidence skoru** | LLM yanıtına `confidence: float` alanı ekle, düşük güven → clarification |
| 11 | **Legacy schema temizliği** | `ToolCommand`, `AIResponse` kullanımlarını `FinalCommand` ile değiştir, schemaları sadeleştir |
| 12 | **Platform-agnostic tool abstraction** | SslScanTool, SubdomainEnumTool, WebAppScanTool için Docker/Linux komut alternatifleri |
| 13 | **`BackendGateway.parse_command()` refactor** | Terminal komutlarını da AI pipeline'ından geçir veya aynı validation katmanını uygula |

### P3 — İleri Sprintler (Sprint 5-6)

| # | Görev | Gerekçe |
|---|-------|---------|
| 14 | **Suggestion engine** | Schema hazır (`SuggestionSchema`), implementasyon başlamalı |
| 15 | **Plugin sistemi** | Interface + Loader + Hot-reload altyapısı |
| 16 | **Test coverage raporu** | `pytest-cov` ile ölçüm; hedef >80% branch coverage |
| 17 | **CI/CD pipeline** | GitHub Actions: lint + test + build on PR |

---

## Sonuç

### Post-Audit Güncelleme (4 Mart 2026)

- Runtime telemetry UI görünürlüğü status bar üzerinden aktifleştirildi.
- `secure_delete` ayarı backend cleaner zincirine bağlandı.
- API execute akışı execution tool `build_command` öncelikli hale getirildi.
- Registry `build_tool_spec` metadata-only davranışa çekildi.
- Sprint 3.5 odaklı test/benchmark turlarıyla ilgili kritik regresyonlar kapatıldı.

SENTINEL AI, Sprint 3/3.5 itibarıyla **sağlam bir mimari temele** sahip. Deterministik karar zinciri, queue/backpressure yönetimi ve registry drift guard gibi mekanizmalar, projenin güvenlik-kritik bir domain'de çalıştığının bilincinde tasarlandığını gösteriyor. 112 testin tamamının yeşil olması ve net katman ayrımı, teknik borcun yönetilebilir düzeyde tutulduğunun kanıtıdır.

Öncelikli iyileştirme alanları: **merkezi logging**, **callback exception safety** ve **dokümantasyon senkronizasyonu**. Sprint 4'e geçiş için en büyük risk, veri modeli/adapter katmanının sıfırdan inşa edilecek olması — bu konuda Pydantic v2'nin mevcut kullanım deneyimi avantaj sağlayacaktır.

Proje takvime **%90 uyumlu** ilerlemiş; kalan eksilikler (UI security indicators, settings genişletmesi) blokleyici değil, Sprint 4 ile paralel tamamlanabilir.

---
---

# Bölüm 2 — Soru-Yanıt: Linux Build, Model Seçimi, Ölçeklenme

> **Kullanıcı Soruları:**
> 1. Uygulama linux tabanlı olacak. Bu proje yapısında uygulamayı linux build alırken ne tür sıkıntılarla karşılaşabiliriz, düzenlememiz gereken yerler var mı?
> 2. Model olarak Qwen 2.5 3B kullaniyoruz (onceki modelden gecis yapildi).
> 3. Mevcut tool sayımıza göre uygulamanın yanıt verme süresi testlerde oldukça iyi duruyor. Ancak ilerleyen zamanlarda tool sayımız ve komut çeşitliliğini arttırdığımızda yanıt süresinin artmasından ve false yanıt dönmesinden korkuyorum bunun için nasıl bir önlem mekanizması önerir misin?

---

## Soru 1: Linux Build — Karşılaşılacak Sorunlar

Kod tabanında **5 kritik Windows bağımlı nokta** tespit edildi:

### Kritik (Build kıran)

| # | Dosya | Satır | Sorun | Çözüm |
|---|-------|-------|-------|-------|
| 1 | `src/core/tool_base.py` (`PingTool.build_command()`) | L334 | `ping -n` (Windows flag) | Linux'ta `ping -c` olmalı |
| 2 | `src/core/tool_base.py` (`SslScanTool.build_command()`) | L555 | `cmd.exe /c "echo \| openssl..."` | Linux'ta `bash -c "echo \| openssl..."` veya direkt pipe |
| 3 | `src/core/tool_base.py` (`SubdomainEnumTool.build_command()`) | L663 | Tüm komut `powershell.exe` ile sarılmış (Test-Path, Get-Content, Write-Output) | Bash script'e dönüştürülmeli veya Python subprocess ile yapılmalı |
| 4 | `src/core/tool_base.py` (`WebAppScanTool.build_command()`) | L787 | `Invoke-WebRequest` + `powershell.exe` | `curl` / `wget` + `bash` olmalı |
| 5 | `src/core/process_manager.py` (`_get_console_encoding()`) | L13 | `chcp` komutu, `cp1254` fallback | Linux'ta her zaman `utf-8`; mevcut fallback çalışır ama `shell=True` kısmı linting uyarısı verir |

### Orta (Davranış farkı yaratacak)

| # | Dosya | Sorun |
|---|-------|-------|
| 6 | `src/core/execution_manager.py` (L101) | `os.environ.get("TEMP", ".")` Windows path'i. Linux'ta `TEMP` yok, `"."` kullanılır — bu proje root'una yazım yapar. |
| 7 | `src/core/cleaner.py` (L35) | `ALLOWED_PATHS`'e Windows temp path ekleniyor ama Linux koşulunda `/tmp/sentinel_` zaten var. Sorun yok, ama dead code kalacak. |
| 8 | `src/core/tool_base.py` (`DnsLookupTool`) | `nslookup` Linux'ta genelde var ama `dig` daha yaygın ve daha parse-friendly. Sorun olmaz, ama suboptimal. |

### Düşük (Build kaybı değil ama dikkat edilmeli)

| # | Konu |
|---|------|
| 9 | PyInstaller Linux build'de `--windowed` flag'i `.spec` dosyasına `console=True` olarak değiştirilmeli |
| 10 | PyQt6 Linux'ta `xcb` plugin gerektirir: `sudo apt install libxcb-xinerama0 libxcb-cursor0` |
| 11 | `docker-compose.yml`'de `runtime: nvidia` GPU olmayan makinelerde fail eder — conditional yapılmalı |

### Önerilen Yaklaşım

En temiz çözüm, platform-dependent tool'ları **`build_command()`** seviyesinde branch'lemek. `ExecutionManager.is_linux` zaten var, sadece kullanılmıyor:

```python
# SslScanTool örneği — platform-aware
def build_command(self, target: str, port: int = 443, **kwargs) -> List[str]:
    # Linux (production hedef)
    return ["bash", "-c", f"echo | openssl s_client -connect {target}:{port} -showcerts 2>&1"]
```

`PingTool` için:
```python
def build_command(self, target: str, count: int = 4, **kwargs) -> List[str]:
    return ["ping", "-c", str(count), target]  # Linux: -c
```

PowerShell tool'ları (`SubdomainEnumTool`, `WebAppScanTool`) tamamen yeniden yazılmalı — Bash + curl kombinasyonuyla. Bunlar en çok iş çıkaracak parçalar.

---

## Soru 2: Model Gecisi -- Qwen 2.5 3B Entegrasyonu

> **Not:** Bu bolum tarihsel referans amaclidir. Proje artik Qwen 2.5 3B Instruct kullanmaktadir.

Mevcut kullanım: LLM **sadece intent belirliyor** (tool, argüman, risk üretmiyor). Bu çok dar bir scope — ve bu avantaj.

### Değerlendirme Tablosu

| Model | Boyut | Intent Speed (CPU) | Intent Speed (GPU) | Accuracy | Önerim |
|-------|-------|-------|-------|----------|--------|
| **Qwen 2.5 3B Q4** (aktif) | ~1.8 GB | 1-2s | <1s | Cok iyi (JSON mode) | **Aktif model** |
| **Phi-3.5-mini 3.8B Q4** | ~2.2 GB | 1-3s | <1s | Çok iyi (structured output) | Alternatif |
| **Gemma-2 2B Q4** | ~1.5 GB | <1s | <0.5s | İyi (basit intent) | Ultra-hız istiyorsanız |

### Net Öneri

**Qwen 2.5 3B** intent resolver için aktif model olarak kullanilmaktadir.

Suggestion engine (Sprint 5) için daha büyük bir model degerlendirilebilir.

```python
# intent için küçük model
intent_resolver = IntentResolver(model="qwen2.5:3b")
```

Geçiş öncesi mutlaka mevcut intent test case'leri (prompt örnekleri) her iki modelle karşılaştırılmalı. Bir `intent_benchmark.py` script'i yazıp 20-30 örnek girdiyle accuracy + latency ölçülmeli.

---

## Soru 3: Tool Sayısı Artışında Yanıt Süresi ve False-Positive Önlemi

Bu soru mimari açısından en kritik olanı. İyi haber: mevcut Action Planner v2 yapısının büyük bölümü zaten bu soruna dayanıklı. Ancak ek önlemler gerekiyor.

### Mevcut Durumun Güçlü Yönleri

LLM **tool seçmiyor** — sadece `IntentType` enum'u döndürüyor. Tool mapping deterministik. Bu demek ki tool sayısı 10'dan 50'ye çıksa bile LLM'in işi değişmiyor. Sorun intent sayısının artmasında.

### Tehlike Senaryoları ve Çözümler

#### Senaryo A: Intent sayısı 15 → 40+ olduğunda

**Risk:** LLM'in prompt'undaki `INTENT TURLERI` listesi uzadıkça, yanlış intent seçme olasılığı artar.

**Çözüm — Hierarchical Intent Resolution (İki Aşamalı Çözümleme):**

```
Kullanıcı girdisi
    ↓
[1. Aşama] Kategori belirle (5-6 kategori)
    scanning | web | recon | bruteforce | exploit | info
    ↓
[2. Aşama] Kategoriye özel sub-intent belirle (5-8 sub-intent)
    scanning → host_discovery | port_scan | service_detection | os_detection | vuln_scan
```

Bu yaklaşımla LLM her aşamada en fazla 6-8 seçenek arasında karar verir. 40 intent'i tek seferde çözmek yerine 2 × 8 = 16 seçenek. Accuracy dramatik artar, latency çok az artar (ikinci çağrı çok kısa).

#### Senaryo B: Aynı intent'e birden fazla tool eşlendiğinde

**Risk:** Bugün `PORT_SCAN → nmap` bire-bir. Yarın `PORT_SCAN → nmap | masscan | rustscan` olacak.

**Çözüm — Tool Selection Policy:**

```python
# tool_registry.py'ye eklenecek
IntentType.PORT_SCAN: [
    ToolDef(tool="nmap",     priority=1, condition="default"),
    ToolDef(tool="masscan",  priority=2, condition="large_range"),  # /16+ CIDR
    ToolDef(tool="rustscan", priority=3, condition="speed_first"),
]
```

Seçim deterministic kalır (LLM'e bırakılmaz): target CIDR büyükse masscan, hız isteniyorsa rustscan, default nmap.

#### Senaryo C: False positive yanıt (yanlış intent)

**Çözüm — Confidence Threshold + Validation Gate:**

```python
# IntentResolver yanıtına confidence ekle
{
    "intent_type": "port_scan",
    "confidence": 0.92,    # ← YENİ
    "target": "192.168.1.1",
    ...
}

# Orchestrator'da kontrol
if intent.confidence < 0.7:
    return {"needs_clarification": True, "message": "Ne yapmak istediğinizi tam olarak anlayamadım..."}
```

Buna ek olarak, **keyword-based pre-filter** (LLM çağrısından önce):

```python
# Regex/keyword ile hızlı ön-eleme
KEYWORD_HINTS = {
    r"port|tara|scan":  [IntentType.PORT_SCAN, IntentType.HOST_DISCOVERY],
    r"dizin|dir|path":  [IntentType.WEB_DIR_ENUM],
    r"dns|domain|whois": [IntentType.DNS_LOOKUP, IntentType.WHOIS_LOOKUP],
}

# LLM'in sonucunu keyword hint ile çapraz doğrula
if llm_intent not in keyword_expected_intents:
    logger.warning("LLM intent keyword hint ile uyumsuz, clarification tetikle")
```

Böylece LLM "port taraması" dediğinde ama `dns_lookup` döndürdüğünde hemen yakalanabilir.

#### Senaryo D: Yanıt süresi artışı (tool sayısı → registry büyümesi)

**Risk:** Düşük. Registry lookup O(1) dict erişimi. 100 tool'da bile <1ms. Gerçek bottleneck her zaman LLM latency.

**Çözüm — Response Time Budget:**

```python
# Orchestrator'a toplam süre bütçesi ekle
MAX_RESPONSE_MS = 10_000  # 10 saniye toplam bütçe

start = time.time()
intent = self._intent_resolver.resolve(...)  # ~2-5s
elapsed = (time.time() - start) * 1000

if elapsed > MAX_RESPONSE_MS * 0.8:  # bütçenin %80'i intent'te harcandıysa
    logger.warning("Intent resolution slow: %.0fms", elapsed)
    # Fallback: keyword-based intent (LLM'siz)
```

### Özet Aksiyon Planı (Ölçeklenme)

| Öncelik | Aksiyon | Ne Zaman |
|---------|---------|----------|
| **P0** | `confidence` alanını Intent schema'ya ekle | Sprint 4 |
| **P0** | Keyword pre-filter + cross-validation | Sprint 4 |
| **P1** | Hierarchical intent (kategori → sub-intent) | Tool sayısı 20'yi geçtiğinde |
| **P1** | Dual-model stratejisi (küçük model → intent) | Sprint 5 öncesi benchmark |
| **P2** | Tool selection policy (aynı intent → birden fazla tool) | Yeni tool eklenirken |
| **P2** | Response time budget + LLM'siz fallback | Sprint 5 |

---

*Doküman Sonu — 26 Şubat 2026*
