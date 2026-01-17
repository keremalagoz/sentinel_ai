# SENTINEL AI – Tool Registry Düzenleme Kılavuzu

Bu kılavuz, Action Planner v2 mimarisinde yeni bir güvenlik aracı/intent ekleme, mevcut araçların argümanlarını güncelleme ve ilgili katmanları senkronize etme adımlarını açıklar.

---

## Mimari Bağlam (v2)
- Intent Resolver: LLM sadece kullanıcı niyetini (Intent) belirler.
- Policy Gate: Opsiyonel intent kontrolü (engelle/uyar).
- Tool Registry: Intent → ToolDef eşlemesi (statik, deterministik).
- Command Builder: ToolSpec + params → FinalCommand (validasyon + komut üretimi).

Tool Registry, LLM’in ürettiği `intent_type` bilgisini deterministik biçimde bir araca (tool) ve temel argümanlara dönüştürür.

---

## Tool Registry Nedir?
`src/ai/tool_registry.py` dosyasında yer alır ve şu yapıyı kullanır:

- `TOOL_REGISTRY: Dict[IntentType, ToolDef]`
- `ToolDef` alanları:
  - **tool:** Aracın adı (örn. `nmap`, `gobuster`).
  - **base_args:** Varsayılan argümanlar listesi (örn. `[-sS, -sV]`).
  - **requires_root:** Root gereksinimi (örn. SYN scan = true).
  - **risk_level:** `LOW | MEDIUM | HIGH` – UI göstergeleri ve uyarılar için.
  - **description:** Kullanıcıya ve loglara yönelik kısa açıklama.
  - **arg_templates:** Parametre → argüman şablonları (örn. `{ "ports": "-p {value}" }`).

---

## Yeni Intent/Tool Ekleme Adımları
1. **IntentType’a ekle** (`src/ai/schemas.py`):
   - Yeni intent sabitini ekleyin (örn. `PING = "ping"`).
2. **ALLOWED_TOOLS’a ekle** (`src/ai/schemas.py`):
   - Güvenlik için izinli araçlar listesine yeni aracınızı ekleyin (örn. `"ping"`).
3. **Tool Registry’e ekle** (`src/ai/tool_registry.py`):
   - `TOOL_REGISTRY` içine yeni `IntentType` için `ToolDef` oluşturun.
4. **Intent Resolver promptunu güncelle** (`src/ai/intent_resolver.py`):
   - LLM promptundaki “INTENT TURLERI” listesine yeni intent’i ekleyin ve kısa açıklama yazın.
5. **Gerekirse Command Builder validasyonlarını kontrol edin** (`src/ai/command_builder.py`):
   - Hedef (IP/domain/URL) ve özel argüman kuralları yeterli mi? Gerekliyse genişletin.
6. **Testleri ekleyin/güncelleyin** (`src/tests/test_action_planner_v2.py`):
   - Registry ve komut üretici testleri.

---

## Örnek: “Ping” Intenti Eklemek
Kullanıcı “hedefe 5 ping gönder” dediğinde `ping` çalıştırmak istiyoruz.

1) `IntentType` içine ekleyin:
```python
# src/ai/schemas.py
class IntentType(str, Enum):
    # ...
    HOST_DISCOVERY = "host_discovery"      # nmap -sn
    PING = "ping"                          # tek host ping testi
    PORT_SCAN = "port_scan"
    # ...
```

2) **ALLOWED_TOOLS** listesine ekleyin:
```python
# src/ai/schemas.py
ALLOWED_TOOLS = frozenset({
    "nmap", "gobuster", "nikto", "dirb", "hydra", "sqlmap",
    "whois", "dig", "nslookup", "ping", "curl", "wget",
})
```

3) Tool Registry eşlemesi:
```python
# src/ai/tool_registry.py
IntentType.PING: ToolDef(
    tool="ping",
    base_args=["-c", "4"],  # Linux/macOS için (Windows: -n 4)
    requires_root=False,
    risk_level=RiskLevel.LOW,
    description="Tek hoste ping gonder",
    arg_templates={
        "count": "-c {value}",  # Örn. -c 5
    }
),
```

4) Intent Resolver promptu:
```text
- ping: Tek hoste ping gonder (5, 10, vs.)
```

5) Command Builder notu:
- Ping hedefi `target` olarak eklenir (`FinalCommand.arguments` sonuna eklenir).
- Platform farklılıkları: Docker/tools konteyneri Linux olduğundan `-c` uygundur. Native Windows geliştirmede `-n` farkı için ileride `ExecutionManager`/`ProcessManager` seviyesinde platform branch’leri eklenebilir.

6) Test ekleme:
```python
# src/tests/test_action_planner_v2.py
spec = build_tool_spec(IntentType.PING, target="192.168.1.1", params={"count": "5"})
assert spec.tool == "ping"
assert "-c" in spec.arguments and "5" in spec.arguments
```

---

## Parametre Eşleme Kuralları
- `arg_templates` şablonları **boşlukla** ayrılır ve `CommandBuilder` tarafından bir listeye bölünür.
- Sadece `{value}` placeholder’ını kullanın; başka `{}` kullanımları reddedilir.
- Girişler `schemas.py` içinde uzunluk ve kontrol karakterleri açısından doğrulanır.

---

## Risk ve Root Sınıflandırması
- **LOW:** Bilgi toplama (ping, whois, dns).
- **MEDIUM:** Aktif tarama, port scan, service detection.
- **HIGH:** Exploit, brute force, NSE vuln scriptleri.
- **requires_root:** SYN scan (`nmap -sS`), OS detection (`-O`) gibi işler için `True`.

---

## Güvenlik İlkeleri
- `ToolCommand.arguments` daima **liste** olmalı; string birleştirme yok.
- Sadece izinli araçlar (`ALLOWED_TOOLS`) çalıştırılabilir.
- `{target}` dışında şablon yer tutucu barındıran argümanlar reddedilir.

---

## Test ve Doğrulama
- Unit: Registry, Builder, Gate (LLM gerekmez).
- Integration: Resolver, Orchestrator (LLM gerekebilir).
- Backward compat: `AIResponse` / `ToolCommand` dönüşleri doğrulanır.

---

## Conventional Commits Önerisi
- `feat(ai): add ping intent mapping`
- `docs(ai): update resolver prompt with ping`
- `test(ai): add ping registry/builder tests`

---

## Sık Hatalar ve Çözümleri
- Intent eklendi ama Registry güncellenmedi → Komut üretilemez.
- Araç ALLOWED_TOOLS’a eklenmedi → Validasyon hatası.
- Prompt güncellenmedi → LLM intent’i yanlış seçebilir.
- Platform farkı (Windows `ping -n`) → Geliştirici modda uyarı gösterin veya ileride platform branch ekleyin.

---

## Referans Dosyalar
- `src/ai/schemas.py` – IntentType, ToolCommand, ALLOWED_TOOLS.
- `src/ai/tool_registry.py` – ToolDef, TOOL_REGISTRY.
- `src/ai/command_builder.py` – FinalCommand üretimi ve validasyon.
- `src/ai/intent_resolver.py` – LLM promptu ve intent çıkışı.
- `src/ai/orchestrator.py` – Katmanlı akış ve API.
- `src/tests/test_action_planner_v2.py` – v2 testleri.
