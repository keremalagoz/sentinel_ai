# Sprint 1 Pre-Implementation Checklist

**Date:** 20 Ocak 2026  
**Status:** ✅ READY TO START

---

## Sprint 1 Locked Design Decisions

All architectural decisions finalized and documented. Implementation can begin.

### 1. Entity ID Generation Strategy ✅

**Document:** [entity_id_strategy.md](entity_id_strategy.md)

**Status:** LOCKED

**Key Decisions:**
- Merkezi `EntityIDGenerator` class
- Canonical ID formats (host, port, service, vuln, web, dns, cert, cred, file)
- Parser'lar override yapamaz
- Deduplication bu stratejiye dayanır
- Collision = Merge logic

**Blocker Risk:** Eliminated

---

### 2. SQLite Backend Schema ✅

**Document:** [sqlite_schema.md](sqlite_schema.md)

**Status:** LOCKED

**Key Decisions:**
- Hybrid approach: JSON blob + FK relationships
- 3 tables: `entities`, `entity_relationships`, `tool_executions`
- Transaction policy: Atomic batch insert with rollback
- TTL & pruning: Auto-prune old entities (default 1 hour)
- Checkpoint/restore: SQLite file copy

**Blocker Risk:** Eliminated

---

### 3. Execution History Model ✅

**Document:** [execution_history_model.md](execution_history_model.md)

**Status:** LOCKED

**Key Decisions:**
- Knowledge State ≠ Execution History State
- ExecutionStatus: SUCCESS | FAILED | PARTIAL_SUCCESS
- ParseStatus: PARSED | PARSE_FAILED | EMPTY_OUTPUT
- Parser fail → PARTIAL_SUCCESS (not error)
- Raw output always saved
- Planner uses history, not entity count

**Blocker Risk:** Eliminated

---

### 4. Execution Policy - Safe by Default ✅

**Document:** [src/ai/execution_policy.py](../src/ai/execution_policy.py)

**Status:** LOCKED

**Key Decisions:**
- `allow_persistent_changes = False` (IMMUTABLE Sprint 1)
- `confirm_before_tactics = [EXPLOIT_WEAKNESS, CREDENTIAL_BRUTE_FORCE]` (IMMUTABLE Sprint 1)
- High-risk tactics blocked or require confirmation
- Legal safety enforced

**Blocker Risk:** Eliminated

---

## Sprint 1 Scope (2 Weeks)

### Week 1: Foundation

**Schema & Infrastructure:**
- [ ] SQLite backend implementation
  - entities table
  - entity_relationships table
  - tool_executions table
  - Indexes
- [ ] EntityIDGenerator implementation
- [ ] Transaction support (batch insert + rollback)
- [ ] TTL & pruning logic
- [ ] Checkpoint/restore methods

**Testing:**
- [ ] Schema creation test
- [ ] Batch insert test (1000 entities)
- [ ] Transaction rollback test
- [ ] Query performance test (10k entities < 100ms)
- [ ] Duplicate entity merge test

### Week 2: Parser & Policy

**Parser Framework:**
- [ ] BaseParser class with ID generator integration
- [ ] ToolExecutionResult model
- [ ] Execution history API
  - record_execution()
  - has_tool_executed()
  - last_execution()
  - has_successful_parse()

**Tool Implementation (3 tools):**
- [ ] ping (ICMP check)
- [ ] nmap_ping_sweep (host discovery)
- [ ] nmap_port_scan (port enumeration)

**Policy Integration:**
- [ ] ExecutionPolicy validation
- [ ] Planner policy check (is_tactic_allowed_auto)
- [ ] Recommendation policy filter

**Testing:**
- [ ] Parser ID generation test
- [ ] Parser failure handling test (PARTIAL_SUCCESS)
- [ ] Execution history query test
- [ ] Policy enforcement test (blocked tactics)
- [ ] End-to-end test (3 tools)

---

## Sprint 1 Deferred to Sprint 2+

**Explicitly OUT of Scope:**
- ToolDefV2Extended metadata (22 fields)
- 12 additional tools
- Parallel execution
- Recommendation engine
- Constraint matcher
- LLM integration for edge cases
- Advanced metrics
- Execution replay

---

## Success Criteria

Sprint 1 complete when:

1. ✅ 3 tools working end-to-end (ping, nmap ping, nmap port scan)
2. ✅ Entity deduplication working (same host from 2 parsers = 1 entity)
3. ✅ Parser failure handling (PARTIAL_SUCCESS, raw output saved)
4. ✅ SQLite persistence (checkpoint/restore working)
5. ✅ Memory < 100MB for 10k entities
6. ✅ Query performance < 100ms for 10k entities
7. ✅ Policy enforcement (exploit blocked, confirmation required)
8. ✅ Unit test coverage > 80%

---

## Risk Mitigation

| Risk | Mitigation | Status |
|------|------------|--------|
| Memory explosion | SQLite backend + TTL pruning | ✅ Mitigated |
| Duplicate entities | Merkezi EntityIDGenerator | ✅ Mitigated |
| Parser failure | PARTIAL_SUCCESS policy + history | ✅ Mitigated |
| Legal risk | allow_persistent_changes=False | ✅ Mitigated |
| Complexity overload | ToolDef CORE only (8 fields) | ✅ Mitigated |
| Scope creep | Explicit Sprint 2 defer list | ✅ Mitigated |

---

## Architecture Review Sign-Off

**Critical Analysis Completed:** ✅  
**Showstopper Check:** ✅  
**Design Lock:** ✅  
**GO/NO-GO Decision:** ✅ GO

**Pre-Sprint 1 Documents:**
1. ✅ entity_id_strategy.md
2. ✅ sqlite_schema.md
3. ✅ execution_history_model.md
4. ✅ execution_policy.py

**Implementation Guidelines:**
- Kilitli kararlara aykırı değişiklik yasak
- Parser ID override yasak
- Transaction olmadan entity insert yasak
- Persistent change default deny
- Confirmation requirement immutable

---

## Feedback Format (Sprint 1)

Agent feedback during implementation:

✅ **"Bu doğru, devam"** - Compliant with locked decisions  
⚠️ **"Bu kilitli karara aykırı"** - Rule violation detected  
🔥 **"Bu implementation ileride patlar"** - Technical debt warning

---

## Sprint 1 Start

**Ready to start:** ✅ YES

**Next Step:** Begin Week 1 foundation implementation

**Sprint 1 başladı. Disiplinli implementation, mimari tartışma kapalı.**
