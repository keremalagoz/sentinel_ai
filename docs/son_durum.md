# SENTINEL AI - Proje Durum Raporu

**Tarih:** 17 Ocak 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0: Proje Altyapısı ✅

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| Klasör yapısı | Kerem | ✅ |
| Git branch yapısı (main, develop, dev_kerem, dev_yigit) | Kerem | ✅ |
| Docker Llama servisi (GPU Enabled 🚀) | Kerem/Yiğit | ✅ |
| Docker API servisi | Kerem | ✅ |
| requirements.txt | Yiğit | ✅ |
| README.md | Kerem | ✅ |

### Sprint 1: Akıllı Süreç Motoru ✅

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| AdvancedProcessManager | Yiğit | ✅ |
| Terminal View | Yiğit | ✅ |
| Styles (tema, renkler) | Yiğit | ✅ |
| Interactive Patterns | Yiğit | ✅ |
| Session Loglama | Yiğit | ✅ |

### Sprint 2: Hibrit AI Komut Motoru ✅

| Görev | Sorumlu | Durum |
|-------|---------|-------|
| JSON Şemaları (schemas.py) | Kerem | ✅ |
| AI Orchestrator (orchestrator.py) | Kerem | ✅ |
| Docker Tools Container | Kerem | ✅ |
| Docker Runner Helper | Kerem | ✅ |
| main.py (GUI entegrasyonu) | Yiğit | ✅ |

---

## Mevcut Dosya Yapısı

```
sentinel_root/
├── main.py                      ✅ PRODUCTION - Docker Full Stack
├── main_developer.py            ✅ YENİ - Developer Mode (Native Ollama)
├── requirements.txt             ✅
├── README.md                    ✅ Developer mode guide eklendi
├── docker-compose.yml           ✅ GPU Support & WhiteRabbitNeo
├── son_durum.md                 ✅
│
├── src/
│   ├── ai/                      ← Kerem'in alanı
│   │   ├── schemas.py           ✅ Intent, ToolSpec, FinalCommand (v2)
│   │   ├── orchestrator.py      ✅ Action Planner v2
│   │   ├── tool_registry.py     ✅ YENİ - 15 tool metadata
│   │   ├── intent_resolver.py   ✅ YENİ - LLM intent parser
│   │   ├── command_builder.py   ✅ YENİ - Deterministik builder
│   │   └── policy_gate.py       ✅ YENİ - Opsiyonel kontrol
│   │
│   ├── core/                    
│   │   ├── execution_manager.py ✅ YENİ (Sprint 3 Core)
│   │   ├── cleaner.py           ✅ YENİ (Sprint 3 Core)
│   │   ├── validators.py        ✅ YENİ (Sprint 3 Core)
│   │   ├── process_manager.py   ✅ Güncellendi
│   │   └── docker_runner.py     ✅ (Legacy support)
│   │
│   ├── ui/                      ← Yiğit'in alanı
│   │   ├── terminal_view.py     ✅
│   │   └── styles.py            ✅
│   │
│   ├── plugins/                 ⏳ Sprint 6
│   │
│   └── tests/
│       ├── test_sprint1.py      ✅
│       ├── interactive_test.py  ✅
│       ├── validate_sprint3.py  ✅ Sprint 3 Validation
│       ├── test_action_planner_v2.py ✅ YENİ - v2 test suite
│       └── test_model_comparison.py  ✅ YENİ - LLM benchmark
│
├── docker/
│   ├── llama/                   ✅ Llama 3 servisi
│   ├── whiterabbitneo/          ✅ YENİ - WhiteRabbitNeo servisi
│   ├── api/                     ✅ API backend
│   └── tools/                   ✅ Güvenlik araçları
│
│
├── docs/
│   └── Detaylı Fazlandırılmış.pdf
│
└── temp/                        Session logları
```

---

## Docker Servisleri

| Container | Durum | Port | İçerik |
|-----------|-------|------|--------|
| sentinel-llama | ✅ Çalışıyor | 8001 | Llama 3 AI (8B model) - **GPU ENABLED** |
| sentinel-api | ✅ Çalışıyor | 8000 | API Backend |
| sentinel-tools | ✅ Çalışıyor | - | Nmap, Gobuster, Nikto, Hydra |

---

## 🎯 Aktif Sprint: Sprint 3

### Sprint 3: Güvenlik, Yetki ve Temizlik

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| ExecutionManager | Yiğit | ✅ | Docker/Native mod yönetimi & Pkexec logic |
| Secure Cleaner (cleaner.py) | Yiğit | ✅ | Güvenli dosya temizleme, Whitelist, Shredding |
| Input Validation | Yiğit | ✅ | IP/Domain validasyonu, Shell injection check |
| ProcessManager Update | Yiğit | ✅ | Yeni core modüllerle entegrasyon |
| UI Security Indicators | Yiğit | ⏳ | Terminalde 'ROOT' ikonu, kilit işareti vb. |
| Settings Menu (Security) | Yiğit | ⏳ | "Temizlik Sıklığı" vb. güvenlik ayarları |

---

## Aktif Mini Sprint: Action Planner v2

**Tarih:** 17 Ocak 2026  
**Sorumlu:** Kerem  
**Amaç:** Karar motoru mimarisini yeniden tasarlamak (ChatGPT 5.2 analizi dogrultusunda)

### Mimari Degisiklikler

| Eski (v1) | Yeni (v2) |
|-----------|-----------|
| LLM tool adi uretiyor | LLM sadece intent belirliyor |
| LLM argumanlar uretiyor | Registry'den geliyor |
| LLM risk/root belirliyor | Tool metadata'dan |
| Tek katman | 4 katmanli mimari |
| Validasyon en sonda | Her katmanda validasyon |

### Gorevler

| # | Gorev | Dosya | Durum |
|---|-------|-------|-------|
| 1 | Intent & ToolSpec semalari | schemas.py | ✅ TAMAMLANDI |
| 2 | Tool Registry (15 arac) | tool_registry.py | ✅ TAMAMLANDI |
| 3 | Intent Resolver | intent_resolver.py | ✅ TAMAMLANDI |
| 4 | Command Builder | command_builder.py | ✅ TAMAMLANDI |
| 5 | Policy Gate (opsiyonel) | policy_gate.py | ✅ TAMAMLANDI |
| 6 | Orchestrator refactor | orchestrator.py | ✅ TAMAMLANDI |
| 7 | Test ve dogrulama | test_action_planner_v2.py | ✅ TAMAMLANDI |
| 8 | Developer Mode | main_developer.py | ✅ TAMAMLANDI |

### Developer Mode

**Problem:** Docker + WSL → ~6GB RAM kullanımı, LLM gecikmeleri

**Çözüm:** Native Ollama + Mock Execution

| Özellik | Production (main.py) | Developer (main_developer.py) |
|---------|----------------------|-------------------------------|
| LLM | Docker Ollama (8001) | Native Ollama (11434) |
| Docker | Gerekli | GEREKMIYOR |
| WSL | Aktif (~6GB) | Kapalı (0GB) |
| Execution | Gerçek komutlar | Mock çıktılar |
| Kullanım | Gerçek testler | UI/AI geliştirme |
| Hız | Normal | 2-3x hızlı |

**Setup:**
```bash
# 1. Native Ollama kur
ollama pull whiterabbitneo

# 2. Developer mode başlat
python main_developer.py
```

### LLM Secimi

| Model | Dogruluk | Karar |
|-------|----------|-------|
| Llama 3:8b | %63.6 | - |
| WhiteRabbitNeo | %90.9 | ✅ SECILDI |

### Yeni Akis

```
User Input
    |
    v
[Intent Resolver] --> LLM sadece intent belirler
    |
    v
[Policy Gate] --> Opsiyonel, toggle ile acilir/kapanir
    |
    v
[Tool Registry] --> Intent --> Tool (deterministic)
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
| Pydantic Veri Modeli (models.py) | Kerem | ❌ | ScanResult, Host, Port, Service modelleri |
| XML Repair fonksiyonu | Kerem | ❌ | Kesik XML çıktılarını düzeltme |
| Nmap Adapter (nmap_adapter.py) | Kerem | ❌ | XML → Pydantic dönüşümü |
| UI Tablo Gösterimi (results_view.py) | Yiğit | ❌ | Parse edilmiş sonuçları tablo olarak göster |

### Sprint 5: Öneri Motoru

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| Maskeleme Servisi (masking.py) | Kerem | ❌ | IP/hostname maskeleme |
| Öneri Şeması | Kerem | ✅ | schemas.py'da SuggestionSchema var |
| Öneri Üretici (suggestion_engine.py) | Kerem | ❌ | Bulgulara göre sonraki adım önerileri |
| UI Öneri Paneli | Yiğit | ❌ | Önerileri kartlar halinde göster |

### Sprint 6: Plugin Sistemi ve Final Build

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| Plugin Structure | Yiğit | ❌ | Interface ve Manager |
| Linux Build | Kerem | ❌ | PyInstaller |

---

## Sıradaki Adımlar

### 🔵 Yiğit İçin (Sprint 3 Kalanlar)

1. **UI Security Indicators** - Öncelik: ORTA
   - TerminalView'da, komut root yetkisi gerektiriyorsa (örn: nmap -sS) küçük bir kırmızı kilit veya kalkan ikonu göster.
   - Kullanıcıya "Bu komut yönetici yetkisiyle çalışacak" uyarısı ver.

2. **Settings Menu** - Öncelik: DÜŞÜK
   - Basit bir ayarlar penceresi.
   - Cleaner ayarları (Gün sayısı, Auto-clean on exit).

### 🟢 Kerem İçin (Sprint 4 Hazırlık)

1. **models.py Tasarımı** - Öncelik: YÜKSEK
   - Nmap XML çıktılarını karşılayacak Pydantic modelleri.

---

## Git Durumu

| Branch | Son Durum |
|--------|-----------|
| main | Sprint 0 + 1 |
| develop | Sprint 0 + 1 + 2 + **3(Core)** ✅ |
| dev_kerem | Sprint 0 + 1 + 2 + GPU Hotfix |
| dev_yigit | Sprint 0 + 1 + 2 + **3(Core)** ✅ |

---

*Son Güncelleme: 17 Ocak 2026*
