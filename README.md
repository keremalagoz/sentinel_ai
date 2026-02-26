# SENTINEL AI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![WhiteRabbitNeo](https://img.shields.io/badge/WhiteRabbitNeo-Local_AI-FF6F00?style=for-the-badge&logo=meta&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Local AI Destekli Güvenlik Test Aracı**

*Local AI | PyQt6 GUI | Docker Backend | Linux Target*

</div>

---

## Proje Hakkında

SENTINEL AI, siber güvenlik testlerini yapay zeka destekli komutlarla otomatikleştiren bir masaüstü uygulamasıdır. Mevcut sürümde local AI (WhiteRabbitNeo/Ollama) ile güvenlik taramalarını yönetir.

### Özellikler

- **Local AI Motoru** - WhiteRabbitNeo/Ollama tabanlı intent çözümleme
- **Modern PyQt6 Arayüzü** - Donmayan, responsive terminal ve sonuç görüntüleme
- **Docker Altyapısı** - İzole ve taşınabilir servis mimarisi
- **Güvenli Yetki Yönetimi** - Pkexec ile şifresiz root işlemleri
- **Deterministik Çalıştırma** - Intent -> Tool -> Command zinciri
- **Çalışma Zamanı Sertleştirme** - Queue/backpressure, per-tool limit, timeout/retry

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
│  ┌─────────────┐                      ┌─────────────┐          │
│  │ Local LLM   │                      │ Linux       │          │
│  │ (WhiteRabbitNeo)                   │ Tools       │          │
│  │ Port: 8002  │                      │ (nmap, etc) │          │
│  └─────────────┘                      └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Proje Yapısı

```
sentinel_root/
├── main.py                   # Production giriş noktası
├── api_server.py             # API modunda komut üretimi
├── requirements.txt          # Python bağımlılıkları
├── docker-compose.yml        # Docker servis tanımları
├── .env                      # Çevre değişkenleri
├── .env.example              # .env şablonu
├── PROJECT_STRUCTURE.md      # Proje yapısı rehberi
├── README.md                 # Bu dosya
├── son_durum.md              # Durum raporu
├── data/                     # Veri klasörü
├── docker/                   # Docker yapılandırmaları
│   ├── api/                  # API servisi
│   │   └── Dockerfile
│   ├── tools/                # Security tools servisi
│   │   └── Dockerfile
│   └── whiterabbitneo/       # WhiteRabbitNeo LLM servisi
│       └── Dockerfile
├── docs/                     # Dokümantasyon
│   ├── AGENT_RULES.md
│   ├── entity_id_strategy.md
│   ├── execution_history_model.md
│   ├── execution_state_model.md
│   ├── sprint_roadmap.md
│   ├── sprint1_ready.md
│   └── sqlite_schema.md
├── models/                   # Model dosyaları ve modelfile'lar
│   ├── model1.gguf
│   ├── model2.gguf
│   ├── Modelfile.model1
│   ├── Modelfile.model2
│   ├── Modelfile.whiterabbitneo
│   └── whiterabbitneo-7b-q4.gguf
├── src/                      # Kaynak kodlar
│   ├── ai/                   # Yapay zeka modülleri
│   ├── core/                 # Backend mantığı
│   ├── ui/                   # PyQt6 arayüz dosyaları
│   ├── plugins/              # Harici araç eklentileri
│   └── tests/                # Unit testler
├── temp/                     # Geçici dosyalar
│  └── sentinel_safe/
├── sentinel_production.db    # Production veritabanı
├── sentinel_dev.db           # Developer mode veritabanı
└── sentinel_state.db         # Test/default veritabanı
```

---

## Kurulum

### Çalışma Modu

SENTINEL AI production modda çalışır:

### Gereksinimler

- **İşletim Sistemi:** Linux (Ubuntu 20.04+ önerilir)
- **Python:** 3.11+
- **Docker:** 20.10+ & Docker Compose
- **RAM:** Minimum 8GB (WhiteRabbitNeo için 16GB önerilir)
- **Disk:** 10GB+ (Model indirme için)
- **RAM:** Minimum 4GB (Native Ollama için 8GB önerilir)
- **Disk:** ~5GB (Model için)

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

### 3. Ortam Değişkenlerini Ayarlayın

```bash
# .env dosyasını oluştur
cp .env.example .env

# API anahtarını düzenle
nano .env
```

### 4. Docker Servislerini Başlatın

```bash
# Servisleri arka planda başlat
docker-compose up -d

# İlk çalıştırmada WhiteRabbitNeo modeli indirilecek
# İndirme durumunu izle:
docker-compose logs -f whiterabbitneo-service
```

### 5. Uygulamayı Başlatın

**Çalıştırma:**
```bash
python main.py
```

---

## Docker Servisleri

| Servis | Port | Açıklama |
|--------|------|----------|
| `whiterabbitneo-service` | 8002 | WhiteRabbitNeo LLM API (Ollama) |
| `api-service` | 8000 | Backend API (Orchestrator) |
| `tools-service` | - | Security tools (nmap, gobuster, nikto, hydra) |

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
pytest src/tests/

# Belirli bir modülü test et
pytest src/tests/test_process_manager.py -v

# Coverage raporu
pytest --cov=src src/tests/
```

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

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## İletişim

- **GitHub:** [keremalagoz/sentinel_ai](https://github.com/keremalagoz/sentinel_ai)
- **Issues:** [GitHub Issues](https://github.com/keremalagoz/sentinel_ai/issues)

---

<div align="center">

**SENTINEL AI - Güvenlik Testlerinizde Yapay Zeka Desteği**

</div>

