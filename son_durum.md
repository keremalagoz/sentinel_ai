# SENTINEL AI - Proje Durum Raporu

**Tarih:** 5 Mart 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0-2 [OK]

- Proje altyapısı, Docker servisleri ve temel UI/Core iskeleti tamamlandı.
- Action Planner v2.1 deterministic akışı devreye alındı.
- Local AI (WhiteRabbitNeo → Qwen 2.5 3B) ile intent çözümleme stabilize edildi.

---

## Mevcut Durum (Özet)

- Mimari: Local-only LLM (Qwen 2.5 3B / Ollama) + deterministic tool execution
- Model: Qwen 2.5 3B Instruct Q4_K_M (1.84 GB, 29+ dil, 151K vocab)
- Intent Pipeline: Keyword Pre-Filter → Stage 1 (5 kategori) → Stage 2 (16 intent)
- Benchmark: %100 doğruluk (30/30, hierarchical mod), %94.7 deterministik pipeline (75 senaryo)
- Kararlılık: Queue/backpressure, per-tool limit, retry/backoff aktif
- Güvenilirlik: Registry drift guard (startup + test) aktif
- Gözlemlenebilirlik: Runtime telemetry (`queue_wait_ms`, `tool_run_ms`) mevcut
- Gözlemlenebilirlik: Runtime telemetry status bar yüzeyi aktif (`Q`, `Wait`, `Run`)
- **i18n**: 11 dil desteği (EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI) — 97 çeviri anahtarı
- **Ayarlar Diyalogu**: Dil seçimi, font boyutu, oturum temizleme
- **Güvenli Temizlik**: `secure_delete` ayarı backend cleaner akışına bağlı
- **Komut Kaynağı**: API execute akışında execution tool `build_command` öncelikli
- **Registry Stratejisi**: `build_tool_spec()` metadata-only (arguments boş)
- **Performans**: 12 optimizasyon uygulandı (debounce, cache, pre-compile, QSS sabitleri)
- **Test**: Full suite **1451 passed** + Sprint 3.6 hedefli doğrulama **21 passed**

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

- Full test suite: **1451 passed** (Sprint 3.5 hotfix sonrası)
- UI testleri: ~500 test (i18n, widget, özellik testleri)
- Optimizasyon testleri: 91 test (performans + anti-pattern taraması)
- Sprint 3.5 audit testleri: 296 test (E2E tool komut doğrulaması)
- Tool komut testleri: 108 test
- Pipeline entegrasyon: 79 test
- Komut üretim doğruluk benchmarkı: 76 test (%94.7 oran)
- Backend/AI testleri: ~124 test
- P0 doğrulama: `scripts/p0_validation.py --with-pytest` başarılı

| Test Dosyası | Test Sayısı | Kapsam |
|---|---|---|
| test_i18n.py | 156 | 11 dil çeviri doğruluğu |
| test_ui_widgets.py | 138 | Widget oluşturma ve davranış |
| test_ui_features.py | 245 | UI özellikleri (settings, swap, history) |
| test_optimizations.py | 91 | Performans ve anti-pattern taraması |
| test_sprint35_audit.py | 296 | Sprint 3.5 E2E audit testleri |
| test_tool_commands.py | 108 | Tool komut üretim testleri |
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
| 3.3.9 | Model değişimi: WhiteRabbitNeo 7B → Qwen 2.5 3B | Kerem | [OK] |
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
| Tool komut doğruluğu | [OK] | Nmap/web/recon/attack tool komut üretimi normalize edildi |
| Yeni tool kapsaması | [OK] | OS detection, whois, hydra ssh/http, sqlmap yürütme katmanında eklendi |
| Registry/execution hizalaması | [OK] | Registry metadata-only; yürütme için execution registry + tool build_command |
| Telemetry görünürlüğü | [OK] | UI status bar metrikleri aktif |
| Secure delete uçtan uca | [OK] | Settings → BackendGateway → Cleaner zinciri bağlı || Yüksek riskli komut onay mekanizması | [OK] | `_needs_confirmation()` + güvenlik ayarları entegrasyonu (hotfix) |
| LLM parse fallback (keyword) | [OK] | LLM başarısız olduğunda keyword filter fallback — orchestrator (hotfix) |
| Komut üretim doğruluk benchmarkı | [OK] | 75 senaryo, %94.7 doğruluk — `test_command_accuracy.py` (hotfix) |
---

## Tamamlanan Sprint: Sprint 3.4 (UI / i18n / Performans Optimizasyonu) [OK]

> Sorumlu: Yiğit  
> Tarih: 1–4 Mart 2026

### Sprint 3.4 Özet

| # | Görev | Sorumlu | Durum | Açıklama |
|---|-------|---------|-------|----------|
| 3.4.1 | Sprint 3 font hataları (5 bug) | Yiğit | [OK] | Chat/terminal font tutarlılığı, bold, miras |
| 3.4.2 | Layout Swap (Chat/Terminal pozisyon) | Yiğit | [OK] | Yatay/dikey düzen değiştirme |
| 3.4.3 | i18n sistemi (11 dil) | Yiğit | [OK] | `src/ui/i18n.py` — 97 anahtar × 11 dil |
| 3.4.4 | Ayarlar Diyalogu | Yiğit | [OK] | `settings_dialog.py` — dil, font, temizlik |
| 3.4.5 | Orchestrator i18n entegrasyonu | Yiğit | [OK] | "Komut hazır" çevirisi + badge fallback |
| 3.4.6 | UI test altyapısı (conftest.py) | Yiğit | [OK] | QApplication fixture + i18n reset |
| 3.4.7 | i18n testleri (~156 test) | Yiğit | [OK] | 8 sınıf, her dil için 78 anahtar doğrulama |
| 3.4.8 | Widget testleri (~138 test) | Yiğit | [OK] | 11 sınıf, tüm widget oluşturma/davranış |
| 3.4.9 | Özellik testleri (~206 test) | Yiğit | [OK] | 11 sınıf, layout swap, history, font, risk |
| 3.4.10 | Performans audit (12 sorun tespit) | Yiğit | [OK] | 5 HIGH + 7 MEDIUM seviye optimizasyon |
| 3.4.11 | 12 optimizasyon uygulaması | Yiğit | [OK] | Debounce, cache, pre-compile, QSS sabitleri |
| 3.4.12 | Optimizasyon testleri (91 test) | Yiğit | [OK] | 13 sınıf, timing benchmark + anti-pattern |

### Uygulanan Performans Optimizasyonları

| # | Seviye | Optimizasyon | Dosya |
|---|--------|-------------|-------|
| H1+H3 | HIGH | Chat History debounce + in-memory cache | chat_interface.py |
| H2 | HIGH | findChild → `_bubble_refs` cache | chat_interface.py |
| H4 | HIGH | Font update re-render yerine şeritsiz | chat_interface.py |
| H5 | HIGH | Regex pre-compile (`_JSON_BLOCK_RE`) | intent_resolver.py, hierarchical_resolver.py |
| M1 | MEDIUM | `get_available_languages()` no-copy | i18n.py |
| M2 | MEDIUM | QFont cache (`_font_cache` dict) | chat_interface.py |
| M3 | MEDIUM | QSS string sabitleri (8+ modul const) | chat_interface.py |
| M4+M11 | MEDIUM | Status badge on-hesaplanmış stiller | terminal_view.py, main_window.py |
| M5 | MEDIUM | Tab-session lookup dictionary | terminal_view.py |
| M6 | MEDIUM | validators.py regex pre-compile | validators.py |
| M7 | MEDIUM | parser_framework regex pre-compile | parser_framework.py |
| M9+M10 | MEDIUM | Terminal buffer toplu temizlik | terminal_view.py |

---

## Git Durumu

| Branch | Son Durum |
|--------|-----------|
| main | Sprint 0 + 1 |
| develop | Sprint 0 → 3.2 dahil (merge commit 02e352c) |
| dev_kerem | Sprint 0 → 3.6 dahil |
| dev_yigit | Sprint 0 + 1 + 2 + 3 (core) |

---

*Son Güncelleme: 5 Mart 2026*
