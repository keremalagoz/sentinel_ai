# SENTINEL AI - Proje Durum Raporu

**Tarih:** 22 Ocak 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0: Proje Altyapısı [OK]

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| Klasör yapısı | Kerem | [OK] |
| Git branch yapısı (main, develop, dev_kerem, dev_yigit) | Kerem | [OK] |
| Docker Llama servisi (GPU Enabled) | Kerem/Yiğit | [OK] |
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

### Sprint 2: Hibrit AI Komut Motoru [OK]

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
├── son_durum.md                 [OK] Guncellendi (22 Ocak 2026)
│
├── src/
│   ├── ai/                      (Kerem)
│   │   ├── schemas.py           [OK] ConfigDict + legacy uyum
│   │   ├── orchestrator.py      [OK] Registry tek kaynak
│   │   ├── tool_registry.py     [OK] Execution mapping + SSL/Subdomain
│   │   ├── intent_resolver.py   [OK] Strict payload dogrulama
│   │   ├── command_builder.py   [OK] Deterministik builder
│   │   ├── policy_gate.py       [OK] Tek policy akis
│   │   ├── execution_policy.py  [OK] ConfigDict guncelleme
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
├── docs/
│   └── Detayli Fazlandirilmis.pdf
│
└── temp/                        Session loglari
```

---

## Docker Servisleri

| Container | Durum | Port | İçerik |
|-----------|-------|------|--------|
| sentinel-llama | Kontrol edilmedi | 8001 | Llama 3 AI (8B model) |
| sentinel-api | Kontrol edilmedi | 8000 | API Backend |
| sentinel-tools | Kontrol edilmedi | - | Nmap, Gobuster, Nikto, Hydra |

---

## Aktif Sprint: Sprint 3

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

## Mini Sprint: Action Planner v2.1 Stabilizasyon

**Tarih:** 22 Ocak 2026  
**Sorumlu:** Kerem  
**Amaç:** Karar motorunu sprint planina girmeden stabil hale getirmek

### Tamamlanan Duzeltmeler

| # | Gorev | Dosya | Durum |
|---|-------|-------|-------|
| 1 | Registry tek kaynak (execution mapping) | tool_registry.py, orchestrator.py | [OK] |
| 2 | Policy tek akis | policy_gate.py, execution_policy.py | [OK] |
| 3 | Intent JSON strict dogrulama | intent_resolver.py | [OK] |
| 4 | API uyumu (deterministik komut) | api_server.py | [OK] |
| 5 | PyQt6 standardizasyonu | core + tests + requirements.txt | [OK] |
| 6 | Emoji temizligi | kod + dokumantasyon | [OK] |

### Test Durumu

- pytest: src/tests/test_action_planner_v2.py -> 6/6 PASSED (22 Ocak 2026)

### Yeni Akis (v2.1 Stabil)

```
User Input
    |
    v
[Intent Resolver] --> LLM sadece intent belirler
    |
    v
[Policy Gate] --> Tek policy akis (aktif)
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
| Maskeleme Servisi (masking.py) | Kerem | [TODO] | IP/hostname maskeleme |
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

### Yigit Icin (Sprint 3 Kalanlar)

1. UI Security Indicators - Oncelik: ORTA
   - TerminalView'da root uyarisi gosterimi

2. Settings Menu - Oncelik: DUSUK
   - Temizlik sikligi ve auto-clean ayarlari

### Kerem Icin (Sprint 4 Hazirlik)

1. models.py tasarimi - Oncelik: YUKSEK
   - Nmap XML ciktilarini karsilayacak Pydantic modelleri

---

## Git Durumu

| Branch | Son Durum |
|--------|-----------|
| main | Sprint 0 + 1 |
| develop | Sprint 0 + 1 + 2 + 3 (core) |
| dev_kerem | Sprint 0 + 1 + 2 + 3 + v2.1 stabilizasyon |
| dev_yigit | Sprint 0 + 1 + 2 + 3 (core) |

---

*Son Güncelleme: 22 Ocak 2026*
