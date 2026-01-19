# SQLite Backend Schema

## Purpose

ExecutionState persistence için SQLite backend schema tanımı.

**Core Principle:** Hybrid approach - JSON blob + FK relationships

**Neden Hybrid?**
- JSON blob → Entity schema değişikliği kolay (migration-free)
- FK relationships → Query performance (JOIN, index)
- Best of both worlds

---

## Schema Overview

```
┌─────────────────────────┐
│      entities           │  ← Core entity storage (JSON blob)
│  - id (PK)              │
│  - entity_type          │
│  - created_at           │
│  - updated_at           │
│  - confidence           │
│  - data (JSON)          │
└─────────────────────────┘
            │
            │ FK
            ▼
┌─────────────────────────┐
│  entity_relationships   │  ← Host→Port, Port→Service relationships
│  - parent_id (FK)       │
│  - child_id (FK)        │
│  - relationship_type    │
└─────────────────────────┘

┌─────────────────────────┐
│  tool_executions        │  ← Execution history (separate concern)
│  - execution_id (PK)    │
│  - tool_id              │
│  - stage_id             │
│  - status               │
│  - parse_status         │
│  - raw_output           │
│  - started_at           │
│  - completed_at         │
│  - entities_created     │
└─────────────────────────┘
```

---

## Table: `entities`

**Purpose:** Core entity storage - hosts, ports, services, vulnerabilities, etc.

**Schema:**

```sql
CREATE TABLE entities (
    id TEXT PRIMARY KEY,                -- EntityIDGenerator output (canonical)
    entity_type TEXT NOT NULL,          -- 'host', 'port', 'service', 'vulnerability', etc.
    created_at REAL NOT NULL,           -- Unix timestamp (float for precision)
    updated_at REAL NOT NULL,           -- Unix timestamp
    confidence REAL DEFAULT 1.0,        -- 0.0 - 1.0
    data JSON NOT NULL                  -- Pydantic BaseEntity.dict() → JSON
);

-- Indexes for query performance
CREATE INDEX idx_entity_type ON entities(entity_type);
CREATE INDEX idx_created_at ON entities(created_at);
CREATE INDEX idx_updated_at ON entities(updated_at);
CREATE INDEX idx_confidence ON entities(confidence);
```

**Example Rows:**

```json
// Host entity
{
  "id": "host_192_168_1_10",
  "entity_type": "host",
  "created_at": 1737328800.123,
  "updated_at": 1737328800.123,
  "confidence": 0.95,
  "data": {
    "ip_address": "192.168.1.10",
    "is_alive": true,
    "hostname": "example.local",
    "os_type": "Linux"
  }
}

// Port entity
{
  "id": "host_192_168_1_10_port_80_tcp",
  "entity_type": "port",
  "created_at": 1737328900.456,
  "updated_at": 1737328900.456,
  "confidence": 1.0,
  "data": {
    "host_id": "host_192_168_1_10",
    "port": 80,
    "protocol": "tcp",
    "state": "open"
  }
}
```

**Design Rationale:**

- **JSON blob:** Entity schema flexible, no ALTER TABLE on schema change
- **Top-level metadata:** Query-critical fields (type, timestamp, confidence) for fast filtering
- **Pydantic serialization:** `.dict()` → JSON, `.parse_obj()` ← JSON

---

## Table: `entity_relationships`

**Purpose:** Entity relationships (Host→Port, Port→Service, DNS→Host, etc.)

**Schema:**

```sql
CREATE TABLE entity_relationships (
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (parent_id, child_id, relationship_type),
    FOREIGN KEY (parent_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (child_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- Indexes for bidirectional queries
CREATE INDEX idx_parent ON entity_relationships(parent_id, relationship_type);
CREATE INDEX idx_child ON entity_relationships(child_id, relationship_type);
```

**Relationship Types:**

| Type | Parent | Child | Example |
|------|--------|-------|---------|
| `has_port` | Host | Port | `host_192_168_1_10` → `host_192_168_1_10_port_80_tcp` |
| `has_service` | Port | Service | `host_192_168_1_10_port_80_tcp` → `..._service_http` |
| `has_vulnerability` | Service | Vulnerability | `..._service_http` → `..._vuln_cve_2024_1234` |
| `has_web_resource` | Service | WebResource | `..._service_http` → `..._web_hash_abc123` |
| `resolves_to` | DNS | Host | `dns_example_com` → `host_192_168_1_10` |

**Example Rows:**

```
parent_id                          | child_id                                    | relationship_type  | created_at
-----------------------------------|---------------------------------------------|-------------------|-------------
host_192_168_1_10                  | host_192_168_1_10_port_80_tcp              | has_port          | 1737328900.0
host_192_168_1_10_port_80_tcp      | host_192_168_1_10_port_80_tcp_service_http | has_service       | 1737329000.0
dns_example_com                    | host_192_168_1_10                          | resolves_to       | 1737329100.0
```

**Query Examples:**

```sql
-- Get all ports for a host
SELECT e.*
FROM entities e
JOIN entity_relationships r ON r.child_id = e.id
WHERE r.parent_id = 'host_192_168_1_10'
  AND r.relationship_type = 'has_port';

-- Get all services on a specific port
SELECT e.*
FROM entities e
JOIN entity_relationships r ON r.child_id = e.id
WHERE r.parent_id = 'host_192_168_1_10_port_80_tcp'
  AND r.relationship_type = 'has_service';

-- Get all vulnerabilities for a host (multi-level JOIN)
SELECT v.*
FROM entities v
JOIN entity_relationships r1 ON r1.child_id = v.id AND r1.relationship_type = 'has_vulnerability'
JOIN entities s ON s.id = r1.parent_id AND s.entity_type = 'service'
JOIN entity_relationships r2 ON r2.child_id = s.id AND r2.relationship_type = 'has_service'
JOIN entities p ON p.id = r2.parent_id AND p.entity_type = 'port'
JOIN entity_relationships r3 ON r3.child_id = p.id AND r3.relationship_type = 'has_port'
WHERE r3.parent_id = 'host_192_168_1_10';
```

---

## Table: `tool_executions`

**Purpose:** Execution history (separate from knowledge state)

**Schema:**

```sql
CREATE TABLE tool_executions (
    execution_id TEXT PRIMARY KEY,      -- UUID
    tool_id TEXT NOT NULL,              -- 'nmap_ping_sweep', 'nmap_port_scan', etc.
    stage_id INTEGER,                   -- Stage number in plan
    status TEXT NOT NULL,               -- 'success', 'failed', 'partial'
    parse_status TEXT NOT NULL,         -- 'parsed', 'parse_failed', 'empty_output'
    raw_output TEXT,                    -- Tool stdout+stderr (for debug/re-parse)
    started_at REAL NOT NULL,
    completed_at REAL NOT NULL,
    entities_created INTEGER DEFAULT 0, -- How many entities added to state
    error_message TEXT                  -- If status=failed or parse_status=parse_failed
);

CREATE INDEX idx_tool_id ON tool_executions(tool_id);
CREATE INDEX idx_stage_id ON tool_executions(stage_id);
CREATE INDEX idx_status ON tool_executions(status);
CREATE INDEX idx_started_at ON tool_executions(started_at);
```

**Example Rows:**

```json
// Successful execution
{
  "execution_id": "exec_abc123",
  "tool_id": "nmap_ping_sweep",
  "stage_id": 1,
  "status": "success",
  "parse_status": "parsed",
  "raw_output": "Starting Nmap...\nHost is up (0.001s latency)...",
  "started_at": 1737328800.0,
  "completed_at": 1737328805.0,
  "entities_created": 54,
  "error_message": null
}

// Parse failed (PARTIAL_SUCCESS)
{
  "execution_id": "exec_def456",
  "tool_id": "nmap_port_scan",
  "stage_id": 2,
  "status": "partial",
  "parse_status": "parse_failed",
  "raw_output": "Weird nmap output...",
  "started_at": 1737329000.0,
  "completed_at": 1737329120.0,
  "entities_created": 0,
  "error_message": "Parser exception: Unexpected format line 42"
}

// Tool execution failed
{
  "execution_id": "exec_ghi789",
  "tool_id": "gobuster",
  "stage_id": 3,
  "status": "failed",
  "parse_status": "empty_output",
  "raw_output": "",
  "started_at": 1737329200.0,
  "completed_at": 1737329201.0,
  "entities_created": 0,
  "error_message": "gobuster: command not found"
}
```

**Query Examples:**

```sql
-- Has tool already run?
SELECT * FROM tool_executions
WHERE tool_id = 'nmap_port_scan'
  AND status IN ('success', 'partial')
LIMIT 1;

-- Get last execution result for a tool
SELECT * FROM tool_executions
WHERE tool_id = 'nmap_ping_sweep'
ORDER BY completed_at DESC
LIMIT 1;

-- Get all failed executions for debugging
SELECT * FROM tool_executions
WHERE status = 'failed'
ORDER BY started_at DESC;
```

---

## Transaction Policy

### Atomic Batch Insert

**Rule:** Parser output = Single transaction

```python
class SQLiteBackend:
    def add_entities_batch(self, entities: List[BaseEntity]) -> int:
        """Atomic batch insert with transaction"""
        with self.connection:  # Auto-commit on success, rollback on exception
            cursor = self.connection.cursor()
            
            for entity in entities:
                cursor.execute(
                    "INSERT OR REPLACE INTO entities (id, entity_type, created_at, updated_at, confidence, data) VALUES (?, ?, ?, ?, ?, ?)",
                    (entity.id, entity.entity_type, entity.created_at, entity.updated_at, entity.confidence, entity.json())
                )
                
                # Add relationships
                for relationship in entity.relationships:
                    cursor.execute(
                        "INSERT OR IGNORE INTO entity_relationships (parent_id, child_id, relationship_type, created_at) VALUES (?, ?, ?, ?)",
                        (relationship.parent_id, relationship.child_id, relationship.type, time.time())
                    )
            
            return len(entities)
```

**Why Atomic?**
- Parse exception → Rollback → No partial state
- State consistency guaranteed
- Retry safety (idempotent)

---

## TTL & Pruning Strategy

### Entity TTL

**Rule:** Entity older than TTL → Deleted

```sql
-- Delete stale entities (default: 1 hour TTL)
DELETE FROM entities
WHERE updated_at < (unixepoch('now') - 3600);

-- Cascade delete: Relationships auto-deleted (ON DELETE CASCADE)
```

**Python Implementation:**

```python
class SQLiteBackend:
    def prune_stale_entities(self, ttl_seconds: int = 3600):
        """Delete entities older than TTL"""
        cutoff = time.time() - ttl_seconds
        
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM entities WHERE updated_at < ?", (cutoff,))
            deleted_count = cursor.rowcount
            
        return deleted_count
```

**Auto-Prune Policy:**
- Every 1000 entity inserts → Auto-prune
- Every 10 minutes → Auto-prune (background task)

---

## Checkpoint & Restore

### Checkpoint (Save State)

```python
class SQLiteBackend:
    def checkpoint(self, checkpoint_path: str):
        """Save current state to checkpoint file"""
        import shutil
        
        # SQLite file copy = Atomic checkpoint
        shutil.copy2(self.db_path, checkpoint_path)
```

**Usage:**
- End of each stage → Auto-checkpoint
- User command: "Save session"
- Crash recovery: Last checkpoint

### Restore (Load State)

```python
class SQLiteBackend:
    def restore(self, checkpoint_path: str):
        """Restore state from checkpoint"""
        import shutil
        
        # Close current connection
        self.connection.close()
        
        # Restore checkpoint file
        shutil.copy2(checkpoint_path, self.db_path)
        
        # Reconnect
        self.connection = sqlite3.connect(self.db_path)
```

**Usage:**
- Resume session after crash
- Team collaboration (share checkpoint file)
- Rollback to previous state

---

## Migration Strategy

### Sprint 1: New Schema

**Fresh start** - No backward compatibility

- Old in-memory state discarded
- New SQLite backend
- Clean entity IDs

### Sprint 2+: Schema Versioning

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);

INSERT INTO schema_version (version, applied_at) VALUES (1, unixepoch('now'));
```

**Migration script:**
```python
def migrate_schema(connection, from_version: int, to_version: int):
    if from_version == 1 and to_version == 2:
        # Add new column
        connection.execute("ALTER TABLE entities ADD COLUMN new_field TEXT")
    # ... more migrations
```

---

## Performance Considerations

### Index Strategy

**Query Patterns:**

| Query | Index Used |
|-------|------------|
| Get all hosts | `idx_entity_type` |
| Get recent entities | `idx_created_at` |
| Get high-confidence entities | `idx_confidence` |
| Get host's ports | `idx_parent` (relationships) |
| Get port's services | `idx_parent` (relationships) |

**Write Performance:**
- Batch insert: 1000 entities/sec (local SSD)
- Index overhead: ~10% slower writes (acceptable trade-off)

### Memory Footprint

**Target:** < 100MB for 10,000 entities

- SQLite cache: 10MB default
- Python object overhead: Minimal (JSON blob in DB)
- Index size: ~1MB per 10k entities

**Measurement:**
```python
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

---

## Backup Strategy

### Auto-Backup

```python
class SQLiteBackend:
    def auto_backup(self, backup_dir: str):
        """Periodic backup (every 10 minutes)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{backup_dir}/state_{timestamp}.db"
        self.checkpoint(backup_path)
```

**Retention Policy:**
- Keep last 10 backups
- Delete older backups
- Backup size: ~same as DB file

---

## Testing Requirements

### Sprint 1 Tests

1. **Schema Creation Test**
   - Create tables
   - Verify indexes
   - Check constraints

2. **Batch Insert Test**
   - Insert 1000 entities
   - Transaction rollback test (exception)
   - Duplicate handling test

3. **Query Performance Test**
   - 10k entities → Query < 100ms
   - Relationship JOIN test
   - Index usage verification

4. **TTL & Pruning Test**
   - Old entities deleted
   - Relationships cascade-deleted
   - Performance after pruning

5. **Checkpoint/Restore Test**
   - Save state
   - Restore state
   - State integrity verification

---

## Summary

| Feature | Implementation |
|---------|---------------|
| Entity Storage | JSON blob + metadata (id, type, timestamps, confidence) |
| Relationships | Separate FK table (parent_id, child_id, type) |
| Execution History | Separate table (tool_id, status, parse_status, raw_output) |
| Transaction | Atomic batch insert with rollback |
| TTL | Auto-prune old entities (default 1 hour) |
| Checkpoint | SQLite file copy (atomic) |
| Performance | Indexed queries < 100ms for 10k entities |
| Memory | < 100MB for 10k entities |

**Critical Rule:** Execution history ≠ Knowledge state (separate tables, separate concerns)
