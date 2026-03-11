# SENTINEL AI v0.4.0-alpha — Kurulum Kilavuzu

> Tarih: 11 Mart 2026 | Ilk etiketli surum

---

## Gereksinimler

| Bilesen | Minimum | Onerilen |
|---------|---------|----------|
| **Isletim Sistemi** | Windows 10+ veya Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **Python** | 3.10 | 3.11+ |
| **Docker** | 20.10+ | 24.0+ |
| **Docker Compose** | v2.0+ | v2.20+ |
| **RAM** | 4 GB | 8 GB+ |
| **Disk** | 3 GB | 5 GB+ |
| **GPU (opsiyonel)** | - | NVIDIA (CUDA destekli) |

> **Not:** Docker, guvenlik araclari (nmap, gobuster, nikto, vb.) ve LLM servisi icin zorunludur.

---

## Hizli Kurulum (5 Adim)

### 1. Repoyu klonlayin

```bash
git clone https://github.com/macsclub/sentinel_ai.git
cd sentinel_ai
```

### 2. Python ortamini kurun

**Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Docker servislerini baslatin

```bash
docker-compose up -d
```

Ilk calistirmada Qwen 2.5 3B modeli indirilecektir (~1.9 GB).
Indirme durumunu izlemek icin:

```bash
docker-compose logs -f ollama-service
```

"SENTINEL AI - Model Ready!" mesajini gorene kadar bekleyin.

### 4. Servislerin hazir oldugunu dogrulayin

```bash
# Ollama LLM servisi
curl http://localhost:8002/api/tags

# API Backend
curl http://localhost:8000/health
```

### 5. Uygulamayi baslatin

```bash
python main.py
```

PyQt6 penceresi acilacaktir. Chat alanina dogal dilde guvenlik komutlari yazabilirsiniz.

---

## Ornek Kullanim

```
Kullanici: "192.168.1.0/24 agini tara"
Sentinel: nmap -sn 192.168.1.0/24

Kullanici: "80 portundaki web sunucusunun dizinlerini bul"
Sentinel: gobuster dir -u http://target -w /usr/share/wordlists/dirb/common.txt

Kullanici: "nmap nedir?"
Sentinel: [Bilgi yaniti — komut uretmez]
```

---

## Docker Servisleri

| Servis | Port | Aciklama |
|--------|------|----------|
| `ollama-service` | 8002 | Qwen 2.5 3B LLM (Ollama) |
| `api-service` | 8000 | Backend API (FastAPI) |
| `tools-service` | - | Guvenlik araclari container |

### Servis Yonetimi

```bash
# Servisleri durdur
docker-compose down

# Servisleri yeniden baslat
docker-compose restart

# Loglari izle
docker-compose logs -f

# Model cache temizle (model yeniden indirilir)
docker-compose down -v
```

---

## GPU Destegi (Opsiyonel)

NVIDIA GPU varsa LLM yanit suresi 3-5x hizlanir.

```bash
# NVIDIA Container Toolkit kurulumu (Ubuntu)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

GPU destegi `docker-compose.yml` icinde zaten yapilandirilmistir.
GPU yoksa CPU modunda otomatik calisir.

---

## Testler

```bash
# Tum testleri calistir (LLM testleri haric)
PYTHONPATH=. pytest -m "not llm" -q

# LLM entegrasyon testleri dahil
PYTHONPATH=. pytest --run-llm -q

# Belirli bir test dosyasi
PYTHONPATH=. pytest src/tests/test_tool_commands.py -v
```

---

## Sorun Giderme

### Docker servisi baslamiyor
```bash
# Container durumlarini kontrol et
docker-compose ps

# Ollama loglarini incele
docker-compose logs ollama-service
```

### "Model not found" hatasi
Model indirme tamamlanmamis olabilir. Bekleyin veya:
```bash
docker-compose restart ollama-service
docker-compose logs -f ollama-service
```

### PyQt6 penceresi acilmiyor (Linux)
```bash
# X11/Wayland kutuphanelerini kurun
sudo apt install libxcb-xinerama0 libxkbcommon-x11-0 libegl1
```

### Windows'ta "docker" komutu bulunamadi
Docker Desktop'in kurulu ve calisir durumda oldugunu dogrulayin.
PowerShell'i yonetici olarak acip `docker --version` komutunu calistirin.

---

## Bilinen Kisitlamalar (v0.4.0-alpha)

- Guvenlik araclari (nmap, gobuster, vb.) yalnizca Docker container icinde calisir
- Windows'ta Docker Desktop (WSL2) zorunludur
- Standalone executable (.exe / binary) bu surumde bulunmaz
- info_query / unknown intent ayrimi bazi edge case'lerde zayif olabilir

---

## Sonraki Surum (v0.5.0)

- Sonuc modelleme ve adapter katmani (Sprint 4)
- PyInstaller standalone build pipeline
- Performans iyilestirmeleri
