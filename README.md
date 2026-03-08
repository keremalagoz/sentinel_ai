# SENTINEL AI

> Son Senkronizasyon: 5 Mart 2026 (Sprint 3.5 hotfix güncellemeleri dahil)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Qwen 2.5](https://img.shields.io/badge/Qwen_2.5_3B-Local_AI-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white)
![License](https://img.shields.io/badge/License-Source--Available-orange?style=for-the-badge)

**Local AI Destekli Güvenlik Test Aracı**

*Local AI | PyQt6 GUI | Docker Backend | Linux Target*

</div>

---

## Proje Hakkında

SENTINEL AI, siber güvenlik testlerini yapay zeka destekli komutlarla otomatikleştiren bir masaüstü uygulamasıdır. Local AI motoru olarak Qwen 2.5 3B (Ollama) kullanır ve 2 aşamalı hierarchical intent resolution pipeline ile yüksek doğruluk sağlar.

### Özellikler

- **Local AI Motoru** - Qwen 2.5 3B / Ollama tabanlı intent çözümleme (1.9 GB, 29+ dil)
- **2 Aşamalı Intent Resolution** - Keyword pre-filter → Kategori → Alt-intent pipeline
- **Modern PyQt6 Arayüzü** - Donmayan, responsive terminal ve sonuç görüntüleme
- **11 Dil Desteği (i18n)** - EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI — 97 çeviri anahtarı
- **Ayarlar Diyalogu** - Dil seçimi, font boyutu, oturum temizleme, güvenlik politikası
- **Esnek Yerleşim (Layout Swap)** - Chat/Terminal pozisyon değiştirme (yatay/dikey)
- **Performans Optimizasyonları** - Debounce I/O, in-memory cache, QFont cache, regex pre-compile, QSS sabitleri
- **Docker Altyapısı** - İzole ve taşınabilir servis mimarisi
- **Güvenli Yetki Yönetimi** - Pkexec ile şifresiz root işlemleri
- **Deterministik Çalıştırma** - Intent → Tool → Command zinciri
- **Tek Kaynak Komut Üretimi** - Çalıştırmada `BaseTool.build_command()` öncelikli, legacy fallback kontrollü
- **Tool Registry Metadata-Only** - Registry UI/planlama metadatası taşır, yürütme argümanları execution katmanında üretilir
- **Çalışma Zamanı Sertleştirme** - Queue/backpressure, per-tool limit, timeout/retry
- **Telemetry Görünürlüğü** - Status bar üzerinde kuyruk/bekleme/çalıştırma metrikleri
- **Güvenli Temizlik Akışı** - Ayarlardaki `secure_delete` bayrağı backend cleaner katmanına iletilir
- **Sprint 3.6 Backend Chat Hafızası** - Session/turn tabanlı multi-turn context (UI değişikliği olmadan)
- **Structured AI Command Execution** - AI komutları structured payload olarak çalıştırılır; raw terminal komutları ayrı güvenlik kapısından geçer
- **Backend-Owned Session Flow** - Chat history id ile backend session id ayrılmıştır; yeni sohbet, geri yükleme ve multi-turn akışları aynı backend session ile sürer
- **Typed Validation + Windows Native Execution** - URL/query/form payload argümanları typed validation ile korunur; Windows native yürütmede merkezi executable resolution ve subprocess fallback kullanılır
- **Kompakt Test Altyapısı** - Çekirdek AI ve backend kontratlarını doğrulayan hızlı regression paketi

### Planlanan Özellikler

- Sonuç modelleme + adapter katmanı (Sprint 4)
- Öneri motoru (Sprint 5)
- Plugin sistemi (Sprint 6)

---

## Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL AI                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │   PyQt6     │    │   AI        │    │   Process   │          │
│  │   GUI       │◄──►│ Orchestrator│◄──►│   Manager   │          │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘          │
│                            │                   │                │
│         ┌──────────────────┼───────────────────┤                │
│         ▼                  ▼                   ▼                │
│  ┌─────────────┐  ┌───────────────┐   ┌─────────────┐          │
│  │ Qwen 2.5 3B │  │ Keyword       │   │ Linux       │          │
│  │ (Ollama)    │  │ Pre-Filter    │   │ Tools       │          │
│  │ Port: 11434 │  │ (Regex)       │   │ (nmap, etc) │          │
│  └─────────────┘  └───────────────┘   └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘

Intent Pipeline:
  User Input → KeywordPreFilter → [Stage 1: Category] → [Stage 2: Sub-Intent] → Tool

Benchmark Politikası:
  Intent benchmark raporlaması hierarchical (2 aşamalı) mod üzerinden sürdürülür.

Backend Chat Pipeline (Sprint 3.6):
  Session Create → Chat Turn → Context Enrichment → Intent Resolution → Safe Command Suggestion
```

---

## 7 Mart 2026 Stabilization Notu

Bu turda Yiğit alanındaki stabilizasyon/hotfix çalışmaları tamamlandı:

- AI tarafından üretilen structured komutlar artık tekrar flat string'e çevrilip parse edilmez.
- Raw terminal komutları mevcut güvenlik kapısında kalır; structured AI komutları typed validation ile çalıştırılır.
- Backend session id, chat history metadata'sından ayrıştırıldı ve `MainWindow` içinde tek otorite haline getirildi.
- `BaseTool` failed-start yarışı kapatıldı; başlatılamayan process ikinci kez timeout üretmez.
- Windows native komut çalıştırmada executable resolution ve subprocess fallback eklendi.

Bu turda bilinçli olarak kodda büyütülmeyen ortak alan sorunları için `docs/kerem_handoff_issues.md` dosyasına bakın.

## Proje Yapısı

```
sentinel_root/
├── main.py                   # Production giriş noktası
├── requirements.txt          # Python bağımlılıkları
├── docker-compose.yml        # Docker servis tanımları
├── PROJECT_STRUCTURE.md      # Proje yapısı rehberi
├── README.md                 # Bu dosya
├── son_durum.md              # Durum raporu
├── data/                     # Veri klasörü
│   └── databases/            # SQLite veritabanı dosyaları
├── docker/                   # Docker yapılandırmaları
│   ├── api/                  # API servisi
│   │   └── Dockerfile
│   ├── ollama/               # Ollama LLM servisi (Qwen 2.5 3B)
│   │   ├── Dockerfile
│   │   └── setup_model.sh
│   ├── tools/                # Security tools servisi
│   │   └── Dockerfile
│   └── whiterabbitneo/       # (Legacy) WhiteRabbitNeo servisi
│       └── Dockerfile
├── docs/                     # Dokümantasyon
│   ├── AGENT_RULES.md
│   ├── entity_id_strategy.md
│   ├── execution_history_model.md
│   ├── execution_state_model.md
│   ├── sprint_roadmap.md
│   ├── sprint_3_6_plan.md
│   ├── sprint1_ready.md
│   ├── sqlite_schema.md
│   ├── ui_regression_checklist.md
│   ├── sprint_3_5_plan.md
│   └── changelog_sprint35_hotfix.md
├── models/                   # Model dosyaları ve modelfile'lar
│   ├── qwen2.5-3b-instruct-q4.gguf  # Primary (1.84 GB)
│   ├── Modelfile.qwen2.5            # SENTINEL system prompt
│   ├── Modelfile.whiterabbitneo      # Legacy modelfile
│   └── whiterabbitneo-7b-q4.gguf     # Legacy model (4.47 GB)
├── src/                      # Kaynak kodlar
│   ├── ai/                   # Yapay zeka modülleri
│   ├── application/          # Uygulama katmanı (API dahil)
│   ├── core/                 # Backend mantığı
│   ├── ui/                   # PyQt6 arayüz + i18n + settings
│   │   ├── i18n.py           # 11 dil çeviri sistemi
│   │   └── settings_dialog.py # Ayarlar diyalogu
│   ├── plugins/              # Harici araç eklentileri
│   └── tests/                # Odakli regression ve kontrat testleri
├── scripts/                  # Yardımcı scriptler
│   └── validate_ui.py
├── temp/                     # Geçici dosyalar
│  └── sentinel_safe/
└── ...
```

---

## Kurulum

### Çalışma Modu

SENTINEL AI production modda çalışır:

### Gereksinimler

- **İşletim Sistemi:** Linux (Ubuntu 20.04+ önerilir)
- **Python:** 3.10+
- **Docker:** 20.10+ & Docker Compose
- **RAM:** Minimum 4GB (8GB önerilir)
- **Disk:** ~3GB (Qwen 2.5 3B model + bağımlılıklar)

### 1. Projeyi Klonlayın

```bash
git clone https://github.com/macsclub/sentinel_ai.git
cd sentinel_ai
```

### 2. Python Ortamını Kurun

```bash
# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 3. Docker Servislerini Başlatın

```bash
# Servisleri arka planda başlat
docker-compose up -d

# İlk çalıştırmada Qwen 2.5 3B modeli indirilecek (~1.9 GB)
# İndirme durumunu izle:
docker-compose logs -f ollama-service
```

### 4. Uygulamayı Başlatın

**Çalıştırma:**
```bash
python main.py
```

## CI

Repo artık GitHub Actions ile temel doğrulamayı otomatik çalıştıracak şekilde yapılandırıldı.

CI akışı şunları yapar:

- Python 3.10 kurar
- `requirements.txt` bağımlılıklarını yükler
- Headless PyQt test ortamını hazırlar
- `python -m pytest src/tests -q` komutunu çalıştırır

Workflow dosyası:

- `.github/workflows/ci.yml`

---

## Docker Servisleri

| Servis | Port | Açıklama |
|--------|------|----------|
| `ollama-service` | 11434 | Qwen 2.5 3B LLM API (Ollama) |
| `api-service` | 8000 | Backend API (Orchestrator) |
| `tools-service` | - | Security tools (nmap, gobuster, nikto, hydra) |

### Backend Chat API (Sprint 3.6)

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/chat/session` | POST | Session oluşturur veya var olanı döndürür |
| `/api/chat/turn` | POST | Session-aware tek chat turunu işler |
| `/api/chat/history/{session_id}` | GET | Session geçmişini döndürür |

### Docker Komutları

```bash
# Servisleri başlat
docker-compose up -d

# Servisleri durdur
docker-compose down

# Logları izle
docker-compose logs -f

# Servisleri yeniden başlat
docker-compose restart

# Model cache'i temizle (dikkat: model yeniden indirilecek)
docker-compose down -v
```

---

## Kullanım

### Temel Akış

1. **Hedef Belirle** - IP adresi veya hostname gir
2. **Komut İste** - Doğal dilde ne yapmak istediğini yaz
   - Örnek: "Bu ağı tara", "Açık portları bul", "Web dizinlerini keşfet"
3. **Onayla & Çalıştır** - AI'ın ürettiği komutu incele ve onayla
4. **Sonuçları İncele** - Parse edilmiş sonuçları tabloda gör
5. **Önerileri Takip Et** - AI'ın sonraki adım önerilerini değerlendir

### Çalıştırma Akışı

- Chat üzerinden gelen AI komutları: `AI -> structured command payload -> BackendGateway.prepare_structured_command() -> TerminalView -> ProcessManager`
- Terminale elle yazılan komutlar: `User raw command -> BackendGateway.parse_command_with_risk() -> TerminalView -> ProcessManager`
- Sohbet geçmişi: UI chat id yalnızca history/display için tutulur, backend tarafındaki kalıcı bağlam `session_id` ile sürer

### Örnek Komutlar

```
Kullanıcı: "192.168.1.0/24 ağını tara"
AI → {"intent_type": "host_discovery", "target": "192.168.1.0/24", "params": {}}

Kullanıcı: "80 portundaki web sunucusunun dizinlerini bul"
AI → {"intent_type": "web_dir_enum", "target": "http://target", "params": {"port": "80"}}
```

---

## Güvenlik

### Yetki Yönetimi

- Root gerektiren işlemler için `pkexec` kullanılır
- Şifre GUI üzerinden güvenli şekilde istenir
- Yetki reddi durumunda uygulama çökmeden devam eder

### Veri Maskeleme

Mevcut sürümde sistem local-only çalışır ve varsayılan akışta veri dış servise gönderilmez.

İleride opsiyonel cloud mode açılırsa:
- IP adresleri → `[HOST_X]`
- Domain adları → `[DOMAIN_Y]`
- Hassas bilgiler otomatik maskelenir

### Güvenli XML İşleme

- `defusedxml` kütüphanesi ile XXE saldırılarına karşı koruma
- Bozuk XML dosyaları otomatik onarılır

---

## Test

```bash
# Tüm testleri çalıştır
PYTHONPATH=. pytest -q

# Belirli bir modülü test et
PYTHONPATH=. pytest src/tests/test_sprint1.py -v

# UI + i18n + optimizasyon testleri
PYTHONPATH=. pytest src/tests/test_i18n.py src/tests/test_ui_widgets.py src/tests/test_ui_features.py src/tests/test_optimizations.py -q

# Coverage raporu
PYTHONPATH=. pytest --cov=src src/tests/
```

Not: `src/tests/test_action_planner_v2.py::test_intent_resolver` canlı LLM exact-match testi olduğu için yerel modele göre oynak olabilir. 7 Mart 2026 tam koşusunda kalan tek kırık bu testti; deterministic Yiğit stabilizasyon regresyon paketi yeşil geçti.

### Test Dağılımı

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
| Diğer test dosyaları | 262 | Backend, parser, AI, resolver, entegrasyon |

---

## Build (Linux)

```bash
# Tek dosya executable oluştur
pyinstaller --onefile --name sentinel-ai --windowed main.py

# Çıktı: dist/sentinel-ai
```

---

## Katkıda Bulunma

### Branch Yapısı

```
main        ← Production (test edilmiş kod)
develop     ← Integration (ortak test)
dev_kerem   ← Kerem'in geliştirme branch'ı
dev_yigit   ← Yiğit'in geliştirme branch'ı
```

### Geliştirme Akışı

1. Kendi branch'ınızda çalışın (`dev_kerem` veya `dev_yigit`)
2. Değişiklikleri commit edin
3. `develop` branch'ına merge request açın
4. Test edin
5. `main` branch'ına merge edin

---

## Ekip

| İsim | Rol | Sorumluluklar |
|------|-----|---------------|
| **Kerem** | AI/Data/Backend | AI Orchestration, Docker, Parsing |
| **Yiğit** | System/UI/Security | PyQt6 UI, Process Manager, Security |

---

## Lisans

Bu proje, kaynak kodu görünür (source-available) bir lisans modeli ile dağıtılır.

- Ticari kullanım **yasaktır**
- Değiştirilmiş sürümlerin dağıtımı **yasaktır**
- Kodun değiştirilmeden paylaşımı, lisans metni korunarak **serbesttir**

Detaylar için [LICENSE](LICENSE) dosyasına bakın.

Model lisansları için: [MODEL_LICENSES.md](MODEL_LICENSES.md)

Üçüncü taraf bileşenler için: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

---

## İletişim

- **GitHub:** [keremalagoz/sentinel_ai](https://github.com/keremalagoz/sentinel_ai)
- **Issues:** [GitHub Issues](https://github.com/keremalagoz/sentinel_ai/issues)

---

<div align="center">

**SENTINEL AI - Güvenlik Testlerinizde Yapay Zeka Desteği**

</div>

