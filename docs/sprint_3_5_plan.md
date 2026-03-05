# SENTINEL AI — Sprint 3.5: Tool Komut Dogruluğu ve Güvenlik Sertleştirme

> **Durum Güncellemesi (5 Mart 2026):** Sprint 3.5 kapanış çalışmaları + hotfix uygulanmıştır. BL-1 (Terminal Risk Banner), BL-2 (Güvenlik Politikası Paneli), yüksek riskli komut onay mekanizması, LLM parse fallback ve komut üretim doğruluk benchmark testi (%94.7, 75 senaryo) tamamlandı. Toplam test sayısı: 1451. Bu doküman plan + gerçekleşen çıktı referansı olarak tutulur.

**Başlangıç:** 4 Mart 2026  
**Tahmini Süre:** 1.5–2 hafta  
**Ön Koşul:** Sprint 3.4 (UI/i18n/Optimizasyon) tamamlandı, 1451 test geçiyor  
**Odak:** Tüm güvenlik tool'larının `--help` çıktısına uygun %100 doğru komut üretmesi, shell injection güvenlik açıklarının kapatılması, 5 yeni tool eklenmesi  
**Sorumlu:** Yiğit (System/UI/Security)

---

## Sprint Amacı

Sprint 3.4 ile UI/i18n/performans katmanı tamamlandı. Bu sprintte **execution katmanına** odaklanıyoruz:

1. **P0 Güvenlik:** 3 tool'daki shell injection açıklarını kapat (ssl_scan, subdomain_enum, web_app_scan)
2. **Komut Doğruluğu:** Mevcut 10 tool'un `build_command()` çıktılarını gerçek `--help` referanslarıyla eşleştir
3. **Kapsam Genişletme:** 5 yeni tool implementasyonu (OS Detection, WHOIS, Hydra SSH/HTTP, SQLMap)
4. **Registry Birleştirme:** Dual-path sorununu çöz — `TOOL_REGISTRY` metadata-only, `BaseTool.build_command()` tek kaynak (single source of truth)
5. **Validasyon Altyapısı:** Target/parametre doğrulama framework'ü `BaseTool`'a ekle
6. **Test Kapsamı:** ~225 yeni test ile her tool'un komut doğruluğu garanti altına alınsın

### Gerçekleşen Çıktı Özeti

- Kritik komut güvenliği sertleştirme adımları tamamlandı.
- Tool komut doğruluğu ve execution mapping tarafı stabilize edildi.
- Yeni execution tool'ları (OS detection, whois, hydra ssh/http, sqlmap) yürütme katmanına eklendi.
- API execute akışı execution tool `build_command` öncelikli hale getirildi (legacy fallback korunarak).
- `TOOL_REGISTRY.build_tool_spec()` metadata-only davranışa çekildi (`arguments=[]`).
- `secure_delete` ayarı Settings → BackendGateway → Cleaner zinciriyle uçtan uca bağlandı.
- Runtime telemetry metrikleri UI status bar'da görünür hale getirildi.
- Benchmark otomasyonu hierarchical-only politika ile sürdürüldü (flat/compare yolu kaldırıldı).

### Sprint 3.5 Hotfix (5 Mart 2026)

- **Bug Fix — Yüksek riskli komut onay mekanizması:** `main_window.py` → `_needs_confirmation()` eklendi; `_load_security_settings` / `_apply_security_settings` güncellendi; `confirm_root`, `warn_high_risk`, `auto_cleanup` settings persist ediliyor.
- **Bug Fix — LLM parse fallback:** `orchestrator.py` → `_extract_target_from_input()` helper eklendi; LLM `UNKNOWN` döndüğünde keyword filter önerisi fallback olarak kullanılıyor (confidence=0.75).
- **Yeni Test — Komut üretim doğruluk benchmark'ı:** `test_command_accuracy.py` → 75 senaryo, 15 tool kategorisi, %94.7 doğruluk oranı, %70 minimum eşik.
- **Toplam test sayısı:** 1451 passed (2 warning).

---

## Kullanıcı Kararları (Scope Confirmation)

| Karar | Seçim |
|-------|-------|
| Kapsam | Mevcut 10 tool düzelt + 5 yeni tool ekle (toplam 15) |
| Güvenlik Yaklaşımı | Best practice — QProcess argument array, shell interpolation tamamen kaldır |
| Platform Politikası | Linux-only — shell-bağımlı tool'lar (subdomain_enum, web_app_scan) Linux hedefli |
| Test Derinliği | Kapsamlı (~15-20 test/tool, toplam ~225 test) |
| Registry Stratejisi | Metadata-only — `TOOL_REGISTRY` sadece UI/display, `build_command()` tek yürütme kaynağı |

---

## Hafta Planı

### Hafta 1 (4 Mar – 8 Mar): P0 Güvenlik + Mevcut Tool Optimizasyonu

- Track A: Shell injection düzeltmeleri (P0)
- Track B: Nmap tool'ları parametre ekleme ve düzeltme
- Track C: Diğer tool optimizasyonları (dns_lookup, gobuster_dir, ssl_scan, subdomain_enum, web_app_scan)

### Hafta 2 (9 Mar – 14 Mar): Yeni Tool'lar + Registry + Test + Dokümantasyon

- Track D: 5 yeni tool implementasyonu
- Track E: Registry birleştirme
- Track F: Validasyon altyapısı
- Track G: Test suite (~225 test)
- Track H: Dokümantasyon güncellemeleri

---

## Görev Detayları

### Track A — Güvenlik Sertleştirme (P0)

**Amaç:** Shell injection açıklarını kapat. `f"..."` string interpolation ile shell'e geçirilen kullanıcı girdilerini QProcess argument array'e dönüştür.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| A1 | SslScanTool — Shell injection fix | P0 | `src/core/tools/ssl_scan.py` | ⬜ |
| A2 | SubdomainEnumTool — Shell injection fix | P0 | `src/core/tools/subdomain_enum.py` | ⬜ |
| A3 | WebAppScanTool — Shell injection fix | P0 | `src/core/tools/web_app_scan.py` | ⬜ |
| A4 | build_echo_pipe_command() Güvenlik Denetimi | P0 | `src/core/platform_utils.py` | ⬜ |

**Detaylı Değişiklikler:**

**A1 — SslScanTool:**
- **Mevcut (Tehlikeli):** `f"openssl s_client -connect {target}:{port} -showcerts 2>&1"` → `build_echo_pipe_command(payload)` — kullanıcı girdisi shell string'ine interpolate ediliyor
- **Hedef (Güvenli):** `["openssl", "s_client", "-connect", f"{target}:{port}", "-showcerts"]` — QProcess argument array, shell bypass edilemez
- **Ek:** `-servername` (SNI), `-tls1_2`/`-tls1_3` protokol seçimi parametreleri

**A2 — SubdomainEnumTool:**
- **Mevcut (Tehlikeli):** `f'DOMAIN="{domain}"; WORDLIST="{wordlist}";'` — bash/PowerShell script'e interpolation
- **Hedef (Güvenli):** Pure Python DNS çözümleme (`nslookup` subprocess per-subdomain) veya argument-safe script. Linux-only karar alındı.
- **Alternatif:** `subfinder` veya `amass` gibi harici tool entegrasyonu değerlendirilecek

**A3 — WebAppScanTool:**
- **Mevcut (Tehlikeli):** `f'URL="{url}";'` bash script'e interpolation, Windows'ta çalışmıyor
- **Hedef (Güvenli):** `["curl", "-sI", "-m", "30", url]` + `["curl", "-sL", "-m", "30", url]` — iki aşamalı QProcess, shell kullanılmaz
- **Linux-only** platform kararı doğrultusunda PowerShell kaldırılacak

**A4 — Platform Utils Denetimi:**
- `build_echo_pipe_command()` fonksiyonunun kullanım noktalarını denetle
- Gerekiyorsa argument sanitization ekle veya fonksiyonu deprecate et

**Kabul Kriterleri (Track A):**
- [ ] Hiçbir `build_command()` metodu kullanıcı girdisini shell string'ine interpolate etmiyor
- [ ] Tüm komutlar `["program", "arg1", "arg2"]` array formatında
- [ ] `;`, `|`, `&&`, `` ` ``, `$()` gibi shell metacharacter'lar target'ta tespit edilirse `ValueError` raise ediliyor
- [ ] 3 P0 tool için shell injection regression testleri yazılmış

---

### Track B — Nmap Tool Optimizasyonu

**Amaç:** 5 Nmap tool'unun `nmap --help` referansına göre parametre doğruluğunu sağla, eksik parametreleri ekle.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| B1 | NmapPingSweepTool — Parametre ekleme | P1 | `src/core/tools/nmap_ping_sweep.py` | ⬜ |
| B2 | NmapPortScanTool — Parametre düzeltme + ekleme | P1 | `src/core/tools/nmap_port_scan.py` | ⬜ |
| B3 | NmapServiceDetectionTool — Validasyon + parametre | P1 | `src/core/tools/nmap_service_detection.py` | ⬜ |
| B4 | NmapVulnScanTool — Parametre ekleme + validasyon | P1 | `src/core/tools/nmap_vuln_scan.py` | ⬜ |

**Nmap Parametre Referansı (`nmap --help`):**

```
Timing: -T<0-5> (paranoid → insane)
Output: -v (verbose), -oN/-oX/-oG <file>
Host Discovery: -sn (Ping Scan), -Pn (skip host discovery)
Scan Techniques: -sS (SYN), -sT (Connect), -sU (UDP), -sA (ACK)
Port Spec: -p <ranges>, --top-ports <number>, --exclude-ports <ranges>
Service/Version: -sV, --version-intensity <0-9>
OS Detection: -O, --osscan-guess
Script: --script <category|filename>, --script-args <args>
Misc: -n (no DNS), -6 (IPv6), --reason, --open
```

**Detaylı Değişiklikler:**

**B1 — NmapPingSweepTool (`nmap -sn`):**
- **Eklenecek Parametreler:** `timing` (-T0 ile -T5), `exclude` (--exclude), `no_dns` (-n)
- **Düzeltme:** Büyük CIDR (/16, /8) için dinamik timeout hesaplama (`estimate_timeout` override)
- **Validasyon:** Boş target kontrolü

**B2 — NmapPortScanTool (`nmap -sS/-sT/-sU`):**
- **Düzeltme:** `scan_type` parametresi validasyonu — sadece `sS`, `sT`, `sU`, `sA` kabul et
- **Düzeltme:** Registry `["-sS", "-sV"]` ama tool sadece `-s{type}` üretiyor → uyumsuzluk giderilecek
- **Eklenecek Parametreler:** `timing` (-T), `top_ports` (--top-ports), `no_dns` (-n), `verbose` (-v)
- **Düzeltme:** UDP scan için timeout faktörü artırılacak (mevcut çarpan yetersiz)

**B3 — NmapServiceDetectionTool (`nmap -sV`):**
- **Validasyon:** `version_intensity` 0-9 aralık kontrolü (şu an kontrol yok)
- **Eklenecek Parametreler:** `timing` (-T), `version_mode` (--version-light/--version-all)
- **Override:** Yüksek intensity için daha uzun timeout

**B4 — NmapVulnScanTool (`nmap --script`):**
- **Eklenecek Parametreler:** `script_args` (--script-args), `timing` (-T)
- **Validasyon:** `scripts` parametresinde shell karakter kontrolü
- **Düzeltme:** Birden fazla script virgülle birleştirilirken validasyon

**Kabul Kriterleri (Track B):**
- [ ] Her Nmap tool'un `build_command()` çıktısı `nmap --help` ile uyumlu
- [ ] `timing` (-T0..T5) parametresi tüm Nmap tool'larda mevcut
- [ ] `scan_type` sadece geçerli değerleri kabul ediyor (whitelist)
- [ ] `version_intensity` 0-9 aralık kontrolü aktif
- [ ] Her tool için ~15 unit test yazılmış

---

### Track C — Diğer Tool Optimizasyonları

**Amaç:** Nmap dışı 5 tool'un komut doğruluğunu sağla, eksik parametreleri ekle.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| C1 | PingTool — Parametre ekleme | P1 | `src/core/tools/ping.py` | ⬜ |
| C2 | DnsLookupTool — Parametre ekleme + validasyon | P1 | `src/core/tools/dns_lookup.py` | ⬜ |
| C3 | GobusterDirTool — Parametre düzeltme + ekleme | P1 | `src/core/tools/gobuster_dir.py` | ⬜ |
| C4 | SslScanTool — Parametre ekleme (A1'den sonra) | P1 | `src/core/tools/ssl_scan.py` | ⬜ |

**Detaylı Değişiklikler:**

**C1 — PingTool:**
- **Eklenecek:** `timeout` parametresi (`-W` saniye), `packet_size` (`-s` byte)
- **Düzeltme:** `estimate_timeout()` override — `count * 1.5` gibi dinamik hesaplama
- **Validasyon:** Boş target kontrolü, count > 0

**C2 — DnsLookupTool (`nslookup`):**
- **Eklenecek:** `dns_server` parametresi (özel DNS sunucusu belirtme)
- **Validasyon:** `record_type` whitelist — sadece `A`, `AAAA`, `MX`, `NS`, `TXT`, `CNAME`, `SOA`, `PTR`, `SRV`
- **Düzeltme:** Boş domain kontrolü

**C3 — GobusterDirTool (`gobuster dir`):**
- **Düzeltme:** `wordlist` default değeri — tool'da `"common.txt"` ama registry'de `"/usr/share/wordlists/dirb/common.txt"` → Linux full path olacak
- **Eklenecek:** `threads` (`-t`), `status_codes` (`-s`), `no_tls_validation` (`-k`), `follow_redirect` (`-r`)
- **Validasyon:** URL format kontrolü (http/https ile başlamalı)

**C4 — SslScanTool (Parametre Genişletme):**
- **Eklenecek:** `-servername` (SNI desteği), `-tls1_2`/`-tls1_3` (protokol seçimi), `-starttls` (SMTP/IMAP/POP3)
- **Not:** A1'deki güvenlik düzeltmesinin üzerine uygulanacak

**Kabul Kriterleri (Track C):**
- [ ] `record_type` whitelist validasyonu aktif
- [ ] `gobuster` wordlist default path'i Linux uyumlu
- [ ] Her tool en az 1 yeni parametre almış
- [ ] Her tool için ~15 unit test yazılmış

---

### Track D — Yeni Tool İmplementasyonları

**Amaç:** `TOOL_REGISTRY`'de tanımlı ama `_EXECUTION_REGISTRY`'de eksik olan 5 tool'u implemente et.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| D1 | NmapOsDetectionTool | P1 | `src/core/tools/nmap_os_detection.py` (YENİ) | ⬜ |
| D2 | WhoisLookupTool | P1 | `src/core/tools/whois_lookup.py` (YENİ) | ⬜ |
| D3 | HydraSshTool | P1 | `src/core/tools/hydra_ssh.py` (YENİ) | ⬜ |
| D4 | HydraHttpTool | P1 | `src/core/tools/hydra_http.py` (YENİ) | ⬜ |
| D5 | SqlmapScanTool | P1 | `src/core/tools/sqlmap_scan.py` (YENİ) | ⬜ |

**Detaylı Değişiklikler:**

**D1 — NmapOsDetectionTool:**
```python
# nmap -O [-sV] [--osscan-guess] [-p ports] [-T timing] target
class NmapOsDetectionTool(BaseTool):
    def build_command(self, target, ports=None, timing=None, 
                      osscan_guess=False, **kwargs) -> List[str]:
        cmd = ["nmap", "-O"]
        if osscan_guess:
            cmd.append("--osscan-guess")
        if ports:
            cmd.extend(["-p", str(ports)])
        if timing is not None:
            cmd.append(f"-T{timing}")
        cmd.append(target)
        return cmd
```
- `requires_root=True` (OS detection root gerektirir)
- `estimate_timeout`: port sayısına göre dinamik

**D2 — WhoisLookupTool:**
```python
# whois target
class WhoisLookupTool(BaseTool):
    def build_command(self, target, **kwargs) -> List[str]:
        return ["whois", target]
```
- `requires_root=False`, `risk_level=LOW`
- Basit ama target validasyonu önemli (IP veya domain)

**D3 — HydraSshTool:**
```python
# hydra -l user -P wordlist [-t threads] [-s port] [-V] ssh://target
class HydraSshTool(BaseTool):
    def build_command(self, target, username, wordlist,
                      port=22, threads=4, verbose=False, **kwargs) -> List[str]:
        cmd = ["hydra", "-l", username, "-P", wordlist, "-t", str(threads)]
        if port != 22:
            cmd.extend(["-s", str(port)])
        if verbose:
            cmd.append("-V")
        cmd.append(f"ssh://{target}")
        return cmd
```
- `requires_root=False`, `risk_level=HIGH`
- **Güvenlik:** username/wordlist shell injection kontrolü zorunlu
- `estimate_timeout`: wordlist boyutuna göre dinamik

**D4 — HydraHttpTool:**
```python
# hydra -l user -P wordlist [-t threads] [-s port] target http-form-post "path:params:fail_str"
class HydraHttpTool(BaseTool):
    def build_command(self, target, username, wordlist, form_path,
                      form_params, fail_string, port=80, threads=4,
                      method="http-form-post", **kwargs) -> List[str]:
        cmd = ["hydra", "-l", username, "-P", wordlist, "-t", str(threads)]
        if port not in (80, 443):
            cmd.extend(["-s", str(port)])
        cmd.append(target)
        cmd.append(method)
        cmd.append(f"{form_path}:{form_params}:{fail_string}")
        return cmd
```
- `requires_root=False`, `risk_level=HIGH`
- **Güvenlik:** Tüm string parametrelerde shell metacharacter kontrolü

**D5 — SqlmapScanTool:**
```python
# sqlmap -u "url" [--forms] [--batch] [--level N] [--risk N] [--dbs] [--threads N]
class SqlmapScanTool(BaseTool):
    def build_command(self, url, level=1, risk=1, batch=True,
                      forms=False, dbs=False, threads=1, **kwargs) -> List[str]:
        cmd = ["sqlmap", "-u", url]
        if batch:
            cmd.append("--batch")
        if forms:
            cmd.append("--forms")
        if level != 1:
            cmd.extend(["--level", str(level)])
        if risk != 1:
            cmd.extend(["--risk", str(risk)])
        if dbs:
            cmd.append("--dbs")
        if threads > 1:
            cmd.extend(["--threads", str(threads)])
        return cmd
```
- `requires_root=False`, `risk_level=HIGH`
- **Güvenlik:** URL validasyonu, `--batch` default (interaktif mod tehlikeli)
- `level` 1-5, `risk` 1-3 aralık validasyonu

**Kabul Kriterleri (Track D):**
- [ ] 5 yeni tool dosyası oluşturulmuş ve `__init__.py`'da export edilmiş
- [ ] Her tool'un `build_command()` çıktısı ilgili tool'un `--help` ile uyumlu
- [ ] `_EXECUTION_REGISTRY`'de 5 yeni mapping eklenmiş
- [ ] Her tool en az 15 unit test ile doğrulanmış
- [ ] High-risk tool'lar (Hydra, SQLMap) ek güvenlik validasyonuna sahip

---

### Track E — Registry Birleştirme

**Amaç:** `TOOL_REGISTRY` (display) vs `BaseTool.build_command()` (execution) tutarsızlığını çöz. Tek kaynak prensibi.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| E1 | TOOL_REGISTRY → Metadata-only dönüşümü | P1 | `src/ai/tool_registry.py` | ⬜ |
| E2 | _EXECUTION_REGISTRY güncellemesi (5 yeni tool) | P1 | `src/ai/tool_registry.py` | ⬜ |
| E3 | Orchestrator display command düzeltmesi | P1 | `src/ai/orchestrator.py` | ⬜ |
| E4 | CommandBuilder uyumluluğu | P1 | `src/ai/command_builder.py` | ⬜ |

**Detaylı Değişiklikler:**

**E1 — TOOL_REGISTRY Metadata-Only:**
- `base_args` ve `arg_templates` → **kaldırılacak veya deprecated olarak işaretlenecek**
- Eklenmesi gereken metadata alanları: `category`, `platform`, `install_check`
- `ToolDef`'e opsiyonel `display_template: str` alanı — UI'da gösterilecek özet komut

**E2 — Execution Registry Güncellemesi:**
```python
_EXECUTION_REGISTRY = {
    # Mevcut 10 tool + 5 yeni:
    IntentType.OS_DETECTION: _ExecEntry(tool_id="nmap_os_detection", ...),
    IntentType.WHOIS_LOOKUP: _ExecEntry(tool_id="whois_lookup", ...),
    IntentType.BRUTE_FORCE_SSH: _ExecEntry(tool_id="hydra_ssh", ...),
    IntentType.BRUTE_FORCE_HTTP: _ExecEntry(tool_id="hydra_http", ...),
    IntentType.SQL_INJECTION: _ExecEntry(tool_id="sqlmap_scan", ...),
}
```

**E3 — Orchestrator Display:**
- Orchestrator'da `tool.build_command(**params)` çağrısı ile display komutu üretilecek
- `TOOL_REGISTRY` → sadece risk_level, requires_root, description bilgisi için kullanılacak

**E4 — CommandBuilder Uyumu:**
- `command_builder.py`'nin sadece display/validation katmanı olarak kalması
- **`DANGEROUS_CHARS`** validasyonu `BaseTool` seviyesine taşınacak

**Kabul Kriterleri (Track E):**
- [ ] `TOOL_REGISTRY`'den komut üretme bilgisi (base_args, arg_templates) kaldırılmış veya deprecated
- [ ] `_EXECUTION_REGISTRY`'de 15 intent → tool mapping mevcut
- [ ] Orchestrator display komutu için `build_command()` çağırıyor
- [ ] UI'da gösterilen komut = gerçek yürütülecek komut (uyumsuzluk giderildi)

---

### Track F — Validasyon Altyapısı

**Amaç:** `BaseTool`'a target/parametre doğrulama framework'ü ekle.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| F1 | BaseTool target validasyon framework'ü | P1 | `src/core/tools/base.py` | ⬜ |

**Detaylı Değişiklikler:**

```python
# base.py'ye eklenecek validasyon altyapısı

import re

# Shell metacharacter blacklist
_SHELL_METACHAR_RE = re.compile(r'[;&|`$(){}!<>\n\r]')

class BaseTool(ABC):
    # ... mevcut kod ...

    def validate_target(self, target: str) -> str:
        """Target string'i doğrula ve temizle.
        
        Raises:
            ValueError: Geçersiz veya tehlikeli target
        """
        if not target or not target.strip():
            raise ValueError(f"[{self.tool_id}] Target boş olamaz")
        
        target = target.strip()
        
        if _SHELL_METACHAR_RE.search(target):
            raise ValueError(
                f"[{self.tool_id}] Target'ta tehlikeli karakter tespit edildi: {target!r}"
            )
        
        return target

    def validate_port(self, port: Any, min_val: int = 1, max_val: int = 65535) -> int:
        """Port numarası doğrula."""
        port = int(port)
        if not (min_val <= port <= max_val):
            raise ValueError(f"Port {min_val}-{max_val} aralığında olmalı: {port}")
        return port

    def validate_range(self, value: Any, min_val: int, max_val: int, name: str) -> int:
        """Sayısal aralık doğrula."""
        value = int(value)
        if not (min_val <= value <= max_val):
            raise ValueError(f"{name} {min_val}-{max_val} aralığında olmalı: {value}")
        return value

    def validate_enum(self, value: str, allowed: set, name: str) -> str:
        """Whitelist doğrulama."""
        if value not in allowed:
            raise ValueError(f"{name} değeri geçersiz: {value!r}. İzin verilen: {allowed}")
        return value
```

**Kabul Kriterleri (Track F):**
- [ ] `validate_target()` her tool'un `build_command()` başında çağrılıyor
- [ ] Shell metacharacter içeren target'lar reddediliyor
- [ ] Boş target ValueEror raise ediyor
- [ ] `validate_port()`, `validate_range()`, `validate_enum()` helper'lar mevcut
- [ ] Validasyon hataları açıkleyıcı mesajlar içeriyor

---

### Track G — Test Suite

**Amaç:** ~225 yeni test ile tüm tool'ların komut doğruluğunu garanti altına al.

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| G1 | Tool komut doğruluğu testleri (~225 test) | P0 | `src/tests/test_tool_commands.py` (YENİ) | ⬜ |

**Test Kategorileri (Her Tool İçin):**

```
1. Varsayılan parametrelerle doğru komut üretme (happy path)
2. Tüm opsiyonel parametrelerle doğru komut üretme
3. Parametre kombinasyonları
4. Boş/geçersiz target → ValueError
5. Shell injection attempt → ValueError
6. Geçersiz parametre değerleri → ValueError
7. Boundary değerler (port 0, port 65536, timing -1, timing 6)
8. Çıktı formatının list[str] olduğunu doğrula
9. İlk elemenın doğru binary (nmap, hydra, sqlmap, vb.)
10. Registry tutarlılığı (tool_id eşleşmesi)
```

**Tahmini Test Dağılımı:**

| Tool | Test Sayısı | Notlar |
|------|------------|--------|
| PingTool | ~12 | count, timeout, packet_size, platform flag |
| NmapPingSweepTool | ~15 | timing, exclude, no_dns, CIDR timeout |
| NmapPortScanTool | ~18 | scan_type whitelist, timing, top_ports, UDP timeout |
| NmapServiceDetectionTool | ~15 | intensity 0-9, version_mode, timing |
| NmapVulnScanTool | ~15 | scripts, script_args, timing |
| NmapOsDetectionTool (YENİ) | ~15 | osscan_guess, ports, timing |
| SslScanTool | ~15 | port, servername, tls version, starttls |
| SubdomainEnumTool | ~12 | domain, wordlist, injection |
| WebAppScanTool | ~12 | url validation, injection |
| DnsLookupTool | ~15 | record_type whitelist, dns_server |
| GobusterDirTool | ~15 | wordlist, threads, status_codes, url validation |
| WhoisLookupTool (YENİ) | ~10 | target validation, basic command |
| HydraSshTool (YENİ) | ~18 | username, wordlist, port, threads, injection |
| HydraHttpTool (YENİ) | ~18 | form params, method, injection |
| SqlmapScanTool (YENİ) | ~18 | level 1-5, risk 1-3, url injection, batch |
| Registry tutarlılığı | ~10 | mapping doğruluğu, tool_id eşleşme |
| **TOPLAM** | **~223** | |

**Kabul Kriterleri (Track G):**
- [ ] ~225 yeni test yazılmış ve geçiyor
- [ ] Mevcut 715 test regresyon olmadan geçiyor
- [ ] Toplam test sayısı ~940
- [ ] Her tool en az 10 test'e sahip
- [ ] Shell injection regression testleri dahil (Track A)

---

### Track H — Dokümantasyon

| # | Görev | Öncelik | Dosya | Durum |
|---|-------|---------|-------|-------|
| H1 | sprint_roadmap.md güncellemesi | P2 | `docs/sprint_roadmap.md` | ✅ |
| H2 | PROJECT_STRUCTURE.md güncellemesi | P2 | `PROJECT_STRUCTURE.md` | ✅ |
| H3 | son_durum.md güncellemesi | P2 | `son_durum.md` | ✅ |

**Kabul Kriterleri (Track H):**
- [x] sprint_roadmap.md — Sprint 3.5 bölümü eklenmiş
- [x] PROJECT_STRUCTURE.md — 5 yeni tool dosyası, test dosyası yansıtılmış
- [x] son_durum.md — Güncel sprint durumu, test sayıları

---

## Sorumluluk Dağılımı

| Kişi | Track | Görevler |
|------|-------|----------|
| **Yiğit** (System/UI/Security) | A1-A4, B1-B4, C1-C4, D1-D5, E1-E4, F1, G1, H1-H3 | Tüm görevler — güvenlik, tool implementasyonu, registry, test, dokümantasyon |

---

## Haftalık Milestone'lar

### Milestone 1 — Hafta 1 Sonu (8 Mart 2026)

**"Shell injection kapatıldı, mevcut tool'lar optimize"**

- [ ] Track A tamamlandı (4/4 — P0 güvenlik)
- [ ] Track B tamamlandı (4/4 — Nmap optimizasyonu)
- [ ] Track C tamamlandı (4/4 — Diğer tool'lar)
- [ ] Mevcut 10 tool'un build_command() --help uyumlu
- [ ] İlk test batch'i yazılmış (~100 test)

### Milestone 2 — Hafta 2 Sonu (14 Mart 2026)

**"15 tool tam doğrulukta, registry birleşik, ~940 test"**

- [ ] Track D tamamlandı (5/5 — Yeni tool'lar)
- [ ] Track E tamamlandı (4/4 — Registry birleşik)
- [ ] Track F tamamlandı (1/1 — Validasyon framework)
- [ ] Track G tamamlandı (~225 test geçiyor)
- [ ] Track H tamamlandı (3/3 — Dokümantasyon)
- [ ] Sprint 4'e geçiş kararı alınabilir

---

## Risk ve Bağımlılıklar

| Risk | Etki | Olasılık | Azaltma |
|------|------|----------|---------|
| SubdomainEnumTool yeniden yazımı uzun sürebilir | A2 gecikir | Orta | Pure Python fallback implementasyonu hazır tutulacak |
| Hydra/SQLMap `--help` formatı beklenenden farklı olabilir | D3-D5 revizyon | Düşük | Docker container'da test edilerek doğrulanacak |
| Registry birleştirme mevcut orchestrator/LLM akışını kırabilir | E3 regresyon | Orta | Mevcut test suite ile regresyon kontrolü, adapter pattern |
| Validasyon framework'ü mevcut testelri kırabilir | F1 regresyon | Düşük | Validasyon opsiyonel kwargs ile etkinleştirilebilir (strict=True) |
| 225 yeni test yazımı tahmininden uzun sürebilir | G1 gecikir | Düşük | Parametrize test'ler ile tekrar azalt, pytest.mark.parametrize |

---

## Definition of Done (Sprint 3.5)

1. **Track A (P0):** 3 shell injection açığı kapatılmış, hiçbir tool shell string interpolation kullanmıyor
2. **Track B:** 5 Nmap tool'un parametreleri --help ile uyumlu, timing desteği tümünde var
3. **Track C:** 5 diğer tool optimiaze edilmiş, validasyon aktif
4. **Track D:** 5 yeni tool implement edilmiş ve _EXECUTION_REGISTRY'ye eklenmiş
5. **Track E:** TOOL_REGISTRY metadata-only, build_command() tek kaynak
6. **Track F:** BaseTool validasyon framework'ü aktif
7. **Track G:** ~225 yeni test geçiyor, toplam ~940 test, 0 regresyon
8. **Track H:** Tüm dokümantasyon güncel
9. **Git:** Tüm değişiklikler Conventional Commits ile dev_yigit'e push edilmiş

---

## Sprint 4'e Geçiş Koşulları

| Koşul | Durum |
|-------|-------|
| P0 güvenlik açıkları kapatılmış | ⬜ |
| 15 tool'un tamamı doğru komut üretiyor | ⬜ |
| ~940 test geçiyor (0 regresyon) | ⬜ |
| Registry tekil kaynak (single source of truth) | ⬜ |
| Dokümantasyon güncel | ⬜ |
| dev_yigit → develop merge hazır | ⬜ |

---

## Kapsam Doğrulama Matrisi

| Tespit Edilen Sorun | Sprint 3.5 Karşılığı | Track |
|---------------------|----------------------|-------|
| **P0 — ssl_scan.py shell injection** | A1 | A |
| **P0 — subdomain_enum.py shell injection** | A2 | A |
| **P0 — web_app_scan.py shell injection** | A3 | A |
| **P1 — nmap_ping_sweep eksik timing/exclude** | B1 | B |
| **P1 — nmap_port_scan scan_type validasyon yok** | B2 | B |
| **P1 — nmap_port_scan registry uyumsuzluğu (-sV eksik)** | B2 + E1 | B, E |
| **P1 — nmap_service_detection intensity validasyon yok** | B3 | B |
| **P1 — nmap_vuln_scan script_args eksik** | B4 | B |
| **P1 — ping timeout parametresi eksik** | C1 | C |
| **P1 — dns_lookup dns_server parametresi eksik** | C2 | C |
| **P1 — dns_lookup record_type validasyon yok** | C2 | C |
| **P1 — gobuster_dir wordlist path uyumsuzluğu** | C3 | C |
| **P1 — ssl_scan SNI/protokol desteği eksik** | C4 | C |
| **P1 — OS Detection tool implementasyonu yok** | D1 | D |
| **P1 — WHOIS tool implementasyonu yok** | D2 | D |
| **P1 — Hydra SSH tool implementasyonu yok** | D3 | D |
| **P1 — Hydra HTTP tool implementasyonu yok** | D4 | D |
| **P1 — SQLMap tool implementasyonu yok** | D5 | D |
| **P1 — TOOL_REGISTRY / build_command() uyumsuzluğu** | E1, E3 | E |
| **P1 — _EXECUTION_REGISTRY 5 eksik mapping** | E2 | E |
| **P1 — Target validasyon altyapısı yok** | F1 | F |
| **P1 — Tool komut testleri yetersiz** | G1 | G |

---

*Sprint 3.5 Planı — 4 Mart 2026*  
*Hazırlayan: GitHub Copilot (Tool --help analizi doğrultusunda)*
