# SENTINEL AI - Proje Yapısı ve Klavuzu

**Versiyon**: Sprint 1 Complete + UI Integration (Öncelik 1)  
**Tarih**: 21 Ocak 2026  
**Mimari**: Action Planner v2.1 (SQLite Backend + Integrated Tools)

---

## 📁 Dizin Yapısı

```
sentinel_root/
├── main.py                      # 🚀 Production Entry Point (Docker + Hibrit AI)
├── main_developer.py            # 🔧 Developer Mode (Mock + Native Ollama)
├── requirements.txt             # 📦 Python bağımlılıkları
├── docker-compose.yml           # 🐳 Docker orchestration
├── .env                         # 🔐 Çevre değişkenleri (API keys)
├── .env.example                 # 📝 .env şablonu
├── README.md                    # 📖 Proje ana dokümantasyonu
├── NMAP_KURULUM.md             # 🛠️ Nmap kurulum rehberi
│
├── src/                         # 📂 Ana kaynak kodu
│   ├── ai/                      # 🤖 AI Modülleri
│   │   ├── orchestrator.py      # AI Orchestrator (Hibrit: Local + Cloud)
│   │   ├── intent_resolver.py   # Intent detection & tool mapping
│   │   ├── command_builder.py   # Komut parametreleri oluşturucu
│   │   ├── policy_gate.py       # Risk politika kontrolü
│   │   ├── execution_policy.py  # Execution policy (izin sistemi)
│   │   ├── schemas.py           # AI veri modelleri (Pydantic)
│   │   └── tool_registry.py     # Tool kayıt sistemi
│   │
│   ├── core/                    # ⚙️ Core Sistemler
│   │   ├── sqlite_backend.py    # SQLite Backend (Hybrid JSON+FK schema)
│   │   ├── entity_id_generator.py # Canonical Entity ID generator
│   │   ├── parser_framework.py  # Parser framework + 3 parser
│   │   ├── tool_base.py         # BaseTool + 3 tool implementation
│   │   ├── tool_integration.py  # IntegratedTool + ToolManager
│   │   ├── sentinel_coordinator.py # UI-ToolManager bridge
│   │   ├── process_manager.py   # QProcess tabanlı process yönetimi
│   │   ├── docker_runner.py     # Docker container runner
│   │   ├── execution_manager.py # Execution state management
│   │   ├── validators.py        # Input validation
│   │   ├── cleaner.py           # Secure file cleanup
│   │   └── adapters/            # (Boş - gelecek için)
│   │
│   ├── ui/                      # 🎨 UI Bileşenleri
│   │   ├── terminal_view.py     # Terminal emülatörü (PyQt6)
│   │   └── styles.py            # UI renk ve font tanımları
│   │
│   ├── plugins/                 # 🔌 Plugin sistemi (gelecek)
│   │   └── .gitkeep
│   │
│   └── tests/                   # 🧪 Test Suite
│       ├── test_sprint1.py      # Sprint 1 main test suite (59 tests)
│       ├── test_sprint1_week1.py # Week 1 tests (backend + entity ID)
│       ├── test_sprint1_week2.py # Week 2 tests (parser + tool + integration)
│       ├── test_parser_framework.py # Parser isolated tests
│       ├── test_action_planner_v2.py # Action Planner v2 tests
│       ├── test_integration.py  # Full integration tests
│       └── test_ui_integration.py # UI integration test window
│
├── docs/                        # 📚 Teknik Dokümantasyon
│   ├── AGENT_RULES.md          # AI agent kuralları ve kısıtlamaları
│   ├── entity_id_strategy.md   # Entity ID tasarım kararları
│   ├── execution_history_model.md # Execution history veri modeli
│   ├── execution_state_model.md # Execution state management
│   ├── sprint1_ready.md        # Sprint 1 completion raporu
│   └── sqlite_schema.md        # SQLite veritabanı şeması
│
├── temp/                        # 🗂️ Geçici Dosyalar
│   ├── sentinel_safe/          # Güvenli sandbox klasörü
│   └── docs_archive/           # Eski/arşiv dokümanlar
│
├── docker/                      # 🐳 Docker Konfigürasyonları
│   ├── api/                    # API container
│   ├── llama/                  # Llama 3 container
│   ├── tools/                  # Security tools container
│   └── whiterabbitneo/         # WhiteRabbitNeo container
│
├── models/                      # 🧠 AI Model Dosyaları
│   ├── Modelfile.whiterabbitneo # Ollama modelfile
│   └── whiterabbitneo-7b-q4.gguf # Model weights (eğer varsa)
│
├── sentinel_production.db       # 💾 Production veritabanı
├── sentinel_dev.db             # 💾 Developer mode veritabanı
└── sentinel_state.db           # 💾 Test/default veritabanı

```

---

## 🚀 Entry Points (Başlangıç Dosyaları)

### 1. **main.py** - Production Mode
**Ne yapar**: Ana uygulama, hibrit AI + Docker containerlar ile çalışır

**Özellikler**:
- ✅ Docker Desktop gerektirir (VmmemWSL)
- ✅ Hibrit AI: Local Llama 3 + Cloud GPT-4o-mini
- ✅ Gerçek komutlar çalıştırır (nmap, gobuster, etc.)
- ✅ Docker'da security tools
- ✅ RAM: ~6-8GB (Docker + AI)
- ✅ SentinelCoordinator entegrasyonu (integrated tools)

**Çalıştırma**:
```powershell
python main.py
```

**Use Case**: Gerçek penetrasyon testleri, production deployment

---

### 2. **main_developer.py** - Developer Mode
**Ne yapar**: Geliştirme modu, mock execution + native Ollama

**Özellikler**:
- ✅ Docker gerektirmez (RAM tasarrufu)
- ✅ Native Ollama (localhost:11434)
- ✅ Mock execution (komutlar gerçekte çalışmaz)
- ✅ Integrated tools: **Gerçek çalışır** (ping, nmap - eğer kuruluysa)
- ✅ Test butonları (4 adet: Ping, Sweep, Portscan, Stats)
- ✅ RAM: ~2-3GB (Docker yok)
- ⚠️ Developer warnings/banners

**Çalıştırma**:
```powershell
python main_developer.py
```

**Use Case**: Geliştirme, test, düşük RAM, Docker sorunları

---

## 🧪 Test Dosyaları

### **src/tests/test_sprint1.py**
Sprint 1 (Action Planner v2.1) main test suite

**Test Sayısı**: 59  
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
UI integration test window (PySide6)

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

## ⚙️ Core Modüller

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
Parser Framework + 3 Parser Implementation

**Sorumluluklar**:
- Unified parser interface (BaseParser)
- Tool output → structured entities
- PARTIAL_SUCCESS policy (bazı hatalar tolere edilir)
- 5 helper method (IP extraction, port parsing, etc.)

**Parsers**:
1. **PingParser**: Ping output → host entities
2. **NmapPingSweepParser**: Nmap -sn → multiple hosts
3. **NmapPortScanParser**: Nmap -sT → host + ports + services

**API**:
```python
parser = PingParser()
result = parser.parse(raw_output, target="192.168.1.1")
# → ParserResult(entities=[...], status=SUCCESS)
```

---

### **src/core/tool_base.py**
BaseTool + 3 Tool Implementations (QProcess-based)

**Sorumluluklar**:
- Async tool execution (QProcess)
- Timeout handling
- Signal-based output streaming
- 3 tool implementation

**Tools**:
1. **PingTool**: System ping (cross-platform)
2. **NmapPingSweepTool**: Nmap ping sweep (`-sn`)
3. **NmapPortScanTool**: Nmap port scan (`-sT -p`)

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
- Policy enforcement (ExecutionPolicy)
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
- Qt Signal routing (PySide6)
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
- Mock execution (developer mode)

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

## 🤖 AI Modülleri

### **src/ai/orchestrator.py**
AIOrchestrator - Hibrit AI System

**Sorumluluklar**:
- Intent detection
- Tool selection
- Command generation
- Hibrit: Local Llama 3 (reasoning) + Cloud GPT-4o-mini (fallback)

**API**:
```python
orchestrator = get_orchestrator()
response = orchestrator.process("192.168.1.1'i tara", target="192.168.1.1")
# → AIResponse(command=Command(...), message="...")
```

---

### **src/ai/intent_resolver.py**
IntentResolver - Intent → Tool mapping

**Sorumluluklar**:
- Kullanıcı intent'i tespit etme
- Tool önerme
- Context tracking

---

### **src/ai/command_builder.py**
CommandBuilder - Komut parametreleri oluşturma

**Sorumluluklar**:
- Tool parametrelerini hazırlama
- Template filling
- Validation

---

### **src/ai/policy_gate.py**
PolicyGate - Risk kontrolü

**Sorumluluklar**:
- Risk seviyesi belirleme (LOW/MEDIUM/HIGH)
- Onay gereksinimi kontrolü
- Root yetki kontrolü

---

### **src/ai/execution_policy.py**
ExecutionPolicy - İzin sistemi

**Sorumluluklar**:
- Tool execution izni
- Stage-based restrictions
- Whitelist/blacklist

---

## 🎨 UI Modülleri

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

## 📚 Dokümantasyon Dosyaları

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

## 🐳 Docker Yapısı

### **docker-compose.yml**
Docker orchestration

**Servisler**:
- `llama`: Llama 3 model server
- `whiterabbitneo`: WhiteRabbitNeo model server
- `tools`: Security tools container (nmap, gobuster, etc.)
- `api`: Sentinel API (gelecek)

---

### **docker/tools/Dockerfile**
Security tools container

**İçerik**: nmap, gobuster, nikto, dirb, sqlmap, etc.

---

### **docker/llama/Dockerfile**
Llama 3 container

**İçerik**: Ollama + Llama 3 model

---

## 📦 Bağımlılıklar

### **requirements.txt**
Python paketleri

**Ana Paketler**:
- `PyQt6` / `PySide6`: UI framework
- `openai`: Cloud API
- `pydantic`: Veri validasyonu
- `pytest`: Test framework
- `requests`: HTTP client

**Kurulum**:
```powershell
pip install -r requirements.txt
```

---

## 💾 Veritabanı Dosyaları

### **sentinel_production.db**
Production mode veritabanı (main.py)

### **sentinel_dev.db**
Developer mode veritabanı (main_developer.py)

### **sentinel_state.db**
Test/default veritabanı (test_ui_integration.py)

**Not**: `.gitignore` ile ignore edilir, commit edilmez

---

## 🔐 Çevre Değişkenleri

### **.env**
Gizli değişkenler (API keys)

**İçerik**:
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
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

## 🛠️ Geliştirme Workflow

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
# 59 test çalıştır
```

### 4. Production Test
```powershell
python main.py
# Docker'ı başlat, hibrit AI test et
```

---

## 📊 Proje Durumu (21 Ocak 2026)

### ✅ Tamamlanan Sprintler

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

### 📝 Gelecek Öncelikler

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

## 📖 İlgili Dosyalar

- [README.md](README.md) - Genel proje tanıtımı
- [NMAP_KURULUM.md](NMAP_KURULUM.md) - Nmap kurulum rehberi
- [docs/sprint1_ready.md](docs/sprint1_ready.md) - Sprint 1 raporu
- [docs/sqlite_schema.md](docs/sqlite_schema.md) - Veritabanı şeması

---

**Son Güncelleme**: 21 Ocak 2026  
**Versiyon**: Sprint 1 Complete + UI Integration  
**Sonraki Hedef**: Öncelik 2 - AI Orchestrator Integration
