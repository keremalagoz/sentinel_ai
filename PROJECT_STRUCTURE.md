# SENTINEL AI - Proje Yapısı (Sadeleştirilmiş)

**Versiyon**: Action Planner v2.1 - Sprint 3.6 (Backend Agent-Chat Foundation)  
**Tarih**: 4 Mart 2026  
**Mimari**: Local-Only LLM (Qwen 2.5 3B) + 2-Asamali Intent Resolution + Deterministic Execution + Backend Session Memory

> Not: Bu doküman sadeleştirme sürecindedir. Öncelik, mevcut çalışma mimarisi ve aktif modüllerin net gösterimidir.

---

## Hızlı Mimari Özeti

Ana akış:

`User Input -> Keyword Pre-Filter -> [Stage 1: Category] -> [Stage 2: Sub-Intent] -> Tool Registry -> Command Builder -> ToolManager -> Parser -> SQLite`

Sprint 3.6 backend chat akışı:

`Session -> Turn History -> Context Enrichment -> Intent Resolution -> Safe Command Suggestion`

Sistem garantileri:
- Queue backpressure
- Global/per-tool concurrency limit
- Local LLM timeout/retry/backoff
- Registry drift guard
- Runtime telemetry (`queue_wait_ms`, `tool_run_ms`)

---

## Dizin Yapısı (Özet)

```
sentinel_root/
├── main.py                      # Production Entry Point (Docker + Local AI)
├── requirements.txt             # Python bağımlılıkları
├── docker-compose.yml           # Docker orchestration
├── README.md                    # Proje ana dokümantasyonu
├── PROJECT_STRUCTURE.md         # Proje yapısı ve kılavuz
├── son_durum.md                 # Proje durum raporu
├── data/                        # Veri klasörü
│   └── databases/               # SQLite veritabanı dosyaları
│
├── src/                         # Ana kaynak kodu
│   ├── ai/                      # AI Modülleri (Local-only)
│   │   ├── orchestrator.py      # AI Orchestrator (Local-Only, feature flag)
│   │   ├── intent_resolver.py   # Flat intent detection (LLM -> intent)
│   │   ├── hierarchical_resolver.py # 2-Asamali intent (Category -> Sub-Intent)
│   │   ├── keyword_filter.py    # Keyword pre-filter + cross-validation
│   │   ├── command_builder.py   # Komut parametreleri oluşturucu
│   │   ├── schemas.py           # AI veri modelleri (Pydantic) + CategoryType
│   │   └── tool_registry.py     # Tool kayıt sistemi
│   │
│   ├── core/                    # Core Sistemler
│   │   ├── sqlite_backend.py    # SQLite Backend (Hybrid JSON+FK schema)
│   │   ├── conversation_memory.py # Session/turn bazli chat hafizasi (Sprint 3.6)
│   │   ├── entity_id_generator.py # Canonical Entity ID generator
│   │   ├── parser_framework.py  # Parser framework + 10 parser
│   │   ├── tool_base.py         # BaseTool + 10 tool implementation
│   │   ├── tool_integration.py  # IntegratedTool + ToolManager (queue/backpressure)
│   │   ├── sentinel_coordinator.py # UI-ToolManager bridge
│   │   ├── process_manager.py   # QProcess tabanlı process yonetimi
│   │   ├── docker_runner.py     # Docker container runner
│   │   ├── execution_manager.py # Execution state management (Docker/Native)
│   │   ├── validators.py        # Input validation (IP/domain/shell injection)
│   │   ├── cleaner.py           # Secure file cleanup
│   │   └── adapters/            # (Bos - Sprint 4 icin)
│   │
│   ├── application/             # Application facade katmani
│   │   ├── __init__.py
│   │   ├── backend_gateway.py   # UI-Backend facade (guvenlik katmanli)
│   │   └── api_server.py        # API modu (deterministic execute + chat/session endpointleri)
│   │
│   ├── ui/                      # UI Bilesenleri
│   │   ├── main_window.py       # Ana pencere (unified header)
│   │   ├── chat_interface.py    # Chat & CommandCard paneli
│   │   ├── terminal_view.py     # Multi-session terminal emulator
│   │   ├── settings_dialog.py   # Ayarlar diyalogu
│   │   └── styles.py            # UI renk ve font tanimlari
│   │
│   ├── plugins/                 # Plugin sistemi (gelecek)
│   │   └── .gitkeep
│   │
│   └── tests/                   # Test Suite (242 test)
│       ├── test_sprint1.py      # Sprint 1 main test suite
│       ├── test_sprint1_week1.py # Week 1 tests (backend + entity ID)
│       ├── test_sprint1_week2.py # Week 2 tests (parser + tool + integration)
│       ├── test_parser_framework.py # Parser isolated tests
│       ├── test_action_planner_v2.py # Action Planner v2 tests
│       ├── test_integration.py  # Full integration tests
│       ├── test_ui_integration.py # UI integration test window
│       ├── test_new_tools.py    # ToolManager + parser + telemetry + callback safety
│       ├── test_advanced_parsers.py # Genis parser senaryolari
│       ├── test_registry_consistency.py # Registry drift guard testleri
│       ├── test_ui_backend_boundary.py # UI-Backend boundary + guvenlik testleri
│       ├── test_backend_chat_session.py # Sprint 3.6 backend chat/session testleri
│       └── test_hierarchical_resolver.py # 2-asamali resolver testleri (57 test)
│
├── docs/                        # Teknik Dokümantasyon
│   ├── AGENT_RULES.md          # AI agent kurallari ve kisitlamalari
│   ├── entity_id_strategy.md   # Entity ID tasarim kararlari
│   ├── execution_history_model.md # Execution history veri modeli
│   ├── execution_state_model.md # Execution state management
│   ├── sprint_roadmap.md       # Sprint plani ve kapsam
│   ├── sprint_3_2_plan.md      # Sprint 3.2 detayli plan
│   ├── sprint_3_6_plan.md      # Sprint 3.6 detayli plan
│   ├── sprint_4_plan.md        # Sprint 4 detayli plan
│   ├── sprint1_ready.md        # Sprint 1 completion raporu
│   ├── conversation_audit_report.md # Kapsamli audit raporu
│   └── sqlite_schema.md        # SQLite veritabani semasi
│
├── temp/                        # Geçici Dosyalar
│   └── sentinel_safe/          # Güvenli sandbox klasörü
├── scripts/                     # Yardımcı scriptler
│   ├── intent_benchmark.py
│   ├── p0_validation.py
│   └── validate_ui.py
│
├── docker/                      # Docker Konfigürasyonları
│   ├── api/                    # API container
│   ├── tools/                  # Security tools container
│   ├── ollama/                 # Ollama LLM container (Qwen 2.5 + legacy WRN)
│   └── whiterabbitneo/         # (Legacy) WhiteRabbitNeo container
│
├── models/                      # AI Model Dosyaları (.gitignore ile korunur)
│   ├── qwen2.5-3b-instruct-q4.gguf  # Qwen 2.5 3B (~1.84 GB) - Ana model
│   ├── Modelfile.qwen2.5             # Qwen Modelfile (SENTINEL system prompt)
│   ├── whiterabbitneo-7b-q4.gguf     # WhiteRabbitNeo 7B (~4.47 GB) - Yedek
│   └── Modelfile.whiterabbitneo      # WhiteRabbitNeo Modelfile
└── ...

```

---

## Entry Points (Kısa)

### **main.py** - Production Mode
- Docker + local AI ile gerçek komut yürütümü
- Ana kullanım: production güvenlik testleri

---

## Test Dosyaları

### **src/tests/test_sprint1.py**
Sprint 1 (Action Planner v2.1) main test suite

**Test Sayısı**: 59 + 15 (yeni testler)  
**Kapsam**:
- SQLite Backend (29 unit tests)
- Entity ID Generator (unit tests)
- Parser Framework (21 parser tests)
- Tool Base (tool execution tests)
- Integration Layer (9 integration tests)

**Çalıştırma**:
```powershell
python -m pytest src/tests/test_sprint1.py -v
```

---

### **src/tests/test_sprint1_week1.py**
Week 1: Backend + Entity ID tests

**Odak**: SQLite backend ve entity ID generation  
**Çalıştırma**:
```powershell
python -m pytest src/tests/test_sprint1_week1.py -v
```

---

### **src/tests/test_sprint1_week2.py**
Week 2: Parser + Tool + Integration tests

**Odak**: Parser framework, tool execution, end-to-end workflow  
**Çalıştırma**:
```powershell
python -m pytest src/tests/test_sprint1_week2.py -v
```

---

### **src/tests/test_parser_framework.py**
Isolated parser tests

**Odak**: PingParser, NmapPingSweepParser, NmapPortScanParser  
**Çalıştırma**:
```powershell
python -m pytest src/tests/test_parser_framework.py -v
```

---

### **src/tests/test_action_planner_v2.py**
Action Planner v2 specific tests

**Odak**: ToolManager, IntegratedTool, policy enforcement  

---

### **src/tests/test_integration.py**
Full integration tests

**Odak**: End-to-end workflow: Tool → Parser → Backend → UI signals  

---

### **src/tests/test_ui_integration.py**
UI integration test window (PyQt6)

**Ne yapar**: Minimal test window, SentinelCoordinator + TerminalView entegrasyonu

**Özellikler**:
- 4 test butonu (Ping, Sweep, Portscan, Stats)
- Gerçek tool execution
- Terminal output display
- Backend stats görüntüleme

**Çalıştırma**:
```powershell
python src/tests/test_ui_integration.py
```

**Use Case**: UI entegrasyonu test, tool çıktılarını görsel kontrol

---

## Core Modüller

### **src/core/sqlite_backend.py**
SQLite Backend - Hybrid JSON+FK schema

**Sorumluluklar**:
- Entity storage (host, port, service, etc.)
- Execution history tracking
- Checkpoint/restore (state management)
- TTL pruning (eski kayıtları temizleme)
- Query interface (get_entities, search)

**Veritabanı Tabloları**:
- `entities`: Entity storage (JSON data + normalized fields)
- `entity_relationships`: Entity ilişkileri (FK-based)
- `tool_executions`: Execution history

**API**:
```python
backend = SQLiteBackend("sentinel.db")
backend.store_entity(entity)
backend.get_entities(entity_type="host")
backend.record_execution(result)
```

---

### **src/core/entity_id_generator.py**
Canonical Entity ID Generator

**Sorumluluklar**:
- Deterministic ID generation (collision-free)
- 9 entity type support
- Deduplication (aynı entity tekrar eklenmez)

**Desteklenen Entity Tipleri**:
1. `host` - IP/hostname
2. `port` - Host + port kombinasyonu
3. `service` - Port + service adı
4. `vulnerability` - Host + CVE/vuln type
5. `url` - Tam URL
6. `credential` - Username + host
7. `file` - Path + hash
8. `dns_record` - Domain + record type
9. `ssl_certificate` - Hostname + serial

**API**:
```python
entity_id = EntityIDGenerator.generate("host", "192.168.1.1")
# → "host:192.168.1.1"
```

---

### **src/core/parser_framework.py**
Parser Framework + 10 Parser Implementation

**Sorumluluklar**:
- Unified parser interface (BaseParser)
- Tool output -> structured entities
- PARTIAL_SUCCESS policy (bazi hatalar tolere edilir)
- 5 helper method (IP extraction, port parsing, etc.)

**Parsers**:
1. **PingParser**: Ping output -> host entities
2. **NmapPingSweepParser**: Nmap -sn -> multiple hosts
3. **NmapPortScanParser**: Nmap -sT -> host + ports + services
4. **NmapServiceDetectionParser**: Nmap -sV -> service version detection
5. **NmapVulnScanParser**: Nmap --script vuln -> vulnerability entities
6. **SslScanParser**: SSL/TLS certificate + cipher analysis
7. **GobusterDirParser**: Directory brute-force sonuclari
8. **SubdomainEnumParser**: Subdomain enumeration
9. **DnsLookupParser**: DNS record cozumlemesi
10. **WebAppScanParser**: Web uygulama tarama sonuclari

**API**:
```python
parser = PingParser()
result = parser.parse(raw_output, target="192.168.1.1")
# → ParserResult(entities=[...], status=SUCCESS)
```

---

### **src/core/tool_base.py**
BaseTool + 10 Tool Implementations (QProcess-based)

**Sorumluluklar**:
- Async tool execution (QProcess)
- Timeout handling + adaptive timeout estimation
- Signal-based output streaming
- 10 tool implementation

**Tools**:
1. **PingTool**: System ping
2. **NmapPingSweepTool**: Nmap ping sweep (`-sn`)
3. **NmapPortScanTool**: Nmap port scan (`-sT -p`)
4. **NmapServiceDetectionTool**: Nmap service detection (`-sV`)
5. **NmapVulnScanTool**: Nmap vulnerability scan (`--script vuln`)
6. **SslScanTool**: SSL/TLS analiz
7. **GobusterDirTool**: Directory brute-force
8. **SubdomainEnumTool**: Subdomain enumeration
9. **DnsLookupTool**: DNS record query
10. **WebAppScanTool**: Web uygulama tarama

**API**:
```python
tool = PingTool()
tool.execute(target="8.8.8.8", count=4)
# Signals: started, output, finished, error
```

---

### **src/core/tool_integration.py**
IntegratedTool + ToolManager

**Sorumluluklar**:
- Tool + Parser + Backend orchestration
- End-to-end workflow
- Signal routing

**Workflow**:
```
ToolManager.execute_tool()
    ↓
IntegratedTool (Tool + Parser + Policy)
    ↓
Tool.execute() → Parser.parse() → Backend.store()
    ↓
Signals → UI Update
```

**API**:
```python
manager = ToolManager(backend)
result = manager.execute_tool("ping", target="8.8.8.8", count=4)
```

---

### **src/core/sentinel_coordinator.py**
SentinelCoordinator - UI ↔ ToolManager Bridge

**Sorumluluklar**:
- UI ve ToolManager arasında köprü
- Qt Signal routing (PyQt6)
- 3 tool registration (ping, sweep, portscan)
- Backend stats query

**Signals**:
- `tool_started(tool_id, execution_id)`
- `tool_output(tool_id, output_chunk)`
- `tool_completed(tool_id, result)`
- `tool_error(tool_id, error_message)`

**API**:
```python
coordinator = SentinelCoordinator(db_path="sentinel.db")
coordinator.execute_ping(target="8.8.8.8", count=4)
coordinator.get_backend_stats()
```

---

### **src/core/process_manager.py**
AdvancedProcessManager (QProcess wrapper)

**Sorumluluklar**:
- Process lifecycle management
- Output streaming (stdout/stderr)
- Docker execution support
- ExecutionManager entegrasyonu

**Özellikler**:
- Auth handling (sudo/docker)
- Cross-platform (Windows/Linux)
- Signal-based notifications

---

### **src/core/docker_runner.py**
DockerRunner - Container execution

**Sorumluluklar**:
- Docker container başlatma/durdurma
- Volume mounting
- Network configuration
- Container cleanup

---

## AI Modülleri

### **src/ai/orchestrator.py**
AIOrchestrator - Local AI System

**Sorumluluklar**:
- Intent detection (flat + hierarchical dual-path)
- Tool selection
- Command generation
- Local-only: Qwen 2.5 3B / Ollama
- Feature flag: `SENTINEL_USE_HIERARCHICAL` (flat/hierarchical secimi)

**API**:
```python
orchestrator = get_orchestrator()
response = orchestrator.process("192.168.1.1'i tara", target="192.168.1.1")
# → AIResponse(command=Command(...), message="...")
```

---

### **src/ai/hierarchical_resolver.py**
HierarchicalResolver - 2 Asamali Intent Cozumleme (Sprint 3.3)

**Sorumluluklar**:
- Stage 1: Kullanici girdisini 5 kategoriye siniflandir (scanning, web, recon, attack, info)
- Stage 2: Kategori icindeki spesifik intent'i belirle (16 intent)
- Keyword pre-filter bypass (Stage 1 atlar, dogrudan Stage 2'ye gecer)
- Keyword override: LLM yerine keyword intent_type kullanilir, LLM sadece NER
- Retry/backoff, singleton pattern

**Pipeline**:
```
User Input -> KeywordPreFilter -> [Stage 1: Category] -> [Stage 2: Sub-Intent] -> Intent
```

---

### **src/ai/keyword_filter.py**
KeywordPreFilter - Regex tabanli hizli intent on-eleme (Sprint 3.2)

**Sorumluluklar**:
- 16 regex pattern ile keyword tabanli intent tahmini
- LLM cross-validation
- INFO_QUERY onceligi (soru kaliplari aksiyon keyword'lerinden once)
- Chitchat/selamlama yakalama (UNKNOWN)

---

### **src/ai/intent_resolver.py**
IntentResolver - Flat LLM tabanli intent tespiti

**Sorumluluklar**:
- Kullanıcı intent'i tespit etme (tek asamali, 16 intent)
- Strict JSON doğrulama
- Context tracking
- Timeout/retry/backoff

---

### **src/ai/command_builder.py**
CommandBuilder - Komut parametreleri oluşturma

**Sorumluluklar**:
- Tool parametrelerini hazırlama
- Template filling
- Validation

---

## UI Modülleri

### **src/ui/terminal_view.py**
TerminalView - Terminal emülatörü (PyQt6)

**Sorumluluklar**:
- Command input
- Output display (colored)
- Tool integration (coordinator parameter)
- Process manager integration
- Mode tracking (idle, busy, tool_running)

**API**:
```python
terminal = TerminalView(process_manager, coordinator=coordinator)
terminal.start_tool("ping", target="8.8.8.8", count=4)
```

---

### **src/ui/styles.py**
UI Stilleri - Renk ve font tanımları

**Tanımlar**:
- `Colors`: Tüm UI renkleri (dark theme)
- `Fonts`: Font aileleri (mono, sans)

---

## Dokümantasyon Dosyaları

### **docs/AGENT_RULES.md**
AI agent kuralları ve kısıtlamaları

**İçerik**: Agent davranış kuralları, kod standartları, commit kuralları

---

### **docs/entity_id_strategy.md**
Entity ID tasarım kararları

**İçerik**: Canonical ID generation stratejisi, collision handling

---

### **docs/execution_history_model.md**
Execution history veri modeli

**İçerik**: Tool execution tracking, history query

---

### **docs/execution_state_model.md**
Execution state management

**İçerik**: Checkpoint/restore, state recovery

---

### **docs/sprint1_ready.md**
Sprint 1 completion raporu

**İçerik**: Sprint 1 özeti, test sonuçları, commit listesi

---

### **docs/sqlite_schema.md**
SQLite veritabanı şeması

**İçerik**: 3 tablo tanımı, indeksler, migration notları

---

## Docker Yapısı

### **docker-compose.yml**
Docker orchestration

**Servisler**:
- `ollama-service`: Qwen 2.5 3B model server (primary, 1.9 GB)
- `tools-service`: Security tools container (nmap, gobuster, etc.)
- `api-service`: Sentinel API

---

### **docker/ollama/Dockerfile**
Ollama LLM container (Sprint 3.3)

**İçerik**: Ollama + Qwen 2.5 3B (primary) + WhiteRabbitNeo (legacy, optional)
**Env**: `SENTINEL_MODEL=qwen2.5` (qwen2.5 | whiterabbitneo | both)

---

### **docker/tools/Dockerfile**
Security tools container

**İçerik**: nmap, gobuster, nikto, dirb, sqlmap, etc.

---

### **docker/whiterabbitneo/** (Legacy)
Eski WhiteRabbitNeo container — geriye uyumluluk için korunuyor

---

## Bağımlılıklar

### **requirements.txt**
Python paketleri

**Ana Paketler**:
- `PyQt6`: UI framework
- `pydantic`: Veri validasyonu
- `defusedxml`: Güvenli XML işleme
- `fastapi`: API server
- `uvicorn`: ASGI server

**Kurulum**:
```powershell
pip install -r requirements.txt
```

---

## Veritabanı Dosyaları

### **data/databases/**
Uygulama veritabanları bu klasör altında tutulur.

Örnekler:
- `data/databases/sentinel_state.db`
- `data/databases/sentinel_dev.db`
- `data/databases/sentinel_production.db`

**Not**: `.gitignore` ile ignore edilir, commit edilmez

---

## Geliştirme Workflow

### 1. UI Integration Test
```powershell
python src/tests/test_ui_integration.py
# Ping, Sweep, Portscan butonları test et
```

### 2. Unit Tests
```powershell
python -m pytest src/tests/test_sprint1.py -v
# güncel testleri çalıştır
```

### 3. Production Test
```powershell
python main.py
# Docker'ı başlat, local AI test et
```

---

## Proje Durumu (4 Mart 2026)

### Tamamlanan Sprintler

**Sprint 1 - Action Planner v2.1** (9 commit, 59/59 test):
- SQLite Backend (Hybrid JSON+FK)
- Entity ID Generator (9 entity type)
- Parser Framework (3 parser)
- Tool Base (3 tool)
- Integration Layer (ToolManager + IntegratedTool)

**Sprint 3.1 - Stabilizasyon / Sertlestirme**:
- Queue backpressure, global/per-tool concurrency limit
- Local LLM timeout/retry/backoff
- Registry drift guard, runtime telemetry

**Sprint 3.2 - Optimizasyon ve Platform Hazirligi** (22/22 gorev):
- Track A: Kritik Bugfix (P0)
- Track B: Linux Platform Uyumu
- Track C: AI Olceklenme Altyapisi (keyword filter, benchmark, etc.)
- Track D: Kod Kalitesi / Teknik Borc

**Sprint 3.3 - Hybrid LLM Motoru** (10/10 gorev, +57 test):
- 2-Asamali Intent Resolution (Category -> Sub-Intent)
- Model degisimi: WhiteRabbitNeo 7B -> Qwen 2.5 3B
- Keyword override: LLM sadece NER, intent keyword'den gelir
- Benchmark: %100 dogruluk (30/30), hierarchical mod
- 242 test toplam

**Sprint 3.6 - Backend Agent-Chat Foundation** (6/6 gorev):
- UI degisimi olmadan backend session-memory chat eklendi
- `conversation_memory.py` ile kalici session/turn tablolari devreye alindi
- `api_server.py` chat endpointleri eklendi (`/api/chat/session`, `/api/chat/turn`, `/api/chat/history/{session_id}`)
- Orchestrator `process_v2` session-aware hale getirildi
- Hedefli backend dogrulama: 21 test yesil (2 yeni + 19 boundary regresyon)

---

### Devam Eden Isler

**Sprint 4** — Veri Adaptasyonu (`models.py` + `nmap_adapter.py`)  
**Sprint 5** — Oneri Motoru  
**Sprint 6** — Plugin Sistemi ve Final Build

---

## 🚦 Hızlı Komutlar

```powershell
# Production
python main.py

# UI Test Window
python src/tests/test_ui_integration.py

# Sprint 1 Tests
python -m pytest src/tests/test_sprint1.py -v

# Tüm Testler
python -m pytest src/tests/ -v

# Backend Stats (CLI)
python -c "from src.core.sqlite_backend import SQLiteBackend; b = SQLiteBackend('data/databases/sentinel_dev.db'); print(b.get_stats())"

# Nmap Version Check
nmap --version
```

---

## İlgili Dosyalar

- [README.md](README.md) - Genel proje tanıtımı
- [NMAP_KURULUM.md](NMAP_KURULUM.md) - Nmap kurulum rehberi
- [docs/sprint1_ready.md](docs/sprint1_ready.md) - Sprint 1 raporu
- [docs/sqlite_schema.md](docs/sqlite_schema.md) - Veritabanı şeması

---

**Son Güncelleme**: 4 Mart 2026  
**Versiyon**: Sprint 3.6 Complete + Backend Session-Memory Chat  
**Sonraki Hedef**: Sprint 4 - Veri Adaptasyonu ve Parsing
