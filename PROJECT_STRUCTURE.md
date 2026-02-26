# SENTINEL AI - Proje Yapısı (Sadeleştirilmiş)

**Versiyon**: Action Planner v2.1 - Sprint 3.6 (Optimizasyon ve Platform Hazirlıgi)  
**Tarih**: 26 Subat 2026  
**Mimari**: Local-Only LLM + Deterministic Execution + Runtime Hardening

> Not: Bu doküman sadeleştirme sürecindedir. Öncelik, mevcut çalışma mimarisi ve aktif modüllerin net gösterimidir.

---

## Hızlı Mimari Özeti

Ana akış:

`User Input -> Intent Resolver -> Tool Registry -> Command Builder -> ToolManager -> Parser -> SQLite`

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
├── main_developer.py            # Developer Mode (Native Ollama)
├── api_server.py                # API modunda komut üretimi
├── requirements.txt             # Python bağımlılıkları
├── docker-compose.yml           # Docker orchestration
├── .env                         # Yerel/servis değişkenleri
├── .env.example                 # .env şablonu
├── README.md                    # Proje ana dokümantasyonu
├── PROJECT_STRUCTURE.md         # Proje yapısı ve kılavuz
├── son_durum.md                 # Proje durum raporu
├── data/                        # Veri klasörü
│
├── src/                         # Ana kaynak kodu
│   ├── ai/                      # AI Modülleri (Local-only)
│   │   ├── orchestrator.py      # AI Orchestrator (Local-Only)
│   │   ├── intent_resolver.py   # Intent detection (LLM -> intent)
│   │   ├── command_builder.py   # Komut parametreleri oluşturucu
│   │   ├── schemas.py           # AI veri modelleri (Pydantic)
│   │   └── tool_registry.py     # Tool kayıt sistemi
│   │
│   ├── core/                    # Core Sistemler
│   │   ├── sqlite_backend.py    # SQLite Backend (Hybrid JSON+FK schema)
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
│   │   └── backend_gateway.py   # UI-Backend facade (guvenlik katmanli)
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
│   └── tests/                   # Test Suite
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
│       └── test_ui_backend_boundary.py # UI-Backend boundary + guvenlik testleri
│
├── docs/                        # Teknik Dokümantasyon
│   ├── AGENT_RULES.md          # AI agent kurallari ve kisitlamalari
│   ├── entity_id_strategy.md   # Entity ID tasarim kararlari
│   ├── execution_history_model.md # Execution history veri modeli
│   ├── execution_state_model.md # Execution state management
│   ├── sprint_roadmap.md       # Sprint plani ve kapsam
│   ├── sprint_3_6_plan.md      # Sprint 3.6 detayli plan
│   ├── sprint1_ready.md        # Sprint 1 completion raporu
│   ├── conversation_audit_report.md # Kapsamli audit raporu
│   └── sqlite_schema.md        # SQLite veritabani semasi
│
├── temp/                        # Geçici Dosyalar
│   └── sentinel_safe/          # Güvenli sandbox klasörü
│
├── docker/                      # Docker Konfigürasyonları
│   ├── api/                    # API container
│   ├── tools/                  # Security tools container
│   └── whiterabbitneo/         # WhiteRabbitNeo container
│
├── models/                      # AI Model Dosyaları
│   ├── model1.gguf
│   ├── model2.gguf
│   ├── Modelfile.model1
│   ├── Modelfile.model2
│   ├── Modelfile.whiterabbitneo
│   └── whiterabbitneo-7b-q4.gguf
├── sentinel_production.db       # Production veritabanı
├── sentinel_dev.db             # Developer mode veritabanı
└── sentinel_state.db           # Test/default veritabanı

```

---

## Entry Points (Kısa)

### 1. **main.py** - Production Mode
- Docker + local AI ile gerçek komut yürütümü
- Ana kullanım: production güvenlik testleri

---

### 2. **main_developer.py** - Developer Mode
- Native Ollama ile geliştirme/deneme modu
- Ana kullanım: UI + AI akış geliştirme ve hızlı doğrulama

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
- Intent detection
- Tool selection
- Command generation
- Local-only: WhiteRabbitNeo/Ollama

**API**:
```python
orchestrator = get_orchestrator()
response = orchestrator.process("192.168.1.1'i tara", target="192.168.1.1")
# → AIResponse(command=Command(...), message="...")
```

---

### **src/ai/intent_resolver.py**
IntentResolver - LLM tabanli intent tespiti

**Sorumluluklar**:
- Kullanıcı intent'i tespit etme
- Strict JSON doğrulama
- Context tracking

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
- `whiterabbitneo-service`: WhiteRabbitNeo model server
- `tools-service`: Security tools container (nmap, gobuster, etc.)
- `api-service`: Sentinel API

---

### **docker/tools/Dockerfile**
Security tools container

**İçerik**: nmap, gobuster, nikto, dirb, sqlmap, etc.

---

### **docker/whiterabbitneo/Dockerfile**
WhiteRabbitNeo container

**İçerik**: Ollama + WhiteRabbitNeo model

---

## Bağımlılıklar

### **requirements.txt**
Python paketleri

**Ana Paketler**:
- `PyQt6`: UI framework
- `pydantic`: Veri validasyonu
- `python-dotenv`: Ortam değişkenleri
- `defusedxml`: Güvenli XML işleme
- `fastapi`: API server
- `uvicorn`: ASGI server

**Kurulum**:
```powershell
pip install -r requirements.txt
```

---

## Veritabanı Dosyaları

### **sentinel_production.db**
Production mode veritabanı (main.py)

### **sentinel_dev.db**
Developer mode veritabanı (main_developer.py)

### **sentinel_state.db**
Test/default veritabanı (test_ui_integration.py)

**Not**: `.gitignore` ile ignore edilir, commit edilmez

---

## Çevre Değişkenleri

### **.env**
Yerel/servis yapılandırma değişkenleri

**İçerik**:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=whiterabbitneo
```

**Not**: `.gitignore` ile korunur, commit edilmez

### **.env.example**
.env şablonu

**Kullanım**:
```powershell
Copy-Item .env.example .env
# .env dosyasını düzenle ve API key ekle
```

---

## Geliştirme Workflow

### 1. Developer Mode Test
```powershell
python main_developer.py
# Test butonlarına bas, integrated tools test et
```

### 2. UI Integration Test
```powershell
python src/tests/test_ui_integration.py
# Ping, Sweep, Portscan butonları test et
```

### 3. Unit Tests
```powershell
python -m pytest src/tests/test_sprint1.py -v
# güncel testleri çalıştır
```

### 4. Production Test
```powershell
python main.py
# Docker'ı başlat, local AI test et
```

---

## Proje Durumu (25 Şubat 2026)

### Tamamlanan Sprintler

**Sprint 1 - Action Planner v2.1** (9 commit, 59/59 test):
- SQLite Backend (Hybrid JSON+FK)
- Entity ID Generator (9 entity type)
- Parser Framework (3 parser)
- Tool Base (3 tool)
- Integration Layer (ToolManager + IntegratedTool)

**Öncelik 1 - UI Integration** (95% complete):
- SentinelCoordinator (bridge)
- TerminalView tool entegrasyonu
- Test butonları (developer mode only)
- Backend stats display
- main.py ve main_developer.py entegrasyonu

---

### 🔄 Devam Eden İşler

**Öncelik 2 - AI Orchestrator Integration** (next):
- AI Intent → Tool selection
- Otomatik tool çağrısı
- Stage-based planning
- Policy enforcement

---

### Gelecek Öncelikler

**Öncelik 3 - Additional Tools**:
- 7 yeni tool (toplam 10)
- Service detection
- Vulnerability scanning
- DNS enumeration
- SSL analysis
- Credential testing
- Web enumeration
- Exploit execution

---

## 🚦 Hızlı Komutlar

```powershell
# Production
python main.py

# Developer Mode
python main_developer.py

# UI Test Window
python src/tests/test_ui_integration.py

# Sprint 1 Tests
python -m pytest src/tests/test_sprint1.py -v

# Tüm Testler
python -m pytest src/tests/ -v

# Backend Stats (CLI)
python -c "from src.core.sqlite_backend import SQLiteBackend; b = SQLiteBackend('sentinel_dev.db'); print(b.get_stats())"

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

**Son Güncelleme**: 21 Ocak 2026  
**Versiyon**: Sprint 1 Complete + UI Integration  
**Sonraki Hedef**: Öncelik 2 - AI Orchestrator Integration
