# SENTINEL AI - Sprint Roadmap (Güncel)

**Güncelleme Tarihi:** 4 Mart 2026  
**Mimari:** Action Planner v2.1 + Backend Session-Memory Chat (Local-Only LLM + Deterministic Command Builder)

---

## 1) Proje Amacı

SENTINEL AI; doğal dilde verilen siber güvenlik taleplerini,
kontrollü ve denetlenebilir bir akışla çalıştırılabilir komutlara dönüştüren
local AI destekli güvenlik test platformudur.

Temel akış:

`User Input -> Intent Resolver -> Tool Registry -> Command Builder -> Execution Layer`

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

### Sprint 3 — Güvenlik ve Temizlik (4/6 — 2 görev backlog'da)

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.1 | ExecutionManager | Yiğit | ✅ | Docker/Native mod yönetimi & Pkexec logic |
| 3.2 | Secure Cleaner (`cleaner.py`) | Yiğit | ✅ | Güvenli dosya temizleme, Whitelist, Shredding |
| 3.3 | Input Validation | Yiğit | ✅ | IP/Domain validasyonu, Shell injection check |
| 3.4 | ProcessManager Update | Yiğit | ✅ | Yeni core modüllerle entegrasyon |
| 3.5 | UI Security Indicators | Yiğit | ⬜ BACKLOG | Terminalde root uyarısı |
| 3.6 | Settings Menu (Security) | Yiğit | ⬜ BACKLOG | Temizlik sıklığı vb. |

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

## 3.1) Hızlı Durum Özeti

- Mimari: Local-only LLM + deterministic execution + backend session-memory chat
- Test sağlığı: en son bilinen full suite **242 passed**, Sprint 3.6 hedefli doğrulama **21 passed**
- Tamamlanan: Sprint 0 → 3.6 (toplam **61 görev** tamamlandı)
- Aktif sprint: **Sprint 3.6 tamamlandı** — sonraki: Sprint 4
- Backlog: 2 görev (Sprint 3'ten kalan UI görevleri — Yiğit)
- Sonraki hedef: Sprint 3.6 → Sprint 4 (Veri Adaptasyonu)

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

### Backlog (Yerleştirilmemiş)

| # | Görev | Sorumlu | Durum | Kaynak |
|---|-------|---------|-------|--------|
| BL-1 | UI Security Indicators | Yiğit | ⬜ | Sprint 3'ten kalan |
| BL-2 | Settings Menu (Security) | Yiğit | ⬜ | Sprint 3'ten kalan |
| BL-3 | Runtime Telemetry UI görünürlüğü | Yiğit | ⬜ | Telemetry verisi mevcut, UI'da gösterim eksik |

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
| Tamamlanan görev | **61** |
| Aktif (Sprint 3.6) | **6** |
| Backlog (yerleştirilmemiş) | **3** |
| Bekleyen (Sprint 4-6) | **9** |
| Toplam test | **242 passed (en son full) + Sprint 3.6 hedefli 21 passed** |
| Son merge | develop `02e352c` |


