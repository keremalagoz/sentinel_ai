# SENTINEL AI - Proje Durum Raporu

**Tarih:** 26 Şubat 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0-2 [OK]

- Proje altyapısı, Docker servisleri ve temel UI/Core iskeleti tamamlandı.
- Action Planner v2.1 deterministic akışı devreye alındı.
- Local AI (WhiteRabbitNeo/Ollama) ile intent çözümleme stabilize edildi.

---

## Mevcut Durum (Özet)

- Mimari: Local-only LLM + deterministic tool execution
- Kararlılık: Queue/backpressure, per-tool limit, retry/backoff aktif
- Güvenilirlik: Registry drift guard (startup + test) aktif
- Gözlemlenebilirlik: Runtime telemetry (`queue_wait_ms`, `tool_run_ms`) mevcut
- Test: Full suite **112 passed**

---

## Docker Servisleri (Beklenen)

| Container | Port | İçerik |
|-----------|------|--------|
| sentinel-whiterabbitneo | 8002 | WhiteRabbitNeo AI (Ollama) |
| sentinel-api | 8000 | API Backend |
| sentinel-tools | - | Nmap, Gobuster, Nikto, Hydra |

---

## Aktif Sprint: Sprint 3.6 (Optimizasyon ve Platform Hazırlığı)

> Sprint 3.5 tamamlandı. Kapsamlı audit raporu sonuçlarına göre Sprint 3.6 açıldı.  
> Detaylı plan: `docs/sprint_3_6_plan.md`

### Sprint 3.6 Özet Hedefler

| Track | Odak | Görev Sayısı | Sorumlu |
|-------|------|--------------|---------|
| **A** | Kritik Bugfix (P0) | 4 | Kerem + Yiğit |
| **B** | Linux Platform Uyumu | 7 | Yiğit + Kerem |
| **C** | AI Ölçeklenme Altyapısı | 4 | Kerem |
| **D** | Kod Kalitesi / Teknik Borç | 4 | Kerem + Yiğit |

---

## Tamamlanan Sprint: Sprint 3.5 (Stabilizasyon / Sertleştirme)

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

- Full test suite: **112 passed**
- P0 doğrulama: `scripts/p0_validation.py --with-pytest` başarılı

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
