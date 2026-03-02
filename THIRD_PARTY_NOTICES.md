# Third Party Notices

Bu proje, üçüncü taraf paketler ve sistem araçları kullanır. Her bileşen kendi
lisansına tabidir.

## 1) Python bağımlılıkları

Kaynak: `requirements.txt`

| Paket | Lisans (yaygın beyan) | Not |
|---|---|---|
| PyQt6 | GPL-3.0 veya ticari lisans | Dağıtım senaryosunda özellikle doğrulanmalı |
| pydantic | MIT |  |
| openai | Apache-2.0 |  |
| defusedxml | PSF benzeri/PSFL uyumlu | Sürüm bazında doğrulanmalı |
| fastapi | MIT |  |
| uvicorn | BSD-3-Clause |  |

Not: Yukarıdaki lisanslar yaygın paket beyanlarına göredir. Kesin doğrulama için
kilitlenen sürüm metadata'sı (`pip show` / PyPI) release öncesi kontrol edilmelidir.

## 2) Docker base image ve servisler

| Bileşen | Kaynak | Not |
|---|---|---|
| python:3.11-slim | `docker/api/Dockerfile` | Debian tabanlı, çoklu lisans içerir |
| ubuntu:22.04 | `docker/tools/Dockerfile` | Ubuntu paket lisansları paket bazlıdır |
| ollama/ollama:latest | `docker/ollama/Dockerfile`, `docker/whiterabbitneo/Dockerfile` | Tag sabitlenmeden lisans/SBOM takibi zorlaşır |

## 3) Tools container içinde kurulan paketler

Kaynak: `docker/tools/Dockerfile`

Kurulan araçlar: `nmap`, `gobuster`, `nikto`, `dirb`, `hydra`, `sqlmap`,
`netcat-openbsd`, `curl`, `wget`, `whois`, `dnsutils`, `iputils-ping`,
`net-tools`, `python3`, `python3-pip`.

Bu araçların lisansları farklıdır (GPL/BSD/Apache vb.). Konteyner içinde ilgili
lisans metinleri genellikle `/usr/share/doc/<paket>/copyright` altında bulunur.

## 4) Genel uyum notu

- Bu proje lisansı, üçüncü taraf bileşen lisanslarının yerine geçmez.
- Yeniden dağıtımda, ilgili üçüncü taraf lisans metinleri ve atıf şartları korunmalıdır.
- Özellikle `PyQt6` ve güvenlik araçları için dağıtım modeli (source/binary/container)
	bazında ek yükümlülük doğabilir.
