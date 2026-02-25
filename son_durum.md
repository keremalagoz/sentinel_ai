# SENTINEL AI - Proje Durum Raporu

**Tarih:** 25 Şubat 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0: Proje Altyapısı [OK]

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| Klasör yapısı | Kerem | [OK] |
| Git branch yapısı (main, develop, dev_kerem, dev_yigit) | Kerem | [OK] |
| Docker WhiteRabbitNeo servisi (GPU Enabled) | Kerem/Yiğit | [OK] |
| Docker API servisi | Kerem | [OK] |
| requirements.txt | Yiğit | [OK] |
| README.md | Kerem | [OK] |

### Sprint 1: Akıllı Süreç Motoru [OK]

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| AdvancedProcessManager | Yiğit | [OK] |
| Terminal View | Yiğit | [OK] |
| Styles (tema, renkler) | Yiğit | [OK] |
| Interactive Patterns | Yiğit | [OK] |
| Session Loglama | Yiğit | [OK] |

### Sprint 2: Local AI Komut Motoru [OK]

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| JSON Şemaları (schemas.py) | Kerem | [OK] |
| AI Orchestrator (orchestrator.py) | Kerem | [OK] |
| Docker Tools Container | Kerem | [OK] |
| Docker Runner Helper | Kerem | [OK] |
| main.py (GUI entegrasyonu) | Yiğit | [OK] |

---

## Mevcut Dosya Yapısı (Kritik Dosyalar)

```
sentinel_root/
├── main.py                      [OK] PRODUCTION - Docker Full Stack
├── main_developer.py            [OK] Developer Mode (Native Ollama)
├── requirements.txt             [OK] PyQt6 standardizasyonu
├── README.md                    [OK] Emoji temizligi + dev mode dokumani
├── PROJECT_STRUCTURE.md         [OK] Emoji temizligi
├── docker-compose.yml           [OK] GPU Support & WhiteRabbitNeo
├── son_durum.md                 [OK] Guncellendi (23 Şubat 2026)
│
├── src/
│   ├── ai/                      (Kerem)
│   │   ├── schemas.py           [OK] ConfigDict + legacy uyum
│   │   ├── orchestrator.py      [OK] Registry tek kaynak
│   │   ├── tool_registry.py     [OK] Execution mapping + SSL/Subdomain
│   │   ├── intent_resolver.py   [OK] Strict payload dogrulama
│   │   ├── command_builder.py   [OK] Deterministik builder
│   │   └── api_server.py        [OK] Deterministik komut uretimi
│   │
│   ├── core/
│   │   ├── execution_manager.py [OK] Sprint 3 Core
│   │   ├── cleaner.py           [OK] Guvenli temizleme
│   │   ├── validators.py        [OK] Input validation
│   │   ├── process_manager.py   [OK] ExecutionManager entegrasyonu
│   │   ├── tool_base.py         [OK] PyQt6 sinyaller
│   │   ├── tool_integration.py  [OK] PyQt6 sinyaller
│   │   └── sentinel_coordinator.py [OK] PyQt6 sinyaller
│   │
│   ├── ui/
│   │   ├── terminal_view.py     [OK] Emoji temizligi
│   │   └── styles.py            [OK]
│   │
│   └── tests/
│       ├── test_action_planner_v2.py [OK] Pytest uyarilari temizlendi
│       ├── test_advanced_parsers.py  [OK] Emoji temizligi
│       ├── test_new_tools.py         [OK] Emoji temizligi
│       └── test_ui_integration.py    [OK] PyQt6 standardizasyonu
│
├── docs/                        Teknik dokumantasyon
│
└── temp/                        Session loglari + sentinel_safe
```

---

## Docker Servisleri

| Container | Durum | Port | İçerik |
|-----------|-------|------|--------|
| sentinel-whiterabbitneo | Kontrol edilmedi | 8002 | WhiteRabbitNeo AI (Ollama) |
| sentinel-api | Kontrol edilmedi | 8000 | API Backend |
| sentinel-tools | Kontrol edilmedi | - | Nmap, Gobuster, Nikto, Hydra |

---

## Aktif Sprint: Sprint 3.5 (Stabilizasyon / Sertleştirme)

### Sprint 3: Güvenlik, Yetki ve Temizlik

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| ExecutionManager | Yiğit | [OK] | Docker/Native mod yönetimi & Pkexec logic |
| Secure Cleaner (cleaner.py) | Yiğit | [OK] | Güvenli dosya temizleme, Whitelist, Shredding |
| Input Validation | Yiğit | [OK] | IP/Domain validasyonu, Shell injection check |
| ProcessManager Update | Yiğit | [OK] | Yeni core modüllerle entegrasyon |
| UI Security Indicators | Yiğit | [TODO] | Terminalde root uyarisi |
| Settings Menu (Security) | Yiğit | [TODO] | Temizlik sikligi vb. |

---

### Sprint 3.5: Performans ve Güvenilirlik Sertleştirme

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

- Full test suite: **111 passed**
- P0 doğrulama: `scripts/p0_validation.py --with-pytest` başarılı

---

## Mini Sprint: Action Planner v2.1 Stabilizasyon

**Tarih:** 22 Ocak 2026  
**Sorumlu:** Kerem  
**Amaç:** Karar motorunu sprint planina girmeden stabil hale getirmek

### Tamamlanan Duzeltmeler

| # | Gorev | Dosya | Durum |
|---|-------|-------|-------|
| 1 | Registry tek kaynak (execution mapping) | tool_registry.py, orchestrator.py | [OK] |
| 2 | Policy sadeleştirme | Policy katmanı kaldırıldı | [OK] |
| 3 | Intent JSON strict dogrulama | intent_resolver.py | [OK] |
| 4 | API uyumu (deterministik komut) | api_server.py | [OK] |
| 5 | PyQt6 standardizasyonu | core + tests + requirements.txt | [OK] |
| 6 | Emoji temizligi | kod + dokumantasyon | [OK] |

### Test Durumu

- pytest: src/tests/test_action_planner_v2.py -> 5/5 PASSED (23 Şubat 2026)

### Yeni Akis (v2.1 Stabil)

```
User Input
    |
    v
[Intent Resolver] --> LLM sadece intent belirler
    |
    v
[Tool Registry] --> Intent -> Tool (deterministic)
    |
    v
[Command Builder] --> ToolSpec + Params --> Final Command
    |
    v
[Execution Layer]
```

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

## Siradaki Adimlar

1. Dokümantasyon senkronizasyonunu tamamla
    - README, PROJECT_STRUCTURE, sprint_roadmap, son_durum tutarlılığı

2. Sprint 4 veri modeli/adapter başlangıcı
    - `models.py` + `nmap_adapter.py` ilk iterasyon

3. Runtime telemetry UI görünürlüğü
    - Tool kuyruğu ve çalışma sürelerinin arayüzde gösterimi

---

## Git Durumu

| Branch | Son Durum |
|--------|-----------|
| main | Sprint 0 + 1 |
| develop | Sprint 0 + 1 + 2 + 3 (core) |
| dev_kerem | Sprint 0 + 1 + 2 + 3 + v2.1 + 3.5 sertleştirme |
| dev_yigit | Sprint 0 + 1 + 2 + 3 (core) |

---

*Son Güncelleme: 25 Şubat 2026*
