# SENTINEL AI v0.4.0-alpha

> Ilk etiketli surum | 11 Mart 2026

Local AI destekli siber guvenlik test araci. Dogal dilde yazdiginiz komutlari
guvenlik test araclarinin parametrelerine cevirir ve calistirir.

---

## One Cikanlar

- **Local AI:** Qwen 2.5 3B Instruct (Ollama) — verileriniz cihazinizdan cikmaz
- **2 Asamali Intent Resolution:** %95 intent dogrulugu (200 bilingual test case)
- **16 Intent Tipi:** port_scan, host_discovery, web_dir_enum, sql_injection, brute_force_ssh, ssl_scan, dns_lookup, whois_lookup, vuln_scan, web_vuln_scan, subdomain_enum, web_app_scan, service_detection, info_query, unknown, needs_clarification
- **8 Guvenlik Araci:** nmap, gobuster, nikto, hydra, sqlmap, dirb, whois, dig
- **11 Dil:** EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI
- **Modern UI:** PyQt6 masaustu uygulamasi, responsive terminal, ayarlar diyalogu

## Benchmark Sonuclari

| Metrik | Skor |
|--------|------|
| Intent Accuracy | %95.0 |
| Param Accuracy | %96.0 |
| Target Extraction | %86.0 |
| Exact Match | %76.0 |
| Clarification Accuracy | %98.0 |

## Gereksinimler

- Python 3.10+
- Docker 20.10+ ve Docker Compose v2+
- 4 GB RAM (8 GB onerilen)
- ~3 GB disk (model + bagimliliklar)

## Hizli Baslangic

```bash
git clone https://github.com/macsclub/sentinel_ai.git
cd sentinel_ai
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker-compose up -d        # Ilk calistirmada ~1.9 GB model indirilir
python main.py              # PyQt6 GUI baslar
```

Detayli kurulum: [docs/INSTALL.md](docs/INSTALL.md)

## Bilinen Kisitlamalar

- Guvenlik araclari yalnizca Docker container icinde calisir
- Windows'ta Docker Desktop (WSL2) zorunludur
- Standalone executable bu surumde bulunmaz
- GPU olmadan LLM yanit suresi 2-5 saniye

## Lisans

Source-available lisans. Detaylar icin [LICENSE](LICENSE) dosyasina bakin.
Model lisanslari: [MODEL_LICENSES.md](MODEL_LICENSES.md)
