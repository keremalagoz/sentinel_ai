# SENTINEL AI - Sprint Roadmap (Güncel)

**Guncelleme Tarihi:** 10 Mart 2026  
**Mimari:** Action Planner v2.1 + Backend Session-Memory Chat (Local-Only LLM + Deterministic Command Builder)

---

## 1) Proje Amacı

SENTINEL AI; doğal dilde verilen siber güvenlik taleplerini,
kontrollü ve denetlenebilir bir akışla çalıştırılabilir komutlara dönüştüren
local AI destekli güvenlik test platformudur.

Temel akış:

`User Input -> Intent Resolver -> Tool Registry -> Command Builder -> Execution Layer`

7 Mart 2026 stabilizasyon notları:

- Tamamlanan Yiğit hotfix özeti: `docs/yigit_stabilization_hotfix.md`
- Ortak/Kerem handoff konuları: `docs/kerem_handoff_issues.md`

---

## 2) Mevcut Mimari (Kaynak Gerçeklik)

- **UI:** PyQt6
- **AI Katmanı:** `src/ai/`
  - `intent_resolver.py`
  - `tool_registry.py`
  - `command_builder.py`
  - `orchestrator.py`
- **Core Katman:** `src/core/`
  - `process_manager.py`
  - `execution_manager.py`
  - `tool_base.py`
  - `tool_integration.py`
  - `sentinel_coordinator.py`
  - `sqlite_backend.py`
  - `parser_framework.py`
- **Docker Servisleri:**
  - `ollama-service` (8002 → 11434)
  - `api-service` (8000)
  - `tools-service`

---

## 3) Tüm Sprintler ve Görev Durumları

### Sprint 0 — Altyapı ✅

| # | Görev | Sorumlu | Durum |
|---|-------|---------|-------|
| 0.1 | Proje klasör yapısı | Kerem | ✅ |
| 0.2 | Docker compose altyapısı | Kerem | ✅ |
| 0.3 | Python bağımlılık standardizasyonu | Kerem | ✅ |

---

### Sprint 1 — Süreç Motoru + State ✅

| # | Görev | Sorumlu | Durum |
|---|-------|---------|-------|
| 1.1 | QProcess tabanlı çalıştırma | Kerem | ✅ |
| 1.2 | SQLite backend + execution history | Kerem | ✅ |
| 1.3 | Parser framework + entity id stratejisi | Kerem | ✅ |
| 1.4 | Tool integration zinciri | Kerem | ✅ |

---

### Sprint 2 — AI Karar Katmanı ✅

| # | Görev | Sorumlu | Durum |
|---|-------|---------|-------|
| 2.1 | Intent tabanlı akış | Kerem | ✅ |
| 2.2 | Deterministik tool mapping | Kerem | ✅ |
| 2.3 | Deterministik command build | Kerem | ✅ |
| 2.4 | API tarafında deterministik command preparation | Kerem | ✅ |

---

### Sprint 3 — Güvenlik ve Temizlik (6/6)

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.1 | ExecutionManager | Yiğit | ✅ | Docker/Native mod yönetimi & Pkexec logic |
| 3.2 | Secure Cleaner (`cleaner.py`) | Yiğit | ✅ | Güvenli dosya temizleme, Whitelist, Shredding |
| 3.3 | Input Validation | Yiğit | ✅ | IP/Domain validasyonu, Shell injection check |
| 3.4 | ProcessManager Update | Yiğit | ✅ | Yeni core modüllerle entegrasyon |
| 3.5 | UI Security Indicators | Yiğit | ✅ | Terminalde risk/root uyarısı |
| 3.6 | Settings Menu (Security) | Yiğit | ✅ | Temizlik sıklığı, güvenlik politikası vb. |

---

### Sprint 3.1 — Stabilizasyon ve Sertleştirme ✅

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|-----------|
| 3.1.1 | Queue backpressure | Kerem | ✅ | ToolManager kuyruk taşmasını kontrollü reddetme |
| 3.1.2 | Global concurrency limiti | Kerem | ✅ | Eşzamanlı çalışma üst sınırı |
| 3.1.3 | Per-tool concurrency limiti | Kerem | ✅ | Tool bazlı paralellik kontrolü |
| 3.1.4 | Local LLM timeout/retry/backoff | Kerem | ✅ | intent_resolver timeout + retry + backoff |
| 3.1.5 | Registry drift guard | Kerem | ✅ | Startup doğrulama + test guard |
| 3.1.6 | Adaptif timeout tahmini | Kerem | ✅ | Tool bazlı tahmini timeout stratejisi |
| 3.1.7 | Runtime telemetry yüzeyi | Kerem | ✅ | queue_wait_ms / tool_run_ms metrikleri |

---

### Sprint 3.2 — Optimizasyon ve Platform Hazırlığı ✅

> Detaylı plan: [sprint_3_2_plan.md](sprint_3_2_plan.md)  
> Merge: develop'a merge edildi (commit `02e352c`)

**Track A — Kritik Bugfix (4/4) ✅**

| # | Görev | Sorumlu | Durum | Commit |
|---|-------|---------|-------|--------|
| A1 | Merkezi Logging Konfigürasyonu | Kerem | ✅ | `f7ace9f` |
| A2 | ToolManager Callback Exception Safety | Kerem | ✅ | `fe79566` |
| A3 | BackendGateway Güvenlik Düzeltmesi | Kerem | ✅ | `89bfed9` |
| A4 | Dokümantasyon Senkronizasyonu | Kerem | ✅ | `51e128f` |

**Track B — Linux Platform Uyumluluğu (7/7) ✅**

| # | Görev | Sorumlu | Durum | Commit |
|---|-------|---------|-------|--------|
| B1 | PingTool Linux Uyumu | Kerem | ✅ | `e3e6a79` |
| B2 | SslScanTool Linux Uyumu | Kerem | ✅ | `e3e6a79` |
| B3 | SubdomainEnumTool Yeniden Yazım | Kerem | ✅ | `e3e6a79` |
| B4 | WebAppScanTool Yeniden Yazım | Kerem | ✅ | `e3e6a79` |
| B5 | ProcessManager Encoding Temizliği | Kerem | ✅ | `e3e6a79` |
| B6 | ExecutionManager Temp Path | Kerem | ✅ | `e3e6a79` |
| B7 | Platform Utility Modülü (`platform_utils.py`) | Kerem | ✅ | `e3e6a79` |

**Track C — AI Ölçeklenme Altyapısı (7/7) ✅**

| # | Görev | Sorumlu | Durum | Commit |
|---|-------|---------|-------|--------|
| C1 | Intent Confidence Skoru | Kerem | ✅ | `842a44e` |
| C2 | Keyword Pre-filter (`keyword_filter.py`) | Kerem | ✅ | `842a44e` |
| C3 | Response Time Budget | Kerem | ✅ | `842a44e` |
| C4 | Intent Benchmark Script (`intent_benchmark.py`) | Kerem | ✅ | `842a44e` |
| C5 | Dual-Model Strateji Altyapısı | Kerem | ✅ | `842a44e` |
| C6 | Hierarchical Intent Tasarım Dokümanı (forward-ref) | Kerem | ✅ | `842a44e` |
| C7 | Tool Selection Policy — priority/condition (forward-ref) | Kerem | ✅ | `842a44e` |

**Track D — Kod Kalitesi / Teknik Borç (4/4) ✅**

| # | Görev | Sorumlu | Durum | Commit |
|---|-------|---------|-------|--------|
| D1 | tool_base.py Dosya Bölme → `src/core/tools/` | Yiğit | ✅ | `2c6794a` |
| D2 | SQLite WAL Mode | Kerem | ✅ | `2c6794a` |
| D3 | Legacy Schema Temizliği → `schemas_legacy.py` | Kerem | ✅ | `2c6794a` |
| D4 | Singleton Thread Safety (Lock guard) | Kerem | ✅ | `2c6794a` |

**Sprint 3.2 Toplam: 22/22 görev ✅**

---

### Sprint 3.3 — Hybrid LLM Motoru ve 2 Aşamalı Intent Resolution ✅

> Tasarım dokümanı: [hierarchical_intent_design.md](hierarchical_intent_design.md)  
> Temel: Sprint 3.2 Track C altyapısı (confidence, keyword filter, dual-model, benchmark)  
> Hedef: Flat 17-intent → Hierarchical 5-category + sub-intent geçişi

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.3.1 | CategoryResult + SENTINEL_CATEGORIES modeli | Kerem | ✅ | Pydantic model, 5 kategori taksonomisi dict |
| 3.3.2 | HierarchicalResolver base class | Kerem | ✅ | ABC: `resolve_category()`, `resolve_sub_intent()`, `resolve()` |
| 3.3.3 | Stage 1 — Category Resolver | Kerem | ✅ | 5 kategorili prompt, hafif model çağrısı (~1-2s) |
| 3.3.4 | Stage 2 — Sub-Intent Resolver | Kerem | ✅ | Kategori bazlı daraltılmış prompt, ana model çağrısı |
| 3.3.5 | KeywordPreFilter bypass entegrasyonu | Kerem | ✅ | Yüksek confidence keyword → Stage 1 atla, direkt Stage 2 |
| 3.3.6 | Orchestrator feature flag | Kerem | ✅ | `USE_HIERARCHICAL = True/False`, flat/hierarchical geçiş |
| 3.3.7 | Flat vs Hierarchical benchmark | Kerem | ✅ | `intent_benchmark.py` genişlet, accuracy/latency karşılaştırma |
| 3.3.8 | Unit testler | Kerem | ✅ | HierarchicalResolver, category routing, fallback senaryoları (57 test) |
| 3.3.9 | Model değişimi: WhiteRabbitNeo 7B → Qwen 2.5 3B | Kerem | ✅ | %50 daha az VRAM, %59 daha az disk, %100 benchmark |
| 3.3.10 | Docker/doküman güncellemesi | Kerem | ✅ | ollama-service, Qwen 2.5 3B default, README/PROJECT_STRUCTURE güncel |

**Sprint 3.3 Toplam: 10/10 görev ✅**

---

### Sprint 3.4 — UI / i18n / Performans Optimizasyonu ✅

> Sorumlu: Yiğit  
> Tarih: 1–4 Mart 2026  
> Kapsam: UI hata düzeltme, çok dil desteği, ayarlar diyalogu, performans optimizasyonu, kapsamlı test

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.4.1 | Sprint 3 font hataları (5 bug) | Yiğit | ✅ | Chat/terminal font tutarlılığı, bold, miras |
| 3.4.2 | Layout Swap (Chat/Terminal pozisyon) | Yiğit | ✅ | Yatay/dikey düzen değiştirme |
| 3.4.3 | i18n sistemi (11 dil, 78 anahtar) | Yiğit | ✅ | `src/ui/i18n.py` — EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI |
| 3.4.4 | Ayarlar Diyalogu | Yiğit | ✅ | `settings_dialog.py` — dil, font boyutu, oturum temizleme |
| 3.4.5 | Orchestrator i18n entegrasyonu | Yiğit | ✅ | "Komut hazır" çevirisi + badge fallback |
| 3.4.6 | UI test altyapısı (conftest + 3 dosya) | Yiğit | ✅ | 500 yeni test (i18n, widget, özellik) |
| 3.4.7 | Performans audit (12 sorun tespiti) | Yiğit | ✅ | 5 HIGH + 7 MEDIUM optimizasyon fırsatı |
| 3.4.8 | 12 optimizasyon fix uygulaması | Yiğit | ✅ | Debounce, cache, pre-compile, QSS sabitleri |
| 3.4.9 | Optimizasyon testleri (91 test) | Yiğit | ✅ | 13 sınıf, timing + anti-pattern taraması |

**Sprint 3.4 Toplam: 9/9 görev ✅**

---

### Sprint 3.5 — Tool Komut Doğruluğu ve Güvenlik Sertleştirme ✅

> Detaylı plan: [sprint_3_5_plan.md](sprint_3_5_plan.md)

| # | Görev Başlığı | Sorumlu | Durum | Açıklama |
|---|---------------|---------|-------|----------|
| 3.5.1 | Komut güvenliği sertleştirme | Yiğit | ✅ | Kritik tool komut yollarında shell interpolation kaldırıldı |
| 3.5.2 | Tool komut doğruluğu normalizasyonu | Yiğit | ✅ | Nmap/web/recon/attack komut üretimleri güncellendi |
| 3.5.3 | Yeni execution tool'ları | Yiğit | ✅ | OS detection, whois, hydra ssh/http, sqlmap eklendi |
| 3.5.4 | Registry/execution tek kaynak hizalaması | Yiğit | ✅ | Registry metadata-only, yürütme execution tool `build_command` üzerinden |
| 3.5.5 | Secure delete uçtan uca bağlama | Yiğit | ✅ | Settings → BackendGateway → Cleaner akışı tamamlandı |
| 3.5.6 | Runtime telemetry UI yüzeyi | Yiğit | ✅ | Status bar metrik gösterimi aktif edildi |
| 3.5.7 | Test ve benchmark doğrulaması | Yiğit | ✅ | Sprint 3.5 odaklı test setleri ve hierarchical benchmark tekrar koşuldu |

**Sprint 3.5 Toplam: 7/7 görev ✅**

---

### Sprint 3.5 v2 — Dev_Kerem Tabanlı UI + Tool Konsolidasyonu ✅

> Kapsam: `dev_kerem` AI/planner mimarisi korunacak; develop tarafındaki UI değişiklikleri alınacak; tool katmanı seçici ve planner uyumlu şekilde genişletilecek  
> Branch stratejisi: `develop` mevcut haliyle `experimental` branch'inde korunur, gerçek geliştirme doğrudan `dev_kerem` üzerinde yürütülür  
> Hedef: İş bittiğinde `dev_kerem` → `develop` merge

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.5v2.1 | Experimental güvenlik dalı | Kerem | ✅ | `develop` mimarisi `experimental` branch'inde donduruldu |
| 3.5v2.2 | İlk güvenlik/telemetry dilimi | Kerem | ✅ | `BackendGateway`, `SecureCleaner`, `MainWindow`, `SecuritySettingsDialog`, `i18n` üzerinde secure-delete + confirmation policy + telemetry yüzeyi eklendi |
| 3.5v2.3 | Terminal risk yüzeyi | Yiğit + Kerem | ✅ | `terminal_view.py` içinde renkli risk bannerları, oturum risk state'i ve risk bazlı terminal görünürlüğü alındı |
| 3.5v2.4 | UI parity göçüsü | Yiğit + Kerem | ✅ | `main_window.py`, `chat_interface.py`, `settings_dialog.py`, `i18n.py` üzerinde parity akışı tamamlandı; session göstergesi, telemetry yüzeyi, chat history -> backend session senkronizasyonu ve clear-all sonrası session reset akışı alındı |
| 3.5v2.5 | Faz 1 tool göçüsü | Kerem | ✅ | `whois_lookup`, `nmap_os_detection` execution katmanına eklendi; parser/coordinator/allowlist ve güvenli `build_command()` uyarlamaları tamamlandı |
| 3.5v2.6 | Planner-friendly registry uyarlaması | Kerem | ✅ | `tool_registry.py` planner kontratını koruyarak yeni tool parametre şablonlarını (`record_type`, `ports`, `aggressive`) ve execution mapping'lerini tamamladı |
| 3.5v2.7 | Faz 2 tool politikası | Kerem | ✅ | `hydra_http`, `hydra_ssh`, `sqlmap_scan` için deterministic explicit clarification politikası tanımlandı; eksik zorunlu parametrede komut hazırlamak yerine netleştirme istenir |
| 3.5v2.8 | Regresyon ve merge hazırlığı | Kerem | ✅ | Planner regresyonları, UI smoke, tool onboarding ve roadmap senkronizasyonu tamamlandı; hedefli doğrulama seti yeşil |

**Sprint 3.5 v2 Toplam: 8/8 görev ✅**

**Sprint 3.5 v2 Kılavuz Kararları**

- AI/planner çekirdeği `dev_kerem` çizgisinde kalır; develop'in execution-first mimarisi ana akış yapılmaz.
- UI tarafında develop değişikliklerinin tamamı hedeflenir.
- Tool katmanı iki fazlı alınır: düşük riskli/recon tool'lar önce, zengin parametre isteyen tool'lar sonra.
- Sprint 3 backlog maddeleri BL-1, BL-2 ve BL-3 bu sprint kapsamına alınmıştır; ayrı backlog takibi yapılmayacaktır.

---

### Sprint 3.6 — Backend Agent-Chat Foundation (UI Değişikliği Yok) ✅

> Detaylı plan: [sprint_3_6_plan.md](sprint_3_6_plan.md)  
> Kapsam: Sadece backend güncellemeleri (UI tasarımına dokunulmadı)

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.6.1 | Conversation memory store | Kerem | ✅ | `conversation_sessions` + `conversation_turns` kalıcı hafıza tabanı |
| 3.6.2 | Orchestrator multi-turn context | Kerem | ✅ | `process_v2` session-aware hale getirildi, son turlar bağlama eklendi |
| 3.6.3 | Yarı-otomatik agent çıktısı | Kerem | ✅ | `requires_approval` + `agent_observation` alanları eklendi |
| 3.6.4 | REST chat endpointleri | Kerem | ✅ | `/api/chat/session`, `/api/chat/turn`, `/api/chat/history/{session_id}` |
| 3.6.5 | Gateway session API | Kerem | ✅ | `ask_ai_with_session()` eklendi (mevcut `ask_ai` korunarak) |
| 3.6.6 | Backend test kapsamı | Kerem | ✅ | Yeni testler + boundary regresyonu (`2 + 19` test yeşil) |

**Sprint 3.6 Toplam: 6/6 görev ✅**

---

### 7 Mart 2026 — Yiğit Stabilization Hotfix ✅

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| YS-1 | Backend session ownership | Yiğit | ✅ | `main_window.py` + `chat_interface.py` aynı backend `session_id` ile hizalandı |
| YS-2 | Structured AI command execution | Yiğit | ✅ | AI komutları reparsing olmadan structured payload olarak çalıştırılıyor |
| YS-3 | Typed validation ayrımı | Yiğit | ✅ | URL/query/form payload argümanları structured path'te kabul ediliyor |
| YS-4 | Failed-start lifecycle fix | Yiğit | ✅ | `BaseTool` tek terminal sonuç üretir, timeout yarışını tekrar etmez |
| YS-5 | Windows native execution | Yiğit | ✅ | Merkezi executable resolution + subprocess fallback aktif |
| YS-6 | Kerem handoff | Yiğit | ✅ | Ortak AI/registry drift ve canlı LLM exact-match oynaklığı ayrı raporlandı |

---

## 3.1) Hızlı Durum Özeti

- Mimari: Local-only LLM + deterministic execution + backend session-memory chat
- Test sağlığı: baseline full suite yeşil (**76 passed**) + önceki sprint testleri korunuyor
- Tamamlanan: Sprint 0 → 3.6 + Sprint 3.5 v2
- **Aktif sprint: Sprint 4 — Veri Adaptasyonu ve Sonuç Modelleri** (beklemede)
- Son benchmark (Sprint 3.7.1): Intent %95.0, Params %96.0, Target %86.0, Exact Match %76.0
- Backlog: Sprint 3 UI backlog'u Sprint 3.5 v2 içinde kapatıldı
- Sonraki hedef: Sprint 3.7 → Sprint 4 (Veri Adaptasyonu)

### Sprint 3.7 — AI Doğruluk Acil Düzeltmeleri (Audit Bulguları) ✅

> Tetikleyen: 9 Mart 2026 Kapsamlı Audit Raporu + 200 vakalık bilingual benchmark sonuçları  
> Detaylı plan: [sprint_3_7_plan.md](sprint_3_7_plan.md)  
> Kapsam: Benchmark'ta tespit edilen params (%33), target (%74.5) ve exact match (%23.5) darboğazlarının giderilmesi  
> Hedef: Intent accuracy ≥%90, params_accuracy ≥%55, target_accuracy ≥%80, exact_match ≥%40

**Track A — Parametre Çıkarma İyileştirmesi (P0)**

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| A1 | Stage 2 prompt param örneklerini zenginleştir | — | ✅ | Few-shot param ornekleri eklendi, format kirigi giderildi |
| A2 | Regex tabanlı ParamExtractor modülü | — | ✅ | `src/ai/param_extractor.py` eklendi |
| A3 | Orchestrator param merge mantığı | — | ✅ | Param merge + implicit param prune iyilestirmeleri uygulandi |
| A4 | vuln_scan / ssl_scan / sql_injection param testleri | — | ✅ | `src/tests/test_sprint37_extraction.py` ile hedefli kapsam eklendi |

**Track B — Target Çıkarma İyileştirmesi (P0)**

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| B1 | Target pre-extraction regex | — | ✅ | URL/IP/domain pre-extraction ParamExtractor'a alindi |
| B2 | Target hint → LLM prompt enjeksiyonu | — | ✅ | Stage-2 context satiri netlestirildi |
| B3 | Target fallback zinciri | — | ✅ | `LLM -> regex -> UI hint -> null` zinciri uygulandi |

**Track C — Intent Sınır Netleştirme (P1)**

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| C1 | info_query keyword filter güçlendirme | — | ✅ | TR/EN info_query pattern seti genisletildi |
| C2 | web_dir_enum vs web_vuln_scan sınır tanımı | — | ✅ | Keyword + Stage-2 ayrim kurallari eklendi |
| C3 | Orchestrator hard-override'ları kural motoruna taşı | — | ✅ | Minimal configurable override yapisi eklendi |
| C4 | unknown intent routing | — | ✅ | unknown siniri ve prompt kurallari netlestirildi |

**Track D — Altyapı ve JSON Güvenilirlik (P1)**

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| D1 | Hierarchical resolver JSON mode | — | ✅ | `response_format={"type": "json_object"}` eklendi |
| D2 | Modelfile system prompt zenginleştirme | — | ✅ | Intent türleri listesi, param talimatı, multi-param örnek eklendi |
| D3 | LLM flaky test izolasyonu | — | ✅ | `pytest.ini` marker + `conftest.py` opt-in (`--run-llm`/`RUN_LLM_TESTS`) + LLM smoke test ayrimi tamamlandi |
| D4 | Benchmark regression gate | — | ✅ | `scripts/benchmark_gate.py` + `.github/workflows/ci.yml` benchmark-gate job'i ile CI entegrasyonu tamamlandi (repo variable ile kontrollu aktivasyon) |

**Sprint 3.7 Toplam: 15/15 görev ✅**

---

### Sprint 3.7.1 — Benchmark Accuracy Hardening ✅

> Tetikleyen: Sprint 3.7 sonrasi benchmark skorlarinin Sprint 4 hazirligi icin yeterli olmamasi
> Detayli rapor: [sprint_371_report.md](sprint_371_report.md)
> Kapsam: Benchmark pipeline'inin production (process_v2) ile senkronizasyonu, regex false positive duzeltmeleri, keyword pattern genisletmeleri
> Hedef: Intent >=90%, Params >=55%, Target >=80%, Exact >=40%

| # | Gorev | Sorumlu | Durum | Aciklama |
|---|-------|---------|-------|----------|
| 3.7.1.1 | Benchmark post-processing | Kerem | ✅ | Strict-regex param pruning, regex target resolution, keyword fallback, INFO_QUERY override eklendi |
| 3.7.1.2 | ParamExtractor regex duzeltmeleri | Kerem | ✅ | service_detection self-ref, _SCRIPTS_RE sikilation, username false positive, DNS A record context |
| 3.7.1.3 | KeywordFilter pattern genisletme | Kerem | ✅ | grab+banner, credential attack, what does X check, web application security |
| 3.7.1.4 | Test ve benchmark dogrulama | Kerem | ✅ | 98 test gecti, 3 benchmark run, tum hedefler asildi |

**Sprint 3.7.1 Toplam: 4/4 gorev ✅**

**Final Benchmark Sonuclari (10 Mart 2026):**

| Metrik | Baseline | Hedef | Final | Iyilestirme |
|--------|----------|-------|-------|-------------|
| Intent | %87.0 | >=90% | **%95.0** | +8pp |
| Params | %52.5 | >=55% | **%96.0** | +43.5pp |
| Target | %78.5 | >=80% | **%86.0** | +7.5pp |
| Exact  | %37.0 | >=40% | **%76.0** | +39pp |

---

## 4) Bekleyen Sprintler

### Sprint 4 — Veri Adaptasyonu ve Sonuç Modelleri

> Detaylı plan: [sprint_4_plan.md](sprint_4_plan.md)

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 4.1 | Pydantic Veri Modeli (`models.py`) | Kerem | ⬜ | ScanResult, Host, Port, Service modelleri |
| 4.2 | XML Repair fonksiyonu | Kerem | ⬜ | Kesik XML çıktılarını düzeltme |
| 4.3 | Nmap Adapter (`nmap_adapter.py`) | Kerem | ⬜ | XML → Pydantic dönüşümü |
| 4.4 | UI Tablo Gösterimi (`results_view.py`) | Yiğit | ⬜ | Parse edilmiş sonuçları tablo olarak göster |
| 4.5 | Adapter Entegrasyonu | Kerem | ⬜ | ToolManager → Adapter → UI pipeline |
| 4.6 | Unit Testler | Kerem | ⬜ | Model/XML/adapter testleri |

### Sprint 5 — Öneri Motoru

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 5.1 | Maskeleme Servisi (`masking.py`) | Kerem | ⬜ | Opsiyonel cloud mode için IP/hostname maskeleme |
| 5.2 | Öneri Şeması | Kerem | ✅ | `schemas.py`'da SuggestionSchema mevcut |
| 5.3 | Öneri Üretici (`suggestion_engine.py`) | Kerem | ⬜ | Bulgulara göre sonraki adım önerileri |
| 5.4 | UI Öneri Paneli | Yiğit | ⬜ | Önerileri kartlar halinde göster |

### Sprint 6 — Plugin Sistemi ve Final Build

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 6.1 | Plugin Structure | Yiğit | ⬜ | Interface ve Manager |
| 6.2 | Linux Build | Kerem | ⬜ | PyInstaller |

### Backlog (Tarihsel Kayıtlar)

| # | Görev | Sorumlu | Durum | Kaynak |
|---|-------|---------|-------|--------|
| BL-1 | UI Security Indicators | Yiğit | Sprint 3.5 v2 ile tamamlandı | `3.5v2.3 / 3.5v2.4` |
| BL-2 | Settings Menu (Security) | Yiğit | Sprint 3.5 v2 ile tamamlandı | `3.5v2.2 / 3.5v2.4` |
| BL-3 | Runtime Telemetry UI görünürlüğü | Yiğit | Sprint 3.5 v2 ile tamamlandı | `3.5v2.2 / 3.5v2.3` |

---

## 6) Definition of Done (DoD)

Bir sprint maddesi tamamlandı sayılması için:

1. İlgili testler geçmeli.
2. Kod + dokümantasyon birlikte güncellenmeli.
3. Deterministik akış bozulmamalı.
4. Güvenlik kontrolleri bypass edilmemeli.
5. UI donmadan işlem tamamlanmalı.

---

## 7) Notlar

- Bu doküman mevcut kod tabanı ile uyumlu tutulur.
- Mevcut çalışma modu local-only LLM'dir; cloud mode sadece gelecekteki opsiyonel genişlemedir.
- Arşiv/eskimiş planlar `temp` altında tutulmaz; temiz çalışma ağacı hedeflenir.

---

## 8) Sayısal Özet

| Metrik | Değer |
|--------|-------|
| Tamamlanan gorev | **99** (95 onceki + 4 Sprint 3.7.1) |
| Aktif | Sprint 4 (beklemede) |
| Backlog (yerlestirilmemis) | **0** |
| Bekleyen (Sprint 4-6) | **11** |
| Toplam test | **98 passed** (baseline) |
| Son benchmark | 10 Mart 2026 — 200 vaka bilingual (Intent %95.0, Params %96.0, Target %86.0, Exact %76.0) |
| Son merge | develop `02e352c` |
| Son commit (dev_kerem) | `e7b70e6` Sprint 3.7.1 |


