# SENTINEL AI - Sprint Roadmap (Güncel)

**Güncelleme Tarihi:** 23 Şubat 2026  
**Mimari:** Action Planner v2.1 (Intent-Driven + Deterministic Command Builder)

---

## 1) Proje Amacı

SENTINEL AI; doğal dilde verilen siber güvenlik taleplerini,
kontrollü ve denetlenebilir bir akışla çalıştırılabilir komutlara dönüştüren
hibrit AI destekli güvenlik test platformudur.

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
  - `execution_policy.py`
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

---

## 4) Aktif Öncelikler (Kısa Vade)

1. **Parser API uyumunun tamamlanması**
   - Test faili: `test_parser_framework.py::TestParserHelpers::test_create_vulnerability_entity`
2. **Dokümantasyon-kod senkronizasyonu**
   - README, PROJECT_STRUCTURE, son_durum güncel kalmalı
3. **ExecutionPolicy netleştirme**
   - Tek policy katmanı korunmalı

---

## 5) Sonraki Sprint Hedefleri

### Sprint 4 - Veri Adaptasyonu ve Sonuç Modelleri
- `src/core/models.py` (Pydantic result modelleri)
- `src/core/adapters/nmap_adapter.py` (XML -> model)
- XML onarım ve robust parse akışı

### Sprint 5 - Öneri Motoru
- `src/ai/masking.py` (cloud öncesi maskeleme)
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
4. Güvenlik politikaları bypass edilmemeli.
5. UI donmadan işlem tamamlanmalı.

---

## 7) Notlar

- Bu doküman mevcut kod tabanı ile uyumlu tutulur.
- Arşiv/eskimiş planlar `temp` altında tutulmaz; temiz çalışma ağacı hedeflenir.


