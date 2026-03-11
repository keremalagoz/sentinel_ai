# SENTINEL AI — Versiyonlama Stratejisi

**Oluşturulma Tarihi:** 11 Mart 2026  
**Yürürlük:** v0.4.0-alpha (İlk Etiketli Sürüm)

---

## 1) Versiyon Şeması

[Semantic Versioning 2.0.0](https://semver.org/) standardı kullanılır.

```
v{MAJOR}.{MINOR}.{PATCH}[-{pre-release}]
```

| Segment | Değişim Kuralı | Örnek |
|---------|---------------|-------|
| **MAJOR** | Geriye uyumsuz API/mimari kırılma | v1.0.0 → v2.0.0 |
| **MINOR** | Geriye uyumlu yeni özellik / sprint milestone | v0.4.0 → v0.5.0 |
| **PATCH** | Bug fix, hotfix, küçük iyileştirme | v0.4.0 → v0.4.1 |
| **pre-release** | Olgunluk etiketi: `alpha` → `beta` → `rc.N` | v0.4.0-alpha |

### Pre-release Etiketleri

| Etiket | Anlam | Kriter |
|--------|-------|--------|
| `alpha` | Aktif geliştirme, özellik eksik, API değişebilir | Çekirdek akış çalışıyor, bilinen eksikler var |
| `beta` | Özellik tamam, stabilite testi devam ediyor | Tüm planlı özellikler mevcut, kullanıcı testi yapılıyor |
| `rc.N` | Sürüm adayı, yalnızca kritik bug fix kabul edilir | Yeni özellik yok, sadece final düzeltmeler |
| *(boş)* | Kararlı sürüm (stable release) | Production hazır |

---

## 2) MAJOR 0 Dönemi (Pre-Stable)

Proje `v1.0.0`'a ulaşana kadar **MAJOR = 0** kalır. Bu dönemde:

- MINOR artışları büyük özellik/sprint milestone'larını temsil eder
- PATCH artışları bug fix ve hotfix'leri karşılar
- API kontratı herhangi bir MINOR artışında kırılabilir (pre-1.0 SemVer kuralı)
- Her MINOR sürüm kendi pre-release yaşam döngüsüne sahiptir (`alpha` → `beta` → `rc` → stable)

---

## 3) Sprint → Versiyon Eşleştirmesi

### Retroaktif Eşleştirme (Tarihsel)

Geçmiş sprint'ler taglanmadı, ancak mantıksal eşleştirme şu şekildedir:

| Versiyon | Sprint(ler) | Milestone | Tarih |
|----------|------------|-----------|-------|
| *(v0.1.0)* | Sprint 0 + 1 | Altyapı + Süreç Motoru + SQLite | — |
| *(v0.2.0)* | Sprint 2 | AI Karar Katmanı (Intent → Tool → Command) | — |
| *(v0.3.0)* | Sprint 3 – 3.5 v2 | Güvenlik, Stabilizasyon, Optimizasyon, UI/i18n, Tool Konsolidasyonu | — |
| **v0.4.0-alpha** | Sprint 3.6 – 3.7.1 | Backend Chat, Hierarchical Intent, AI Accuracy Hardening | **11 Mart 2026** |

### İleriye Dönük Plan

| Versiyon | Hedef Sprint | İçerik | Tahmini Pre-release |
|----------|-------------|--------|---------------------|
| v0.4.x | — | v0.4.0 sonrası hotfix/patch'ler | — |
| v0.5.0-alpha | Sprint 4 | Veri Adaptasyonu + Sonuç Modelleri | alpha → beta |
| v0.6.0-alpha | Sprint 5 | Öneri Motoru + Maskeleme | alpha → beta |
| v0.7.0-alpha | Sprint 6 | Plugin Sistemi + Linux Build | alpha → beta → rc |
| **v1.0.0** | Post-Sprint 6 | İlk Kararlı Sürüm | rc.1 → rc.2 → stable |

---

## 4) v0.4.0-alpha — İlk Sürüm Kapsamı

Bu, projenin ilk resmi etiketli sürümüdür.

### Dahil Olan Özellikler

- **Altyapı:** Docker compose, Python bağımlılık sistemi, SQLite backend
- **Süreç Motoru:** QProcess çalıştırma, execution history, parser framework
- **AI Karar Katmanı:** 2 aşamalı hierarchical intent resolution (Qwen 2.5 3B)
- **Güvenlik:** Input validation, secure cleaner, pkexec entegrasyonu, shell injection koruması
- **UI:** PyQt6 arayüz, 11 dil desteği (i18n), ayarlar diyalogu, layout swap
- **Performans:** Debounce I/O, cache, regex pre-compile, QSS sabitleri
- **Backend Chat:** Session/turn tabanlı multi-turn conversation memory
- **Tool Desteği:** 15+ güvenlik aracı (nmap, whois, ssl scan, sqlmap, hydra vb.)
- **AI Doğruluk:** Intent %95, Params %96, Target %86, Exact Match %76 (200 vakalık benchmark)
- **Test:** 98 deterministik test + LLM smoke test izolasyonu
- **CI:** GitHub Actions pipeline + benchmark regression gate

### Bilinen Sınırlamalar (alpha)

- Sonuç modelleme/parser adapter eksik (Sprint 4 hedefi)
- Öneri motoru yok (Sprint 5 hedefi)
- Plugin sistemi yok (Sprint 6 hedefi)
- Yalnızca Windows native execution (Linux build Sprint 6'da)

---

## 5) Git Tag Kuralları

### Tag Formatı

```
v{MAJOR}.{MINOR}.{PATCH}[-{pre-release}]
```

Örnekler:
```
v0.4.0-alpha
v0.4.1
v0.5.0-beta
v1.0.0-rc.1
v1.0.0
```

### Tag Oluşturma

```bash
# Annotated tag (her zaman annotated kullanılır)
git tag -a v0.4.0-alpha -m "v0.4.0-alpha: İlk resmi sürüm - Hierarchical AI + Backend Chat"

# Push
git push origin v0.4.0-alpha
```

### Tag Kuralları

1. Tag'ler **yalnızca `develop` veya `main` branch'ten** oluşturulur
2. Tag oluşturulmadan önce **tüm testler yeşil** olmalıdır
3. alpha/beta tag'leri `develop`'tan, rc/stable tag'leri `main`'den atılır
4. Tag mesajı sürümün kısa özetini içerir

---

## 6) Branch → Sürüm İlişkisi

```
feature/xxx ──→ dev_kerem ──→ develop ──→ main
                                │            │
                           alpha/beta    rc/stable
                            tag'leri     tag'leri
```

| Branch | Rol | Tag Türü |
|--------|-----|----------|
| `dev_kerem` | Aktif geliştirme | Tag atılmaz |
| `develop` | Entegrasyon | alpha, beta |
| `main` | Kararlı sürüm | rc, stable |

---

## 7) Sürüm Yayınlama Kontrol Listesi

Yeni bir sürüm yayınlamadan önce:

- [ ] Tüm hedef sprint görevleri tamamlandı
- [ ] `pytest -m "not llm"` tam yeşil
- [ ] Benchmark gate geçiyor (varsa)
- [ ] Sprint dokümanları güncel
- [ ] `sprint_roadmap.md` senkronize
- [ ] Changelog/release notes hazır
- [ ] `dev_kerem` → `develop` merge edildi
- [ ] Annotated tag oluşturuldu
- [ ] Tag push edildi

---

## 8) Changelog Formatı

Her sürüm için `CHANGELOG.md` (proje kökünde) tutulur. Format:

```markdown
## [v0.4.0-alpha] — 2026-03-11

### Eklenenler
- 2 aşamalı hierarchical intent resolution
- Backend session-memory chat
- 11 dil desteği (i18n)
- Benchmark regression gate (CI)

### Değişenler
- Qwen 2.5 3B Instruct model entegrasyonu
- flat intent → hierarchical intent mimarisi

### Düzeltilenler
- Few-shot JSON brace escaping hatası
- DNS/WHOIS override false positive
- Param hallucination (implicit param pruning)
```

[Keep a Changelog](https://keepachangelog.com/) standardı izlenir:  
`Eklenenler`, `Değişenler`, `Düzeltilenler`, `Kaldırılanlar`, `Kullanımdan Kaldırılanlar`, `Güvenlik`

---

## 9) 1.0.0'a Giden Yol

```
v0.4.0-alpha ── v0.4.x ──► v0.5.0-alpha ── v0.5.x ──► v0.6.0-alpha ──► ... ──► v1.0.0
     │                          │                          │                       │
  Bugün                   Veri Adaptasyonu           Plugin Sistemi          Kararlı Sürüm
  AI Pipeline             Sonuç Modelleri            Linux Build             Production Ready
  Backend Chat            Sprint 4                   Sprint 5+6              Tüm Sprint'ler ✅
```

### v1.0.0 Kriterleri

Aşağıdaki koşullar sağlandığında MAJOR 1'e yükseltilir:

1. **Çekirdek özellik tamam:** Intent → Execute → Parse → Suggest döngüsü eksiksiz
2. **Platform desteği:** Windows + Linux native build
3. **Plugin sistemi:** 3. parti tool entegrasyonu mümkün
4. **Stabilite:** 500+ test, %95+ benchmark skoru, 0 kritik bug
5. **Dokümantasyon:** Kullanıcı kılavuzu, API belgeleri, katkı rehberi mevcut

---

## 10) Özet Karar Tablosu

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Şema | SemVer 2.0.0 | Endüstri standardı, araç uyumluluğu |
| İlk sürüm | v0.4.0-alpha | Sprint milestone eşleştirmesi, pre-stable dönemi |
| Pre-release akışı | alpha → beta → rc → stable | Kademeli olgunlaşma |
| Tag kaynağı | develop (alpha/beta), main (rc/stable) | Branch rollerine uygun |
| Changelog | Keep a Changelog standardı | Okunabilir, yapılandırılmış |
| 1.0.0 hedefi | Post-Sprint 6 | Tüm çekirdek özellikler tamamlandığında |
