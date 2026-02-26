# SENTINEL AI - Sprint Roadmap (Güncel)

**Güncelleme Tarihi:** 26 Şubat 2026  
**Mimari:** Action Planner v2.1 (Local-Only LLM + Deterministic Command Builder)

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
  - `whiterabbitneo-service` (8002)
  - `api-service` (8000)
  - `tools-service`

---

## 3) Tamamlanan Kapsam

### Sprint 0 - Altyapı
- Proje klasör yapısı
- Docker compose altyapısı
- Python bağımlılık standardizasyonu

### Sprint 1 - Süreç Motoru + State
- QProcess tabanlı çalıştırma
- SQLite backend + execution history
- Parser framework + entity id stratejisi
- Tool integration zinciri

### Sprint 2 - AI Karar Katmanı
- Intent tabanlı akış
- Deterministik tool mapping
- Deterministik command build
- API tarafında deterministik command preparation

### Sprint 3 - Güvenlik ve Temizlik
- `execution_manager` ile mod yönetimi (docker/native)
- `process_manager` ile yetki/red senaryoları
- `cleaner.py` ile güvenli temizlik

### Sprint 3.5 - Stabilizasyon ve Sertleştirme
- Queue backpressure + global concurrency limiti
- Per-tool concurrency limiti
- Local LLM timeout/retry/backoff akışı
- Registry drift guard (startup doğrulama + test)
- Adaptif timeout kestirimi + runtime telemetry yüzeyi

---

### Sprint 3.6 - Optimizasyon ve Platform Hazırlığı
- **Track A:** Kritik bugfix (merkezi logging, callback safety, BackendGateway fix, dok senkronizasyonu)
- **Track B:** Linux platform uyumluluğu (5 Windows-bağımlı tool komutu düzeltme, platform_utils modülü)
- **Track C:** AI ölçeklenme altyapısı (intent confidence skoru, keyword pre-filter, response time budget)
- **Track D:** Kod kalitesi (tool_base.py bölme, SQLite WAL, legacy schema temizliği)
- Detaylı plan: [sprint_3_6_plan.md](sprint_3_6_plan.md)

---

## 3.1) Hızlı Durum Özeti

- Mimari: Local-only LLM + deterministic execution
- Test sağlığı: full suite yeşil (112 passed)
- Aktif sprint: **Sprint 3.6** (Optimizasyon ve Platform Hazırlığı)
- Operasyonel odak: P0 bugfix, Linux uyumluluk, AI scaling altyapısı

---

## 4) Aktif Öncelikler (Sprint 3.6)

1. **P0 Bugfix** — Merkezi logging, callback deadlock fix, BackendGateway güvenlik düzeltmesi
2. **Linux Platform Uyumu** — 5 Windows-only tool komutu düzeltme, platform_utils modülü
3. **AI Ölçeklenme** — Intent confidence skoru, keyword pre-filter, response time budget
4. **Kod Kalitesi** — tool_base.py dosya bölme, SQLite WAL mode
5. **Dokümantasyon senkronizasyonu** — PROJECT_STRUCTURE, README güncellemesi

---

## 5) Sonraki Sprint Hedefleri

### Sprint 4 - Veri Adaptasyonu ve Sonuç Modelleri
- `src/core/models.py` (Pydantic result modelleri)
- `src/core/adapters/nmap_adapter.py` (XML -> model)
- XML onarım ve robust parse akışı

### Sprint 5 - Öneri Motoru
- `src/ai/masking.py` (ileride opsiyonel cloud mode için)
- `src/ai/suggestion_engine.py`
- UI öneri paneli entegrasyonu

### Sprint 6 - Plugin ve Final Build
- Plugin interface + loader
- Linux build pipeline (PyInstaller)

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

## 8) Kısa Backlog (Öncelik Sırası)

1. ~~Telemetry verisini UI'da görünür yap~~ → Sprint 3.6 Track C'ye taşındı
2. `models.py` + `nmap_adapter.py` ilk çalışan sürüm (Sprint 4)
3. Sonuç modeline bağlı öneri üretim prototipi (Sprint 5)
4. Plugin altyapısı için minimum arayüz (Sprint 6)
5. Dual-model stratejisi benchmark (Sprint 4-5 arası)


