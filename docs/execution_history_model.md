# `execution_history_model.md`

## Purpose

Bu dokümanın amacı:

* **Tool execution gerçeği** ile **knowledge state**’i ayırmak
* Parser failure durumlarında **yanlış varsayım üretimini engellemek**
* Planner ve conditional stage logic için **deterministik referans** sağlamak
* Debug, audit ve resume senaryolarını mümkün kılmak

> **Önemli ilke:**
> *“Tool çalıştı mı?” ≠ “Bilgi üretildi mi?”*

---

## Core Design Principle

Execution State **iki ayrı katmandan oluşur**:

1. **Knowledge State**

   * Normalize entity’ler (Host, Port, Service, …)
   * Deduplicated
   * TTL + pruning uygulanır

2. **Execution History State**

   * Tool execution sonuçları
   * Parse durumu
   * Zamanlama, hata, çıktı bilgisi

Bu iki katman **asla karıştırılmaz**.

---

## Core Data Model

### 1. ExecutionStatus

```python
class ExecutionStatus(Enum):
    SUCCESS = "success"              # Tool çalıştı, exit code OK
    FAILED = "failed"                # Tool çalışmadı (runtime error)
    PARTIAL_SUCCESS = "partial"      # Tool çalıştı ama parse başarısız
```

---

### 2. ParseStatus

```python
class ParseStatus(Enum):
    PARSED = "parsed"                # Output başarıyla parse edildi
    PARSE_FAILED = "parse_failed"    # Parser exception aldı
    EMPTY_OUTPUT = "empty_output"    # Tool çalıştı ama anlamlı çıktı yok
```

---

### 3. ToolExecutionResult

```python
class ToolExecutionResult(BaseModel):
    execution_id: str                # UUID
    stage_id: str                    # Planner stage reference
    tool_id: str                     # Registry tool id
    target: str                      # IP / CIDR / URL
    
    execution_status: ExecutionStatus
    parse_status: ParseStatus
    
    entities_created: int            # Parse sonucu üretilen entity sayısı
    
    stdout_path: str                 # Raw output path (zorunlu)
    stderr_path: Optional[str]
    
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    
    error_message: Optional[str]     # Runtime veya parse error
```

---

## Parser Failure Policy (KİLİTLİ)

### Temel Karar

> **Parser exception = PARTIAL_SUCCESS**

Bu bir hata değil, **bilgi eksikliği** durumudur.

---

### Davranış Matrisi

| Durum                 | execution_status | parse_status | Knowledge State | History      |
| --------------------- | ---------------- | ------------ | --------------- | ------------ |
| Tool crash            | FAILED           | —            | ❌ Güncellenmez  | ✅ Kaydedilir |
| Tool OK, parse OK     | SUCCESS          | PARSED       | ✅ Güncellenir   | ✅ Kaydedilir |
| Tool OK, parse fail   | PARTIAL_SUCCESS  | PARSE_FAILED | ❌ Güncellenmez  | ✅ Kaydedilir |
| Tool OK, empty output | SUCCESS          | EMPTY_OUTPUT | ❌ Güncellenmez  | ✅ Kaydedilir |

---

### Kritik Kurallar

* **Raw output her zaman saklanır**
* Parser fail → entity eklenmez
* Planner **asla** “entity yok” varsayımı yapmaz
* Planner **execution history’ye bakar**

---

## ExecutionState API (History Tarafı)

```python
class ExecutionState:

    def record_execution(self, result: ToolExecutionResult) -> None:
        """Her tool run SONRASINDA zorunlu çağrılır"""
        pass

    def has_tool_executed(self, tool_id: str, target: str) -> bool:
        """Bu tool bu hedefte daha önce çalıştı mı?"""
        pass

    def last_execution(self, tool_id: str, target: str) -> Optional[ToolExecutionResult]:
        """Son execution sonucunu döner"""
        pass

    def has_successful_parse(self, tool_id: str, target: str) -> bool:
        """PARSED execution var mı?"""
        pass
```

---

## Planner Integration Rules

Planner **entity state yerine execution history’yi** kullanır:

### Yanlış (YASAK)

```python
if not state.get_open_ports(host):
    skip_port_dependent_stages()
```

### Doğru (ZORUNLU)

```python
if not state.has_successful_parse("nmap_syn_scan", host):
    skip_port_dependent_stages()
```

---

## Conditional Stage Examples

```python
Stage(
    tactical_intent=PORT_SCAN,
    condition=lambda state: not state.has_tool_executed("nmap_syn_scan", target)
)

Stage(
    tactical_intent=VULN_SCAN,
    condition=lambda state: state.has_successful_parse("nmap_syn_scan", target)
)
```

---

## Transaction & Atomicity Policy

* **Tool execution + history write atomik değildir**
* **Parser output → entity insert → transaction** zorunludur
* History kaydı **her durumda** yazılır
* Entity insert **transaction içinde** yapılır

```python
# Pseudocode
result = execute_tool(...)
state.record_execution(result)

if result.parse_status == PARSED:
    with state.transaction():
        state.add_entities(parsed_entities)
```

---

## Debug & Audit Guarantees

Bu model sayesinde:

* “Tool çalıştı ama neden ilerlemedi?” → history’den cevap
* Parser bug → raw output replay edilebilir
* Yanlış stage skip → deterministic olarak izlenebilir
* Legal / audit trail → zaman damgalı execution kayıtları

---

## Sprint 1 Scope Boundary

### Sprint 1’de VAR

* ExecutionStatus / ParseStatus
* ToolExecutionResult
* History storage (SQLite)
* History query API
* Planner integration (history-aware)

### Sprint 1’de YOK

* Execution replay
* Retry policies
* Parallel execution history
* Advanced metrics

---

## Final Lock

Bu doküman:

* Parser base class
* ExecutionState
* Planner condition logic

için **tek referans**tır.

Bu kurallar Sprint 1 boyunca **değiştirilemez**.

---