# Changelog

Tum onemli degisiklikler bu dosyada belgelenir.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versiyonlama: [Semantic Versioning 2.0.0](https://semver.org/)

---

## [v0.4.0-alpha] — 2026-03-11

Ilk etiketli surum. Local AI destekli guvenlik test araci.

### Eklenenler

**AI Pipeline**
- 2 asamali hierarchical intent resolution (Category -> Sub-Intent)
- Keyword pre-filter ile LLM bypass (yuksek confidence pattern'lar)
- Param extractor modulu (regex tabanli parametre cikartma)
- Implicit param pruning (hallucination onleme)
- DNS/WHOIS hard-override mekanizmasi
- 16 intent tipi destegi (host_discovery, port_scan, web_dir_enum, sql_injection, vb.)

**Backend**
- Session/turn tabanli multi-turn chat hafizasi (Sprint 3.6)
- Structured AI command execution pipeline
- Backend-owned session flow (UI history id ve backend session id ayrimi)
- Typed argument validation (URL, query, form payload)
- FastAPI REST API (session create, chat turn, history endpoints)

**UI**
- Modern PyQt6 masaustu arayuzu
- 11 dil destegi (EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI) — 97 ceviri anahtari
- Ayarlar diyalogu (dil, font boyutu, oturum temizleme, guvenlik politikasi)
- Esnek yerlesim (Chat/Terminal pozisyon degistirme)
- Status bar uzerinde kuyruk/bekleme/calistirma metrikleri

**Altyapi**
- Docker servis mimarisi (Ollama LLM + API Backend + Security Tools)
- Qwen 2.5 3B Instruct model entegrasyonu (1.9 GB, 29+ dil)
- SQLite backend (execution history, chat sessions)
- Benchmark regression gate (CI destegi)
- LLM test izolasyonu (@pytest.mark.llm + --run-llm flag)
- 98 regression testi

**Guvenlik Araclari (Docker Container)**
- nmap (port scan, host discovery, service detection)
- gobuster (web directory enumeration)
- nikto (web vulnerability scan)
- hydra (brute force)
- sqlmap (SQL injection)
- dirb (directory brute force)
- whois, dig (DNS/domain reconnaissance)

### Benchmark Sonuclari (200 bilingual test case)

| Metrik | Skor |
|--------|------|
| Intent Accuracy | %95.0 |
| Param Accuracy | %96.0 |
| Target Extraction | %86.0 |
| Exact Match | %76.0 |

### Bilinen Kisitlamalar

- Guvenlik araclari Docker container gerektirir (native Windows destegi yok)
- GPU olmadan LLM yanit suresi 2-5 saniye arasinda degisebilir
- info_query vs unknown intent ayrimi bazi edge case'lerde zayif
- PyInstaller standalone build henuz hazir degil (v0.5.0-beta planli)

---

*Bu dosya v0.4.0-alpha ile baslatilmistir. Onceki sprintler icin `docs/sprint_roadmap.md` dosyasina bakin.*
