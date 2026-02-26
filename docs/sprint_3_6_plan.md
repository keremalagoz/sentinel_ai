# SENTINEL AI — Sprint 3.6: Optimizasyon ve Platform Hazırlığı

**Başlangıç:** 26 Şubat 2026  
**Hedef Bitiş:** ~7 Mart 2026 (1.5 hafta)  
**Odak:** Audit sonuçları doğrultusunda kritik bugfix, Linux platform uyumluluğu, AI ölçeklenme altyapısı  
**Kaynak:** [conversation_audit_report.md](conversation_audit_report.md)

---

## Sprint Amacı

Sprint 3.5'teki stabilizasyon çalışmalarının ardından, kapsamlı audit raporunda tespit edilen **kritik hataları düzeltmek**, **Linux hedef platforma uyumluluk** sağlamak ve **Sprint 4+ için ölçeklenme altyapısını** kurmak. Sprint 4'e temiz ve güvenli bir kod tabanıyla girmek ana motivasyondur.

---

## Hafta Planı

### Hafta 1 (26 Şub – 2 Mar): Kritik Bugfix + Linux Uyumluluk

### Hafta 2 (3 Mar – 7 Mar): AI Ölçeklenme Altyapısı + Kod Kalitesi

---

## Görev Detayları

### Track A — Kritik Bugfix (P0) ✅ TAMAMLANDI

| # | Görev | Sorumlu | Öncelik | Dosya(lar) | Durum | Commit |
|---|-------|---------|---------|------------|-------|--------|
| A1 | Merkezi Logging Konfigürasyonu | Kerem | P0 | `main.py` | ✅ Tamamlandı | `f7ace9f` |
| A2 | ToolManager Callback Exception Safety | Kerem | P0 | `src/core/tool_integration.py` | ✅ Tamamlandı | `fe79566` |
| A3 | BackendGateway Güvenlik Düzeltmesi | Kerem | P0 | `src/application/backend_gateway.py` | ✅ Tamamlandı | `89bfed9` |
| A4 | Dokümantasyon Senkronizasyonu | Kerem | P0 | `PROJECT_STRUCTURE.md` | ✅ Tamamlandı | `51e128f` |

**Yapılan Değişiklikler:**
- **A1:** `setup_logging()` fonksiyonu eklendi — RotatingFileHandler (5MB/3 backup), console+file handler, structured format. `main_developer.py` projeden kaldırıldı.
- **A2:** `_wrapped_callback()` yeniden yazıldı — metric recording ve user callback izole try bloklarına ayrıldı, `_active_count` her koşulda doğru kalıyor. Unit test eklendi.
- **A3:** `parse_command()` tamamen yeniden yazıldı — `shlex.split()`, `_ALLOWED_COMMANDS` whitelist, `InputValidator` entegrasyonu, `_ROOT_FLAGS` frozenset. 19 güvenlik testi eklendi.
- **A4:** `PROJECT_STRUCTURE.md` güncellendi — tarih, tool/parser sayıları, application katmanı, yeni dosyalar.

**Kabul Kriterleri (Track A):**
- [x] `main.py` çalıştırıldığında `logs/sentinel.log` dosyasına structured çıktı yazılıyor
- [x] `ToolManager` callback exception senaryosunda `_active_count` doğru kalıyor (unit test ile doğrulandı)
- [x] `BackendGateway.parse_command()` shell injection attempt'ı reddediyor (19 unit test ile doğrulandı)
- [x] `PROJECT_STRUCTURE.md` son güncelleme tarihi ≥ 26 Şubat 2026
- **Regresyon:** 93 test geçti, 0 hata

---

### Track B — Linux Platform Uyumluluğu

| # | Görev | Sorumlu | Öncelik | Dosya(lar) | Açıklama |
|---|-------|---------|---------|------------|----------|
| B1 | PingTool Linux Uyumu | Yiğit | P0 | `src/core/tool_base.py` | `ping -n` → `ping -c` (platform check ile). `ExecutionManager.is_linux` pattern'ini kullan. |
| B2 | SslScanTool Linux Uyumu | Yiğit | P0 | `src/core/tool_base.py` | `cmd.exe /c "echo \| openssl..."` → `bash -c "echo \| openssl..."` veya direkt pipe komutu. |
| B3 | SubdomainEnumTool Yeniden Yazım | Yiğit | P0 | `src/core/tool_base.py` | PowerShell script (Test-Path, Get-Content, Write-Output) → Bash + standart Unix komutları. En çok iş çıkaracak madde. |
| B4 | WebAppScanTool Yeniden Yazım | Yiğit | P0 | `src/core/tool_base.py` | `Invoke-WebRequest` + `powershell.exe` → `curl` + `bash`. |
| B5 | ProcessManager Encoding Temizliği | Yiğit | P1 | `src/core/process_manager.py` | `_get_console_encoding()` `chcp` + `shell=True` linting uyarısı. Linux path'te `shell=True` gereksiz; platform guard ekle. |
| B6 | ExecutionManager Temp Path | Yiğit | P1 | `src/core/execution_manager.py` | `os.environ.get("TEMP", ".")` → Linux'ta `tempfile.gettempdir()` kullan. |
| B7 | Platform Utility Modülü | Kerem | P1 | `src/core/platform_utils.py` (YENİ) | `is_linux()`, `is_windows()`, `get_shell()`, `get_temp_dir()` merkezi platform helper'ları. Tüm tool'ların ortak kullanacağı tek kaynak. |

**Kabul Kriterleri (Track B):**
- [ ] Tüm 10 tool'un `build_command()` metodu Linux'ta çalışabilir komut üretiyor
- [ ] `platform_utils.py` modülü oluşturulmuş ve ilgili dosyalar bunu kullanıyor
- [ ] Mevcut 112 test hâlâ geçiyor (regression yok)
- [ ] Linux ortamında (WSL veya Docker) en az PingTool, SslScanTool, DnsLookupTool testi başarılı

---

### Track C — AI Ölçeklenme Altyapısı

| # | Görev | Sorumlu | Öncelik | Dosya(lar) | Açıklama |
|---|-------|---------|---------|------------|----------|
| C1 | Intent Confidence Skoru | Kerem | P0 | `src/ai/schemas.py`, `src/ai/intent_resolver.py` | `Intent` modeline `confidence: float` alanı ekle. Prompt'u `confidence` döndürecek şekilde güncelle. Orchestrator'da `< 0.7` → clarification tetikle. |
| C2 | Keyword Pre-filter | Kerem | P0 | `src/ai/keyword_filter.py` (YENİ) | Regex/keyword tabanlı hızlı intent ön-eleme. LLM sonucunu cross-validate et. Uyumsuzlukta warning log + clarification. |
| C3 | Response Time Budget | Kerem | P1 | `src/ai/orchestrator.py` | `MAX_RESPONSE_MS = 10_000` bütçe mekanizması. Intent resolution slow olursa keyword fallback devreye girsin. |
| C4 | Intent Benchmark Script | Kerem | P1 | `scripts/intent_benchmark.py` (YENİ) | 25-30 test girdisiyle mevcut model accuracy + latency ölçümü. İleride dual-model karşılaştırması için temel. |
| C5 | Dual-Model Strateji Altyapısı | Kerem | P1 | `src/ai/intent_resolver.py`, `src/ai/orchestrator.py` | IntentResolver'da `model` parametresini konfigurasyon dosyasından okunabilir yap. Intent için küçük model (Phi-3.5-mini / Qwen2.5-3B), suggestion engine için WhiteRabbitNeo kullanılacak şekilde model routing altyapısı hazırla. `ollama pull phi3.5` ile alternatif modeli indir ve `intent_benchmark.py` ile karşılaştırmalı test yap. |
| C6 | Hierarchical Intent Hazırlığı (Forward-Ref) | Kerem | P2 | `src/ai/intent_resolver.py` | Tool sayısı 20'yi geçtiğinde devreye girecek 2 aşamalı intent çözümleme altyapısı. Bu sprintte **sadece tasarım dokümanı + interface** hazırlanacak; implementasyon tool sayısı arttığında yapılacak. Aşama 1: Kategori (scanning/web/recon/bruteforce/exploit/info), Aşama 2: Kategori-özel sub-intent. |
| C7 | Tool Selection Policy (Forward-Ref) | Kerem | P2 | `src/ai/tool_registry.py` | Aynı intent'e birden fazla tool (ör: port_scan → nmap/masscan/rustscan) eşlendiğinde deterministik seçim politikası. Bu sprintte **sadece ToolDef'e `priority` ve `condition` alanları eklenir**, aktif routing Sprint 5'te yeni tool'lar eklendiğinde devreye girer. |

**Kabul Kriterleri (Track C):**
- [ ] `Intent` schema'sında `confidence` alanı var ve IntentResolver bunu döndürüyor
- [ ] Confidence < 0.7 durumunda orchestrator clarification mesajı üretiyor (unit test)
- [ ] Keyword pre-filter en az 10 keyword pattern içeriyor ve LLM sonucu ile cross-validation yapıyor
- [ ] `intent_benchmark.py` çalıştırılabilir ve sonuçları JSON/CSV olarak kaydediyor
- [ ] İkinci model (phi3.5 veya qwen2.5) ile en az 20 örnek üzerinde karşılaştırmalı benchmark yapılmış
- [ ] `ToolDef` yapısına `priority` ve `condition` alanları eklenmiş (opsiyonel, default değerli)
- [ ] Hierarchical intent tasarım notu `docs/` altına yazılmış

---

### Track D — Kod Kalitesi ve Teknik Borç

| # | Görev | Sorumlu | Öncelik | Dosya(lar) | Açıklama |
|---|-------|---------|---------|------------|----------|
| D1 | tool_base.py Dosya Bölme | Yiğit | P1 | `src/core/tool_base.py` → `src/core/tools/` | 792 satırlık dosyayı `src/core/tools/` dizinine böl. Her tool kendi dosyasında: `ping.py`, `nmap_port_scan.py`, vb. `__init__.py` ile geriye uyumlu import sağla. |
| D2 | SQLite WAL Mode | Kerem | P1 | `src/core/sqlite_backend.py` | `PRAGMA journal_mode=WAL` ekle. Concurrent read/write performansı artacak. |
| D3 | Legacy Schema Temizliği | Kerem | P2 | `src/ai/schemas.py` | Kullanılmayan `ToolCommand`, `AIResponse`, `TOOL_COMMAND_SCHEMA`, `AI_RESPONSE_SCHEMA` temizle veya `_legacy` altına taşı. 577 → ~380 satır hedef. |
| D4 | Singleton Thread Safety | Kerem | P2 | `src/ai/orchestrator.py`, `src/ai/intent_resolver.py` | Global `_orchestrator` ve `_resolver` singleton'larına `threading.Lock` ile guard ekle. |

**Kabul Kriterleri (Track D):**
- [ ] `src/core/tools/` dizini oluşturulmuş, her tool ayrı dosyada, `__init__.py` geriye uyumlu
- [ ] SQLite WAL mode aktif, `PRAGMA journal_mode` sorgusu `wal` döndürüyor
- [ ] Tüm testler geçiyor (112+)

---

## Sorumluluk Dağılımı

| Kişi | Track | Görevler |
|------|-------|----------|
| **Kerem** (AI/Data/Backend) | ~~A1~~, ~~A2~~, ~~A4~~, ~~B7~~, C1-C7, D2, D3, D4 | ~~Logging~~, ~~callback safety~~, ~~platform_utils~~, AI scaling, dual-model, SQLite, schema cleanup |
| **Yiğit** (System/UI/Security) | ~~A3~~, ~~A4~~, ~~B1-B6~~, D1 | ~~BackendGateway fix~~, ~~Linux uyumluluk~~, tool dosya bölme |

---

## Haftalık Milestone'lar

### Milestone 1 — Hafta 1 Sonu (2 Mart 2026)

**"Kritik bug'sız, Linux'ta çalışır"**

- [x] Track A tamamlandı (4/4 görev) — 26 Şubat 2026
- [x] Track B (B1-B4) kritik Linux fix'leri tamamlandı — 26 Şubat 2026
- [x] 126 test yeşil (hedef 112+ aşıldı)
- [  ] Güncellenmiş dokümantasyon merge edildi

### Milestone 2 — Hafta 2 Sonu (7 Mart 2026)

**"Ölçeklenmeye hazır, temiz kod tabanı"**

- [x] Track B tamamlandı (B5-B7 dahil) — 26 Şubat 2026
- [  ] Track C (C1-C4) tamamlandı (confidence, pre-filter, benchmark, dual-model baseline)
- [  ] Track C (C5) dual-model routing altyapısı hazır, karşılaştırmalı benchmark tamamlanmış
- [  ] Track C (C6, C7) forward-ref tasarım dokümanları yazılmış
- [  ] Track D (D1, D2) tamamlandı
- [  ] Track D (D3, D4) en az başlamış
- [  ] Sprint 4'e geçiş kararı alındı

---

## Risk ve Bağımlılıklar

| Risk | Etki | Azaltma |
|------|------|---------|
| SubdomainEnumTool PowerShell → Bash dönüşümü beklenenden uzun sürebilir | ~~B3 gecikir~~ | ✅ Tamamlandı — bash/PowerShell dual-path uygulandı |
| Confidence skoru LLM'den tutarsız gelebilir | C1 doğruluğu düşük | Prompt engineering + 30 örnek ile kalibrasyon, hard-coded 0.7 threshold yerine ayarlanabilir yap |
| tool_base.py bölme sırasında import zinciri kırılabilir | D1 regression | `__init__.py` ile backward compatibility, her bölme adımında test çalıştır |
| Keyword pre-filter false negative üretebilir | C2 güvenilirliği | Pre-filter sadece cross-validation için; tek başına karar verici değil, LLM sonucunu override etmez |

---

## Definition of Done (Sprint 3.6)

1. Track A (P0 bugfix) — ✅ **%100 tamamlandı** (26 Şubat 2026)
2. Track B (Linux uyumluluk) — ✅ **%100 tamamlandı** (26 Şubat 2026)
3. Track C (AI scaling) — **C1 + C2 %100**, C3 + C4 + C5 en az prototype, C6 + C7 tasarım dokümanı
4. Track D (teknik borç) — **D1 + D2 %100**, D3 + D4 opsiyonel
5. Tüm testler yeşil (minimum 112, yeni testlerle birlikte 120+ hedef)
6. `sprint_roadmap.md` ve `son_durum.md` senkronize
7. Sprint 4 için hazırlık notu yazılmış

---

## Sprint 4'e Geçiş Koşulları

Sprint 3.6 tamamlandığında Sprint 4'e geçiş için şu koşullar aranır:

- [  ] P0 görevlerin tamamı kapatılmış
- [x] Linux'ta en az temel tool'lar (ping, nmap, dns) çalışır durumda (cross-platform build_command tamamlandı)
- [  ] Intent confidence mekanizması aktif
- [  ] Kod tabanı tool dosyalarına bölünmüş (`src/core/tools/`)
- [  ] 120+ test geçiyor

---

---

## Kapsam Doğrulama Matrisi

Audit raporunda ve takip konuşmalarında belirlenen tüm konuların sprint karşılığı:

| Audit / Konuşma Konusu | Sprint 3.6 Karşılığı | Durum |
|-------------------------|----------------------|-------|
| **P0 — Merkezi logging** | A1 | ✅ Tamamlandı (`f7ace9f`) |
| **P0 — Callback deadlock** | A2 | ✅ Tamamlandı (`fe79566`) |
| **P0 — BackendGateway güvenlik** | A3 | ✅ Tamamlandı (`89bfed9`) |
| **P0 — Dokümantasyon sync** | A4 | ✅ Tamamlandı (`51e128f`) |
| **P1 — SQLite WAL mode** | D2 | ✅ Dahil |
| **P1 — tool_base.py bölme** | D1 | ✅ Dahil |
| **P2 — Legacy schema temizliği** | D3 | ✅ Dahil |
| **P2 — Singleton thread safety** | D4 | ✅ Dahil |
| **Linux — PingTool `-n` → `-c`** | B1 | ✅ Tamamlandı (`e3e6a79`) |
| **Linux — SslScanTool `cmd.exe`** | B2 | ✅ Tamamlandı (`e3e6a79`) |
| **Linux — SubdomainEnumTool PowerShell** | B3 | ✅ Tamamlandı (`e3e6a79`) |
| **Linux — WebAppScanTool PowerShell** | B4 | ✅ Tamamlandı (`e3e6a79`) |
| **Linux — ProcessManager encoding** | B5 | ✅ Tamamlandı (`e3e6a79`) |
| **Linux — ExecutionManager temp path** | B6 | ✅ Tamamlandı (`e3e6a79`) |
| **Linux — Platform utility modülü** | B7 | ✅ Tamamlandı (`e3e6a79`) |
| **Model — Dual-model stratejisi (küçük model → intent)** | C5 | ✅ Dahil |
| **Model — Intent benchmark karşılaştırması** | C4 | ✅ Dahil |
| **Ölçeklenme — Intent confidence skoru** | C1 | ✅ Dahil |
| **Ölçeklenme — Keyword pre-filter & cross-validation** | C2 | ✅ Dahil |
| **Ölçeklenme — Response time budget** | C3 | ✅ Dahil |
| **Ölçeklenme — Hierarchical intent (2 aşamalı)** | C6 (forward-ref) | ✅ Tasarım dahil |
| **Ölçeklenme — Tool selection policy (aynı intent → çoklu tool)** | C7 (forward-ref) | ✅ Tasarım dahil |
| **Sprint 4 — Pydantic veri modeli + nmap adapter** | Sprint 4'e kalır | ⏭️ Sonraki sprint |
| **Sprint 5 — Suggestion engine (WhiteRabbitNeo)** | Sprint 5'e kalır | ⏭️ Sonraki sprint |

---

*Sprint 3.6 Planı — 26 Şubat 2026*  
*Son Güncelleme: 26 Şubat 2026 — Track A+B tamamlandı, main_developer.py kaldırıldı*  
*Hazırlayan: GitHub Copilot (Audit Report verileri doğrultusunda)*
