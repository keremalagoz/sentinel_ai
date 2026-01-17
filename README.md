# 🛡️ SENTINEL AI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Llama](https://img.shields.io/badge/Llama_3-Local_AI-FF6F00?style=for-the-badge&logo=meta&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Hibrit AI Destekli Güvenlik Test Aracı**

*Local + Cloud AI | PyQt6 GUI | Docker Backend | Linux Target*

</div>

---

## 📖 Proje Hakkında

SENTINEL AI, siber güvenlik testlerini yapay zeka destekli komutlarla otomatikleştiren bir masaüstü uygulamasıdır. Hibrit AI mimarisi sayesinde hem yerel (Llama 3) hem de bulut (OpenAI GPT-4) yapay zeka modellerini kullanarak güvenlik taramalarını yönetir.

### ✨ Özellikler

- 🤖 **Hibrit AI Motoru** - Basit görevler için Local Llama 3, karmaşık senaryolar için Cloud AI
- 🖥️ **Modern PyQt6 Arayüzü** - Donmayan, responsive terminal ve sonuç görüntüleme
- 🐳 **Docker Altyapısı** - İzole ve taşınabilir servis mimarisi
- 🔒 **Güvenli Yetki Yönetimi** - Pkexec ile şifresiz root işlemleri
- 📊 **Akıllı Parsing** - Nmap XML çıktılarını otomatik parse ve tablo görüntüleme
- 💡 **Öneri Motoru** - Bulgulara göre sonraki adım önerileri
- 🔌 **Plugin Sistemi** - Genişletilebilir araç desteği

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL AI                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │   PyQt6     │    │   AI        │    │   Process   │          │
│  │   GUI       │◄──►│ Orchestrator│◄──►│   Manager   │          │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘          │
│                            │                   │                 │
│         ┌──────────────────┼───────────────────┤                 │
│         ▼                  ▼                   ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │ Local LLM   │    │ Cloud API   │    │ Linux       │          │
│  │ (Llama 3)   │    │ (OpenAI)    │    │ Tools       │          │
│  │ Port: 8001  │    │             │    │ (nmap, etc) │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Proje Yapısı

```
sentinel_root/
├── 📂 src/                      # Kaynak kodlar
│   ├── 📂 core/                 # Backend mantığı
│   │   ├── 📂 adapters/         # Araç çıktı parserleri
│   │   │   └── nmap_adapter.py  # Nmap XML parser
│   │   ├── process_manager.py   # QProcess wrapper
│   │   ├── models.py            # Pydantic veri modelleri
│   │   ├── cleaner.py           # Güvenli dosya temizleyici
│   │   ├── interfaces.py        # Plugin arayüzleri
│   │   └── plugin_manager.py    # Plugin yükleyici
│   ├── 📂 ui/                   # PyQt6 arayüz dosyaları
│   │   ├── terminal_view.py     # Terminal widget
│   │   └── results_view.py      # Sonuç tablosu
│   ├── 📂 ai/                   # Yapay zeka modülleri
│   │   ├── schemas.py           # JSON şemaları
│   │   ├── orchestrator.py      # AI karar motoru
│   │   └── masking.py           # Veri maskeleme
│   ├── 📂 plugins/              # Harici araç eklentileri
│   └── 📂 tests/                # Unit testler
├── 📂 docker/                   # Docker yapılandırmaları
│   ├── 📂 llama/                # Llama 3 servisi
│   │   ├── Dockerfile
│   │   └── pull_model.sh
│   └── 📂 api/                  # API servisi
│       └── Dockerfile
├── 📂 docs/                     # Dokümantasyon
├── 📂 temp/                     # Session logları (gitignore)
├── main.py                      # Uygulama giriş noktası
├── requirements.txt             # Python bağımlılıkları
├── docker-compose.yml           # Docker servis tanımları
├── .env.example                 # Ortam değişkenleri şablonu
└── README.md                    # Bu dosya
```

---

## 🚀 Kurulum

### İki Çalışma Modu

SENTINEL AI iki farklı modda çalışabilir:

| Mod | Dosya | Kullanım Durumu | RAM | LLM |
|-----|-------|-----------------|-----|-----|
| **Production** | `main.py` | Gerçek güvenlik testleri | ~8GB | Docker Ollama |
| **Developer** | `main_developer.py` | UI/AI geliştirme | ~2GB | Native Ollama |

> 💡 **Developer Mode:** Sadece UI ve AI geliştirme için optimize edilmiştir. Komutlar gerçekte çalıştırılmaz, mock çıktı gösterilir. WSL/Docker kapalı olduğu için ~6GB RAM tasarrufu sağlar.

### Gereksinimler (Production Mode)

- **İşletim Sistemi:** Linux (Ubuntu 20.04+ önerilir)
- **Python:** 3.11+
- **Docker:** 20.10+ & Docker Compose
- **RAM:** Minimum 8GB (Llama 3 için 16GB önerilir)
- **Disk:** 10GB+ (Model indirme için)

### Gereksinimler (Developer Mode)

- **İşletim Sistemi:** Windows/Linux/macOS
- **Python:** 3.11+
- **Ollama:** Native kurulum gerekli
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

# İlk çalıştırmada Llama 3 modeli indirilecek (~4.7GB)
# İndirme durumunu izle:
docker-compose logs -f llama-service
```

### 5. Uygulamayı Başlatın

**Production Mode (Gerçek Testler):**
```bash
python main.py
```

**Developer Mode (UI/AI Geliştirme):**
```bash
python main_developer.py
```

---

## 🔧 Developer Mode Kurulumu

Developer mode, sadece UI ve AI geliştirmesi için optimize edilmiştir. Docker/WSL kapalı çalıştığı için ~6GB RAM tasarrufu sağlar.

### 1. Native Ollama Kurulumu

**Windows:**
```bash
# https://ollama.com/download adresinden indir ve kur
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

### 2. WhiteRabbitNeo Modelini İndir

```bash
ollama pull whiterabbitneo
```

### 3. Ollama'yı Başlat (Otomatik başlamazsa)

```bash
ollama serve
```

### 4. Developer Mode'u Çalıştır

```bash
python main_developer.py
```

### Developer Mode Özellikleri

✅ **Native Ollama Bağlantısı** - Docker'a gerek yok  
✅ **RAM Tasarrufu** - WSL kapalı (~6GB tasarruf)  
✅ **Hızlı LLM Yanıt** - Network overhead yok (2-3x hızlı)  
✅ **Mock Execution** - Komutlar çalıştırılmaz, güvenli  
✅ **Action Planner Testi** - Intent, Tool, Command çıktılarını görüntüle  
✅ **Policy Gate** - Production ile aynı mantık  

⚠️ **UYARI:** Developer mode gerçek güvenlik testleri için kullanılamaz!

---

## 🐳 Docker Servisleri

| Servis | Port | Açıklama |
|--------|------|----------|
| `llama-service` | 8001 | Local Llama 3 LLM API |
| `api-service` | 8000 | Backend API (Orchestrator) |

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

## 💻 Kullanım

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
AI → {"tool": "nmap", "arguments": ["-sn", "192.168.1.0/24"]}

Kullanıcı: "80 portundaki web sunucusunun dizinlerini bul"
AI → {"tool": "gobuster", "arguments": ["dir", "-u", "http://target", "-w", "wordlist.txt"]}
```

---

## 🔒 Güvenlik

### Yetki Yönetimi

- Root gerektiren işlemler için `pkexec` kullanılır
- Şifre GUI üzerinden güvenli şekilde istenir
- Yetki reddi durumunda uygulama çökmeden devam eder

### Veri Maskeleme

Cloud AI'ya gönderilen verilerde:
- IP adresleri → `[HOST_X]`
- Domain adları → `[DOMAIN_Y]`
- Hassas bilgiler otomatik maskelenir

### Güvenli XML İşleme

- `defusedxml` kütüphanesi ile XXE saldırılarına karşı koruma
- Bozuk XML dosyaları otomatik onarılır

---

## 🧪 Test

```bash
# Tüm testleri çalıştır
pytest src/tests/

# Belirli bir modülü test et
pytest src/tests/test_process_manager.py -v

# Coverage raporu
pytest --cov=src src/tests/
```

---

## 📦 Build (Linux)

```bash
# Tek dosya executable oluştur
pyinstaller --onefile --name sentinel-ai --windowed src/main.py

# Çıktı: dist/sentinel-ai
```

---

## 🤝 Katkıda Bulunma

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

## 👥 Ekip

| İsim | Rol | Sorumluluklar |
|------|-----|---------------|
| **Kerem** | AI/Data/Backend | AI Orchestration, Docker, Parsing |
| **Yiğit** | System/UI/Security | PyQt6 UI, Process Manager, Security |

---

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 📞 İletişim

- **GitHub:** [macsclub/sentinel_ai](https://github.com/macsclub/sentinel_ai)
- **Issues:** [GitHub Issues](https://github.com/macsclub/sentinel_ai/issues)

---

<div align="center">

**⚔️ SENTINEL AI - Güvenlik Testlerinizde Yapay Zeka Desteği ⚔️**

</div>

