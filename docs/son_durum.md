# SENTINEL AI - Proje Durum Raporu

**Tarih:** 7 Mart 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0-2 [OK]

- Proje altyapısı, Docker servisleri ve temel UI/Core iskeleti tamamlandı.
- Action Planner v2.1 deterministic akışı devreye alındı.
- Local AI (Qwen 2.5 3B / Ollama) ile intent çözümleme stabilize edildi.

---

## Mevcut Durum (Özet)

- Mimari: Local-only LLM (Qwen 2.5 3B / Ollama) + deterministic tool execution
- Model: Qwen 2.5 3B Instruct Q4_K_M (1.84 GB, 29+ dil, 151K vocab)
- Intent Pipeline: Keyword Pre-Filter → Stage 1 (5 kategori) → Stage 2 (16 intent) + Hard-Override Mekanizmaları
- Benchmark: deterministic regression paketi yeşil; tam yerel koşuda 1578/1579 test geçti
- Kararlılık: Queue/backpressure, per-tool limit, retry/backoff aktif
- Güvenilirlik: Registry drift guard (startup + test) aktif
- Gözlemlenebilirlik: Runtime telemetry (`queue_wait_ms`, `tool_run_ms`) mevcut
- Gözlemlenebilirlik: Runtime telemetry status bar yüzeyi aktif (`Q`, `Wait`, `Run`)
- **i18n**: 11 dil desteği (EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI) — 97 çeviri anahtarı
- **Ayarlar Diyalogu**: Dil seçimi, font boyutu, oturum temizleme
- **Güvenli Temizlik**: `secure_delete` ayarı backend cleaner akışına bağlı
- **Komut Kaynağı**: API execute akışında execution tool `build_command` öncelikli
- **AI Execution Flow**: Structured AI command payload ile raw terminal command gate ayrıldı
- **Session Ownership**: Backend `session_id` artık UI history id'den ayrışmış durumda
- **Validation**: Typed validation ile query string, form payload ve percent-encoded değerler destekleniyor
- **Windows Native**: Merkezi executable resolution + subprocess fallback aktif
- **Registry Stratejisi**: `build_tool_spec()` metadata-only (arguments boş)
- **Performans**: 12 optimizasyon uygulandı (debounce, cache, pre-compile, QSS sabitleri)
- **Test**: Full local run **1578 passed, 1 failed**; kalan tek kırık canlı LLM exact-match testi

---

## 7 Mart 2026 Yiğit Stabilization Hotfix [OK]

- `MainWindow` ve `ChatInterface` backend-owned session modeline geçirildi; history restore/new chat akışında aynı backend session sürdürülebiliyor.
- AI komutları structured payload olarak çalıştırılıyor; raw terminal komutları mevcut güvenlik kapısında kaldı.
- `validators.py` typed validation ile `sqlmap`, HTTP query string ve form payload argümanlarını kabul edecek şekilde ayrıştırıldı.
- `BaseTool`, `ExecutionManager` ve `AdvancedProcessManager` tarafında Windows native executable resolution + subprocess fallback eklendi.
- Failed-to-start yarış durumu kapatıldı; başlatılamayan process ikinci kez timeout sonucuna düşmüyor.
- Kerem'e owner handoff: canlı LLM exact-match testi oynaklığı ve ortak AI/registry semantik drift alanları.

---

## Docker Servisleri (Beklenen)

| Container | Port | İçerik |
|-----------|------|--------|
| sentinel-ollama | 11434 | Qwen 2.5 3B AI (Ollama) |
| sentinel-api | 8000 | API Backend |
| sentinel-tools | - | Nmap, Gobuster, Nikto, Hydra |

---

## Tamamlanan Sprint: Sprint 3.2 (Optimizasyon ve Platform Hazırlığı) [OK]

> Sprint 3.1 tamamlandı. Kapsamlı audit raporu sonuçlarına göre Sprint 3.2 açıldı ve tamamlandı.  
> Detaylı plan: `docs/sprint_3_2_plan.md`  
> Merge: develop'a merge edildi (commit 02e352c)

### Sprint 3.2 Özet Hedefler

| Track | Odak | Görev Sayısı | Sorumlu | Durum |
|-------|------|--------------|---------|-------|
| **A** | Kritik Bugfix (P0) | 4/4 | Kerem + Yiğit | [OK] |
| **B** | Linux Platform Uyumu | 7/7 | Yiğit + Kerem | [OK] |
| **C** | AI Ölçeklenme Altyapısı | 7/7 | Kerem | [OK] |
| **D** | Kod Kalitesi / Teknik Borç | 4/4 | Kerem + Yiğit | [OK] |

---

## Tamamlanan Sprint: Sprint 3.1 (Stabilizasyon / Sertleştirme)

### Sprint 3: Güvenlik, Yetki ve Temizlik

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| ExecutionManager | Yiğit | [OK] | Docker/Native mod yönetimi & Pkexec logic |
| Secure Cleaner (cleaner.py) | Yiğit | [OK] | Güvenli dosya temizleme, Whitelist, Shredding |
| Input Validation | Yiğit | [OK] | IP/Domain validasyonu, Shell injection check |
| ProcessManager Update | Yiğit | [OK] | Yeni core modüllerle entegrasyon |
| UI Security Indicators | Yiğit | [OK] | Terminal risk bannerı (BL-1) — Sprint 3.5 hotfix |
| Settings Menu (Security) | Yiğit | [OK] | Güvenlik Politikası paneli (BL-2) — Sprint 3.5 hotfix |

---

### Sprint 3.1: Performans ve Güvenilirlik Sertleştirme

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| Queue backpressure | Kerem | [OK] | ToolManager kuyruk taşmasını kontrollü reddetme |
| Global concurrency limiti | Kerem | [OK] | Eşzamanlı çalışma üst sınırı |
| Per-tool concurrency limiti | Kerem | [OK] | Tool bazlı paralellik kontrolü |
| Local LLM timeout/retry | Kerem | [OK] | intent_resolver timeout + retry + backoff |
| Registry drift guard | Kerem | [OK] | Startup doğrulama + test guard |
| Adaptif timeout tahmini | Kerem | [OK] | Tool bazlı tahmini timeout stratejisi |
| Runtime telemetry yüzeyi | Kerem | [OK] | queue_wait_ms/tool_run_ms metrikleri |

### Test Durumu (Güncel)

- Full test suite local run (7 Mart 2026): **1578 passed, 1 failed**
- Kalan tek kırık: `src/tests/test_action_planner_v2.py::test_intent_resolver` (canlı LLM exact-match oynaklığı)
- Yiğit stabilization regresyon paketi: **311 passed**
- Komut üretim doğruluk benchmarkı: 76 test (%100 oran)
- Intent/Prompt Coverage: 50+ senaryo, DNS/Nmap/Gobuster JSON Esnetmeleri ve Subdomain Enum
- Backend/AI testleri: ~124 test
- P0 doğrulama: `scripts/p0_validation.py --with-pytest` başarılı

| Test Dosyası | Test Sayısı | Kapsam |
|---|---|---|
| test_i18n.py | 156 | 11 dil çeviri doğruluğu |
| test_ui_widgets.py | 144 | Widget oluşturma ve davranış |
| test_ui_features.py | 245 | UI özellikleri (settings, swap, history) |
| test_optimizations.py | 91 | Performans ve anti-pattern taraması |
| test_sprint35_audit.py | 296 | Sprint 3.5 E2E audit testleri |
| test_tool_commands.py | 112 | Tool komut üretim testleri |
| test_pipeline_integration.py | 79 | Pipeline entegrasyon testleri |
| test_command_accuracy.py | 76 | Komut üretim doğruluk benchmarkı |
| Diğer (backend, AI, parser) | 262 | Backend, resolver, entegrasyon |

---

## Bekleyen Sprintler

### Sprint 4: Veri Adaptasyonu ve Parsing

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| Pydantic Veri Modeli (models.py) | Kerem | [TODO] | ScanResult, Host, Port, Service modelleri |
| XML Repair fonksiyonu | Kerem | [TODO] | Kesik XML çıktılarını düzeltme |
| Nmap Adapter (nmap_adapter.py) | Kerem | [TODO] | XML -> Pydantic dönüşümü |
| UI Tablo Gösterimi (results_view.py) | Yiğit | [TODO] | Parse edilmiş sonuçları tablo olarak göster |

### Sprint 5: Öneri Motoru

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| Maskeleme Servisi (masking.py) | Kerem | [TODO] | Opsiyonel cloud mode için IP/hostname maskeleme |
| Öneri Şeması | Kerem | [OK] | schemas.py'da SuggestionSchema var |
| Öneri Üretici (suggestion_engine.py) | Kerem | [TODO] | Bulgulara göre sonraki adım önerileri |
| UI Öneri Paneli | Yiğit | [TODO] | Önerileri kartlar halinde göster |

### Sprint 6: Plugin Sistemi ve Final Build

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| Plugin Structure | Yiğit | [TODO] | Interface ve Manager |
| Linux Build | Kerem | [TODO] | PyInstaller |

---

## Tamamlanan Sprint: Sprint 3.3 (Hybrid LLM Motoru) [OK]

> Tasarım dokümanı: `docs/hierarchical_intent_design.md`  
> Temel: Sprint 3.2 Track C altyapısı

| # | Görev | Sorumlu | Durum |
|---|-------|---------|-------|
| 3.3.1 | CategoryResult + SENTINEL_CATEGORIES modeli | Kerem | [OK] |
| 3.3.2 | HierarchicalResolver base class | Kerem | [OK] |
| 3.3.3 | Stage 1 — Category Resolver | Kerem | [OK] |
| 3.3.4 | Stage 2 — Sub-Intent Resolver | Kerem | [OK] |
| 3.3.5 | KeywordPreFilter bypass entegrasyonu | Kerem | [OK] |
| 3.3.6 | Orchestrator feature flag | Kerem | [OK] |
| 3.3.7 | Flat vs Hierarchical benchmark | Kerem | [OK] |
| 3.3.8 | Unit testler (57 test) | Kerem | [OK] |
| 3.3.9 | Model: Qwen 2.5 3B Instruct entegrasyonu | Kerem | [OK] |
| 3.3.10 | Docker/doküman güncellemesi | Kerem | [OK] |

---

## Tamamlanan Sprint: Sprint 3.6 (Backend Agent-Chat Foundation) [OK]

> Kapsam: UI tarafında değişiklik yapılmadan sadece backend geliştirmesi.

| # | Görev | Sorumlu | Durum |
|---|-------|---------|-------|
| 3.6.1 | Conversation memory store (`conversation_memory.py`) | Kerem | [OK] |
| 3.6.2 | Orchestrator multi-turn context (`process_v2` session-aware) | Kerem | [OK] |
| 3.6.3 | Yarı-otomatik agent çıktısı (`requires_approval`, `agent_observation`) | Kerem | [OK] |
| 3.6.4 | REST chat endpointleri (`/api/chat/session`, `/api/chat/turn`, `/api/chat/history`) | Kerem | [OK] |
| 3.6.5 | Backend gateway session çağrısı (`ask_ai_with_session`) | Kerem | [OK] |
| 3.6.6 | Backend testleri (`test_backend_chat_session.py`) + regresyon | Kerem | [OK] |

---

## Sıradaki Adımlar

1. **Sprint 4** — Veri Adaptasyonu (`models.py` + `nmap_adapter.py`)
2. **Sprint 5** — Öneri Motoru

---

## Tamamlanan Sprint: Sprint 3.5 (Tool Komut Doğruluğu + Güvenlik) [OK]

| Başlık | Durum | Not |
|---|---|---|
| Shell injection sertleştirme | [OK] | Kritik tool komut yolları güvenli arg-list üretimine çekildi |
| Tool komut doğruluğu | [OK] | Nmap/web/recon/attack tool komut üretimi normalize edildi, %100 oran |
| Yeni tool kapsaması | [OK] | OS detection, whois, hydra ssh/http, sqlmap yürütme katmanında eklendi |
| Registry/execution hizalaması | [OK] | Registry metadata-only; yürütme için execution registry + tool build_command |