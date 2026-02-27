# SENTINEL AI - Proje Durum Raporu

**Tarih:** 28 Şubat 2026  
**Ekip:** Kerem (AI/Data/Backend) & Yiğit (System/UI/Security)

---

## Tamamlanan Sprintler

### Sprint 0-2 [OK]

- Proje altyapısı, Docker servisleri ve temel UI/Core iskeleti tamamlandı.
- Action Planner v2.1 deterministic akışı devreye alındı.
- Local AI (WhiteRabbitNeo → Qwen 2.5 3B) ile intent çözümleme stabilize edildi.

---

## Mevcut Durum (Özet)

- Mimari: Local-only LLM (Qwen 2.5 3B / Ollama) + deterministic tool execution
- Model: Qwen 2.5 3B Instruct Q4_K_M (1.84 GB, 29+ dil, 151K vocab)
- Intent Pipeline: Keyword Pre-Filter → Stage 1 (5 kategori) → Stage 2 (16 intent)
- Benchmark: %100 doğruluk (30/30, hierarchical mod)
- Kararlılık: Queue/backpressure, per-tool limit, retry/backoff aktif
- Güvenilirlik: Registry drift guard (startup + test) aktif
- Gözlemlenebilirlik: Runtime telemetry (`queue_wait_ms`, `tool_run_ms`) mevcut
- Test: Full suite **242 passed**

---

## Docker Servisleri (Beklenen)

| Container | Port | İçerik |
|-----------|------|--------|
| sentinel-ollama | 11434 | Qwen 2.5 3B AI (Ollama) |
| sentinel-api | 8000 | API Backend |
| sentinel-tools | - | Nmap, Gobuster, Nikto, Hydra |

---

## Tamamlanan Sprint: Sprint 3.6 (Optimizasyon ve Platform Hazırlığı) [OK]

> Sprint 3.5 tamamlandı. Kapsamlı audit raporu sonuçlarına göre Sprint 3.6 açıldı ve tamamlandı.  
> Detaylı plan: `docs/sprint_3_6_plan.md`  
> Merge: develop'a merge edildi (commit 02e352c)

### Sprint 3.6 Özet Hedefler

| Track | Odak | Görev Sayısı | Sorumlu | Durum |
|-------|------|--------------|---------|-------|
| **A** | Kritik Bugfix (P0) | 4/4 | Kerem + Yiğit | [OK] |
| **B** | Linux Platform Uyumu | 7/7 | Yiğit + Kerem | [OK] |
| **C** | AI Ölçeklenme Altyapısı | 7/7 | Kerem | [OK] |
| **D** | Kod Kalitesi / Teknik Borç | 4/4 | Kerem + Yiğit | [OK] |

---

## Tamamlanan Sprint: Sprint 3.5 (Stabilizasyon / Sertleştirme)

### Sprint 3: Güvenlik, Yetki ve Temizlik

| Görev | Sorumlu | Durum | Açıklama |
|-------|---------|-------|----------|
| ExecutionManager | Yiğit | [OK] | Docker/Native mod yönetimi & Pkexec logic |
| Secure Cleaner (cleaner.py) | Yiğit | [OK] | Güvenli dosya temizleme, Whitelist, Shredding |
| Input Validation | Yiğit | [OK] | IP/Domain validasyonu, Shell injection check |
| ProcessManager Update | Yiğit | [OK] | Yeni core modüllerle entegrasyon |
| UI Security Indicators | Yiğit | [BACKLOG] | Terminalde root uyarisi — Sprint 3'ten kalan |
| Settings Menu (Security) | Yiğit | [BACKLOG] | Temizlik sikligi vb. — Sprint 3'ten kalan |

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

- Full test suite: **242 passed** (Sprint 3.7 sonrası: +57 yeni test)
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

## Tamamlanan Sprint: Sprint 3.7 (Hybrid LLM Motoru) [OK]

> Tasarım dokümanı: `docs/hierarchical_intent_design.md`  
> Temel: Sprint 3.6 Track C altyapısı

| # | Görev | Sorumlu | Durum |
|---|-------|---------|-------|
| 3.7.1 | CategoryResult + SENTINEL_CATEGORIES modeli | Kerem | [OK] |
| 3.7.2 | HierarchicalResolver base class | Kerem | [OK] |
| 3.7.3 | Stage 1 — Category Resolver | Kerem | [OK] |
| 3.7.4 | Stage 2 — Sub-Intent Resolver | Kerem | [OK] |
| 3.7.5 | KeywordPreFilter bypass entegrasyonu | Kerem | [OK] |
| 3.7.6 | Orchestrator feature flag | Kerem | [OK] |
| 3.7.7 | Flat vs Hierarchical benchmark | Kerem | [OK] |
| 3.7.8 | Unit testler (57 test) | Kerem | [OK] |
| 3.7.9 | Model değişimi: WhiteRabbitNeo 7B → Qwen 2.5 3B | Kerem | [OK] |
| 3.7.10 | Docker/doküman güncellemesi | Kerem | [OK] |

---

## Sıradaki Adımlar

1. **Sprint 4** — Veri Adaptasyonu (`models.py` + `nmap_adapter.py`)
2. **Sprint 3 backlog** — UI Security Indicators, Settings Menu (Yiğit, paralel)
3. **Sprint 5** — Öneri Motoru
4. **Runtime telemetry UI** — Tool kuyruk/süre gösterimi (backlog)

---

## Git Durumu

| Branch | Son Durum |
|--------|-----------|
| main | Sprint 0 + 1 |
| develop | Sprint 0 → 3.6 dahil (merge commit 02e352c) |
| dev_kerem | Sprint 0 → 3.7 dahil |
| dev_yigit | Sprint 0 + 1 + 2 + 3 (core) |

---

*Son Güncelleme: 28 Şubat 2026*
