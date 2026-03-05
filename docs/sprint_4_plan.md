# Sprint 4 — Veri Adaptasyonu ve Sonuç Modelleri

**Başlangıç:** Sprint 3.6 tamamlandıktan sonra  
**Tahmini Süre:** 1-2 hafta  
**Ön Koşul:** Sprint 3.6 (Backend Agent-Chat Foundation) tamamlandı ✅

---

## 1. Hedef

Tool çıktılarını (özellikle Nmap XML) yapılandırılmış Pydantic modellere dönüştürmek ve UI'da tablo formatında göstermek. Bu, ham terminal çıktısından yapılandırılmış veri katmanına geçişi sağlar.

---

## 2. Görevler

| # | Görev | Sorumlu | Durum | Dosya | Açıklama |
|---|-------|---------|-------|-------|----------|
| 4.1 | Pydantic Veri Modelleri | Kerem | ⬜ | `src/core/models.py` | ScanResult, Host, Port, Service, Vulnerability modelleri |
| 4.2 | XML Repair Fonksiyonu | Kerem | ⬜ | `src/core/xml_repair.py` | Kesik/bozuk XML çıktılarını düzeltme (unclosed tags, encoding) |
| 4.3 | Nmap Adapter | Kerem | ⬜ | `src/core/adapters/nmap_adapter.py` | XML → Pydantic ScanResult dönüşümü |
| 4.4 | UI Tablo Gösterimi | Yiğit | ⬜ | `src/ui/results_view.py` | Parse edilmiş sonuçları QTableView ile göster |
| 4.5 | Adapter Entegrasyonu | Kerem | ⬜ | `src/core/tool_integration.py` | ToolManager → Adapter → UI pipeline |
| 4.6 | Unit Testler | Kerem | ⬜ | `src/tests/test_sprint4.py` | Model validation, XML repair, adapter dönüşüm testleri |

---

## 3. Detaylı Görev Açıklamaları

### 4.1 — Pydantic Veri Modelleri (`src/core/models.py`)

```python
class Port(BaseModel):
    port_id: int
    protocol: str  # tcp, udp
    state: str     # open, closed, filtered
    service: str | None = None
    version: str | None = None

class Host(BaseModel):
    ip: str
    hostname: str | None = None
    state: str  # up, down
    ports: list[Port] = []
    os_match: str | None = None

class ScanResult(BaseModel):
    tool: str           # nmap, nikto, etc.
    target: str
    start_time: datetime
    end_time: datetime | None = None
    hosts: list[Host] = []
    raw_output: str | None = None
    entity_id: str | None = None
```

**Kabul Kriterleri:**
- Tüm field'lar Pydantic v2 validation ile korunmalı
- `model_dump()` / `model_validate()` round-trip çalışmalı
- JSON serializable olmalı (SQLite'a kaydedilebilir)

### 4.2 — XML Repair (`src/core/xml_repair.py`)

Nmap bazen kesik XML üretir (timeout, Ctrl+C, buffer overflow). Bu modül:

- Kapatılmamış tag'leri otomatik kapatır
- Encoding hatalarını düzeltir (UTF-8 dışı karakterler)
- Minimum valid XML garantisi sağlar
- Repair başarısız olursa raw text olarak fallback

**Test Senaryoları:**
- Normal XML → değişiklik yok
- Kesik XML (son tag kapatılmamış) → otomatik kapama
- Boş/invalid girdi → graceful fallback

### 4.3 — Nmap Adapter (`src/core/adapters/nmap_adapter.py`)

```
Nmap XML Output → xml_repair() → ElementTree parse → ScanResult model
```

- `-oX -` flag'i ile XML çıktı alınır
- `xml.etree.ElementTree` ile parse
- Host/port/service bilgilerini ScanResult'a map'ler
- OS detection sonuçlarını dahil eder

### 4.4 — UI Tablo Gösterimi (`src/ui/results_view.py`)

- `QTableView` + custom `QAbstractTableModel`
- Kolonlar: IP, Port, Protocol, State, Service, Version
- Sıralama ve filtreleme desteği
- Tablo + ham çıktı arası toggle (tab veya split view)

### 4.5 — Adapter Entegrasyonu

ToolManager callback zincirinde adapter'ı araya sokmak:

```
Tool çalışır → raw output → Adapter (varsa) → ScanResult → UI'a gönder
```

- Her tool için opsiyonel adapter mapping
- Adapter yoksa mevcut davranış (raw text) korunur
- `tool_registry.py`'de adapter field eklenir

### 4.6 — Unit Testler

- Model validation testleri (geçerli/geçersiz veri)
- XML repair edge case'leri
- Nmap adapter dönüşüm testleri (gerçek nmap XML örnekleri)
- Adapter entegrasyon testleri (mock tool output → ScanResult)

---

## 4. Teknik Notlar

- **Bağımlılık:** Yeni paket gerekmez (Pydantic v2 + xml.etree.ElementTree standart kütüphane)
- **Geriye Uyumluluk:** Adapter olmayan tool'lar mevcut davranışı korur
- **Performans:** XML parse < 100ms hedef (tipik nmap çıktısı için)
- **SQLite:** ScanResult JSON olarak `execution_history` tablosuna kaydedilebilir

---

## 5. Definition of Done

- [ ] Tüm Pydantic modeller tanımlanmış ve validate edilmiş
- [ ] XML repair en az 3 edge case'i handle ediyor
- [ ] Nmap adapter gerçek XML örnekleri ile test edilmiş
- [ ] UI tablo görünümü çalışıyor (en az nmap için)
- [ ] Adapter pipeline ToolManager'a entegre
- [ ] Tüm yeni testler geçiyor
- [ ] Mevcut test seti regresyonsuz geçiyor (güncel sayı için `son_durum.md` referans alınır)
- [ ] Dokümanlar güncel (PROJECT_STRUCTURE, sprint_roadmap)

---

## 6. Sprint 3.6 → Sprint 4 Geçiş Koşulları

| Koşul | Durum |
|-------|-------|
| Sprint 3.6 tamamlandı | ✅ |
| Güncel test sağlığı yeşil | ✅ |
| Docker container'lar sağlıklı | ✅ |
| Qwen 2.5 3B inference çalışıyor | ✅ |
| dev_kerem → develop merge planı hazır | ✅ |

Ek not (Sprint 3.6):
- Backend chat endpointleri hazır (`/api/chat/session`, `/api/chat/turn`, `/api/chat/history/{session_id}`)
- Session memory altyapısı hazır (`conversation_sessions`, `conversation_turns`)

---

*Son Güncelleme: 4 Mart 2026*
