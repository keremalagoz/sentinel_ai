# SENTINEL AI - Execution State Model
## Stateful Multi-Tool Chaining Design

---

## TEMEL PRENSİP

**State = Normalized Knowledge Graph**

Raw tool output değil, **anlamlı entity'ler** ve **aralarındaki ilişkiler**.

```
Tool Output (text) → Parser → State Update → Knowledge Graph
```

---

## 1. ENTITY TYPES (Knowledge Model)

### Core Entities

Pentest sırasında keşfedilen **anlamlı nesneler**.

```python
from enum import Enum
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# ENTITY BASE
# =============================================================================

class EntityType(str, Enum):
    """Entity türleri"""
    HOST = "host"
    PORT = "port"
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    CREDENTIAL = "credential"
    WEB_RESOURCE = "web_resource"
    DNS_RECORD = "dns_record"
    CERTIFICATE = "certificate"
    FILE = "file"


class EntityStatus(str, Enum):
    """Entity durumu"""
    DISCOVERED = "discovered"      # Yeni keşfedildi
    VERIFIED = "verified"          # Doğrulandı
    EXPLOITED = "exploited"        # Exploit edildi
    FAILED = "failed"              # İşlem başarısız
    UNREACHABLE = "unreachable"    # Erişilemez


class BaseEntity(BaseModel):
    """Tüm entity'lerin base class'ı"""
    id: str                        # Unique identifier
    entity_type: EntityType
    discovered_by: str             # Hangi tool keşfetti
    discovered_at: datetime
    status: EntityStatus
    confidence: float = 1.0        # 0.0 - 1.0 güven skoru
    tags: Set[str] = set()         # ["interesting", "high_value", etc.]


# =============================================================================
# HOST ENTITY
# =============================================================================

class HostEntity(BaseEntity):
    """Ağdaki bir host"""
    entity_type: EntityType = EntityType.HOST
    
    # Identifiers
    ip_address: str
    hostnames: List[str] = []
    mac_address: Optional[str] = None
    
    # Attributes
    os_family: Optional[str] = None        # "Linux", "Windows", etc.
    os_version: Optional[str] = None       # "Ubuntu 20.04"
    os_confidence: float = 0.0             # OS detection confidence
    
    # State
    is_alive: bool = True
    last_seen: datetime
    response_time_ms: Optional[float] = None
    
    # Relations
    open_ports: List[str] = []             # Port entity IDs
    services: List[str] = []               # Service entity IDs
    vulnerabilities: List[str] = []        # Vulnerability entity IDs


# =============================================================================
# PORT ENTITY
# =============================================================================

class PortState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNKNOWN = "unknown"


class PortEntity(BaseEntity):
    """Bir host üzerindeki port"""
    entity_type: EntityType = EntityType.PORT
    
    # Identifiers
    host_id: str                           # Parent host
    port_number: int
    protocol: str = "tcp"                  # tcp, udp
    
    # State
    state: PortState = PortState.UNKNOWN
    
    # Relations
    service_id: Optional[str] = None       # Running service


# =============================================================================
# SERVICE ENTITY
# =============================================================================

class ServiceEntity(BaseEntity):
    """Port üzerinde çalışan servis"""
    entity_type: EntityType = EntityType.SERVICE
    
    # Identifiers
    host_id: str
    port_id: str
    
    # Attributes
    service_name: str                      # "http", "ssh", "mysql"
    product: Optional[str] = None          # "Apache", "OpenSSH"
    version: Optional[str] = None          # "2.4.41"
    banner: Optional[str] = None           # Raw banner
    
    # CPE (Common Platform Enumeration)
    cpe: Optional[str] = None              # "cpe:/a:apache:http_server:2.4.41"
    
    # Relations
    vulnerabilities: List[str] = []


# =============================================================================
# VULNERABILITY ENTITY
# =============================================================================

class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityEntity(BaseEntity):
    """Keşfedilen zafiyet"""
    entity_type: EntityType = EntityType.VULNERABILITY
    
    # Identifiers
    vuln_id: str                           # CVE-2021-44228, etc.
    title: str
    
    # Attributes
    severity: VulnerabilitySeverity
    cvss_score: Optional[float] = None
    description: str
    
    # Relations
    affected_host: str                     # Host entity ID
    affected_service: Optional[str] = None # Service entity ID
    
    # Exploitation
    exploitable: bool = False
    exploit_available: bool = False
    exploit_verified: bool = False


# =============================================================================
# WEB RESOURCE ENTITY
# =============================================================================

class WebResourceType(str, Enum):
    DIRECTORY = "directory"
    FILE = "file"
    ENDPOINT = "endpoint"
    PARAMETER = "parameter"


class WebResourceEntity(BaseEntity):
    """Web üzerindeki kaynak"""
    entity_type: EntityType = EntityType.WEB_RESOURCE
    
    # Identifiers
    url: str
    resource_type: WebResourceType
    
    # Attributes
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    
    # Content
    title: Optional[str] = None
    technologies: List[str] = []           # ["PHP", "WordPress", etc.]
    
    # Relations
    host_id: str
    vulnerabilities: List[str] = []


# =============================================================================
# DNS RECORD ENTITY
# =============================================================================

class DNSRecordEntity(BaseEntity):
    """DNS kaydı"""
    entity_type: EntityType = EntityType.DNS_RECORD
    
    # Identifiers
    domain: str
    record_type: str                       # "A", "MX", "TXT", etc.
    value: str
    
    # Relations
    resolves_to_host: Optional[str] = None # Host entity ID


# =============================================================================
# CREDENTIAL ENTITY
# =============================================================================

class CredentialEntity(BaseEntity):
    """Keşfedilen credential"""
    entity_type: EntityType = EntityType.CREDENTIAL
    
    # Identifiers
    username: str
    password: Optional[str] = None         # Hash veya plaintext
    credential_type: str = "password"      # password, hash, key
    
    # Context
    service_id: Optional[str] = None       # Hangi serviste çalışıyor
    host_id: Optional[str] = None
    
    # Validation
    is_valid: Optional[bool] = None        # Test edildi mi?
    tested_at: Optional[datetime] = None


# =============================================================================
# CERTIFICATE ENTITY
# =============================================================================

class CertificateEntity(BaseEntity):
    """SSL/TLS sertifikası"""
    entity_type: EntityType = EntityType.CERTIFICATE
    
    # Identifiers
    common_name: str
    subject_alt_names: List[str] = []
    
    # Attributes
    issuer: str
    valid_from: datetime
    valid_until: datetime
    is_expired: bool
    is_self_signed: bool
    
    # Relations
    host_id: str
```

---

## 2. STATE STORAGE (Knowledge Graph)

### ExecutionState Class

```python
from typing import Dict, List, Optional
from collections import defaultdict


class ExecutionState:
    """
    Execution sırasında toplanan tüm bilgi.
    
    Bu normalized knowledge graph:
    - Raw output değil, parse edilmiş entity'ler
    - İlişkiler entity ID'leriyle
    - Query'lenebilir
    """
    
    def __init__(self):
        # Entity storage (ID -> Entity)
        self._entities: Dict[str, BaseEntity] = {}
        
        # Type index (EntityType -> List[ID])
        self._by_type: Dict[EntityType, List[str]] = defaultdict(list)
        
        # Host index (host_id -> related entities)
        self._by_host: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Execution history
        self._execution_log: List[ExecutionRecord] = []
        
        # Statistics
        self.stats = ExecutionStats()
    
    # =========================================================================
    # ENTITY MANAGEMENT
    # =========================================================================
    
    def add_entity(self, entity: BaseEntity) -> str:
        """
        State'e yeni entity ekle.
        
        Returns:
            Entity ID
        """
        entity_id = entity.id
        self._entities[entity_id] = entity
        self._by_type[entity.entity_type].append(entity_id)
        
        # Host ilişkisini indexle
        if hasattr(entity, 'host_id'):
            self._by_host[entity.host_id][entity.entity_type].append(entity_id)
        
        return entity_id
    
    def get_entity(self, entity_id: str) -> Optional[BaseEntity]:
        """Entity ID'den entity getir"""
        return self._entities.get(entity_id)
    
    def update_entity(self, entity_id: str, updates: Dict) -> bool:
        """Entity'yi güncelle"""
        if entity_id not in self._entities:
            return False
        
        entity = self._entities[entity_id]
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        return True
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_all_hosts(self) -> List[HostEntity]:
        """Tüm host'ları getir"""
        host_ids = self._by_type[EntityType.HOST]
        return [self._entities[hid] for hid in host_ids]
    
    def get_alive_hosts(self) -> List[HostEntity]:
        """Aktif host'ları getir"""
        return [h for h in self.get_all_hosts() if h.is_alive]
    
    def get_host_services(self, host_id: str) -> List[ServiceEntity]:
        """Bir host'un tüm servislerini getir"""
        service_ids = self._by_host[host_id][EntityType.SERVICE]
        return [self._entities[sid] for sid in service_ids]
    
    def get_open_ports(self, host_id: str) -> List[PortEntity]:
        """Bir host'un açık portlarını getir"""
        port_ids = self._by_host[host_id][EntityType.PORT]
        ports = [self._entities[pid] for pid in port_ids]
        return [p for p in ports if p.state == PortState.OPEN]
    
    def get_vulnerabilities(
        self,
        min_severity: VulnerabilitySeverity = VulnerabilitySeverity.LOW
    ) -> List[VulnerabilityEntity]:
        """Belirli severity üstü zafiyetleri getir"""
        vuln_ids = self._by_type[EntityType.VULNERABILITY]
        vulns = [self._entities[vid] for vid in vuln_ids]
        
        severity_order = {
            VulnerabilitySeverity.CRITICAL: 4,
            VulnerabilitySeverity.HIGH: 3,
            VulnerabilitySeverity.MEDIUM: 2,
            VulnerabilitySeverity.LOW: 1,
            VulnerabilitySeverity.INFO: 0,
        }
        
        min_level = severity_order[min_severity]
        return [v for v in vulns if severity_order[v.severity] >= min_level]
    
    def get_web_resources(self, host_id: str) -> List[WebResourceEntity]:
        """Bir host'un web kaynaklarını getir"""
        resource_ids = self._by_host[host_id][EntityType.WEB_RESOURCE]
        return [self._entities[rid] for rid in resource_ids]
    
    def has_web_service(self, host_id: str) -> bool:
        """Host'ta web servisi var mı?"""
        services = self.get_host_services(host_id)
        web_services = ["http", "https", "ssl/http", "http-proxy"]
        return any(s.service_name in web_services for s in services)
    
    def get_credentials(self, validated_only: bool = False) -> List[CredentialEntity]:
        """Credential'ları getir"""
        cred_ids = self._by_type[EntityType.CREDENTIAL]
        creds = [self._entities[cid] for cid in cred_ids]
        
        if validated_only:
            return [c for c in creds if c.is_valid is True]
        return creds
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """State istatistikleri"""
        return {
            "hosts": {
                "total": len(self._by_type[EntityType.HOST]),
                "alive": len(self.get_alive_hosts()),
            },
            "ports": {
                "total": len(self._by_type[EntityType.PORT]),
                "open": sum(1 for p in self.get_all_ports() if p.state == PortState.OPEN),
            },
            "services": len(self._by_type[EntityType.SERVICE]),
            "vulnerabilities": {
                "total": len(self._by_type[EntityType.VULNERABILITY]),
                "critical": len([v for v in self.get_vulnerabilities() 
                                if v.severity == VulnerabilitySeverity.CRITICAL]),
                "high": len([v for v in self.get_vulnerabilities() 
                            if v.severity == VulnerabilitySeverity.HIGH]),
            },
            "web_resources": len(self._by_type[EntityType.WEB_RESOURCE]),
            "credentials": len(self._by_type[EntityType.CREDENTIAL]),
        }
    
    def get_all_ports(self) -> List[PortEntity]:
        """Tüm portları getir"""
        port_ids = self._by_type[EntityType.PORT]
        return [self._entities[pid] for pid in port_ids]


# =============================================================================
# EXECUTION RECORD
# =============================================================================

class ExecutionRecord(BaseModel):
    """Bir tool execution kaydı"""
    stage_id: int
    tactical_intent: str               # TacticalIntent
    tool: str
    arguments: List[str]
    target: str
    
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    
    exit_code: int
    success: bool
    
    # State changes
    entities_added: List[str]          # Entity IDs
    entities_updated: List[str]
    
    # Output
    raw_output: str
    parsed_output: Optional[Dict] = None


class ExecutionStats(BaseModel):
    """Execution istatistikleri"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_duration_seconds: float = 0.0
    
    entities_discovered: int = 0
    hosts_discovered: int = 0
    services_discovered: int = 0
    vulnerabilities_found: int = 0
```

---

## 3. STATE UPDATE (Tool Output → State)

### Output Parser Framework

```python
from abc import ABC, abstractmethod


class OutputParser(ABC):
    """
    Tool output'u parse edip state'e entity ekler.
    
    Her tool için bir parser implementation.
    """
    
    @abstractmethod
    def parse(
        self,
        raw_output: str,
        execution_context: Dict
    ) -> ParseResult:
        """
        Raw output'u parse et.
        
        Args:
            raw_output: Tool'un stdout/stderr
            execution_context: Tool, target, arguments
        
        Returns:
            ParseResult (entities, relations, metadata)
        """
        pass


class ParseResult(BaseModel):
    """Parser çıktısı"""
    entities: List[BaseEntity]
    relations: List[Relation]              # Entity'ler arası ilişkiler
    metadata: Dict = {}                     # Ek bilgi
    errors: List[str] = []


class Relation(BaseModel):
    """Entity'ler arası ilişki"""
    from_entity: str                       # Entity ID
    to_entity: str                         # Entity ID
    relation_type: str                     # "has_service", "runs_on", etc.


# =============================================================================
# PARSER IMPLEMENTATIONS
# =============================================================================

class NmapPingSweepParser(OutputParser):
    """nmap -sn output parser"""
    
    def parse(self, raw_output: str, context: Dict) -> ParseResult:
        entities = []
        
        # Parse nmap output (örnek - gerçekte XML veya grep-able format)
        import re
        
        # "Nmap scan report for 192.168.1.1"
        pattern = r"Nmap scan report for ([0-9.]+)"
        
        for match in re.finditer(pattern, raw_output):
            ip = match.group(1)
            
            # Host entity oluştur
            host = HostEntity(
                id=f"host_{ip.replace('.', '_')}",
                ip_address=ip,
                discovered_by=context['tool'],
                discovered_at=datetime.now(),
                status=EntityStatus.DISCOVERED,
                is_alive=True,
                last_seen=datetime.now(),
            )
            entities.append(host)
        
        return ParseResult(entities=entities, relations=[])


class NmapPortScanParser(OutputParser):
    """nmap -sS -sV output parser"""
    
    def parse(self, raw_output: str, context: Dict) -> ParseResult:
        entities = []
        relations = []
        
        # Nmap XML parse (lxml kullanarak)
        # veya grep-able format
        
        # Örnek: "22/tcp open ssh OpenSSH 8.2p1"
        pattern = r"(\d+)/(tcp|udp)\s+(open|closed|filtered)\s+(\S+)(?:\s+(.+))?"
        
        host_id = context.get('host_id')  # Önceden keşfedilmiş host
        
        for match in re.finditer(pattern, raw_output):
            port_num = int(match.group(1))
            protocol = match.group(2)
            state = match.group(3)
            service_name = match.group(4)
            service_info = match.group(5) or ""
            
            # Port entity
            port = PortEntity(
                id=f"{host_id}_port_{port_num}_{protocol}",
                host_id=host_id,
                port_number=port_num,
                protocol=protocol,
                state=PortState(state),
                discovered_by=context['tool'],
                discovered_at=datetime.now(),
                status=EntityStatus.DISCOVERED,
            )
            entities.append(port)
            
            # Service entity (eğer açıksa)
            if state == "open" and service_name:
                service = ServiceEntity(
                    id=f"{host_id}_service_{port_num}",
                    host_id=host_id,
                    port_id=port.id,
                    service_name=service_name,
                    banner=service_info,
                    discovered_by=context['tool'],
                    discovered_at=datetime.now(),
                    status=EntityStatus.DISCOVERED,
                )
                
                # Version parse
                version_match = re.search(r"(\S+)\s+([\d.]+)", service_info)
                if version_match:
                    service.product = version_match.group(1)
                    service.version = version_match.group(2)
                
                entities.append(service)
                
                # Relation: port -> service
                relations.append(Relation(
                    from_entity=port.id,
                    to_entity=service.id,
                    relation_type="runs_service"
                ))
        
        return ParseResult(entities=entities, relations=relations)


class GobusterParser(OutputParser):
    """gobuster dir output parser"""
    
    def parse(self, raw_output: str, context: Dict) -> ParseResult:
        entities = []
        
        host_id = context.get('host_id')
        base_url = context.get('target')
        
        # Örnek: "/admin (Status: 200) [Size: 1234]"
        pattern = r"(/\S+)\s+\(Status:\s+(\d+)\)"
        
        for match in re.finditer(pattern, raw_output):
            path = match.group(1)
            status_code = int(match.group(2))
            
            web_resource = WebResourceEntity(
                id=f"{host_id}_web_{path.replace('/', '_')}",
                url=f"{base_url}{path}",
                resource_type=WebResourceType.DIRECTORY if path.endswith('/') else WebResourceType.FILE,
                status_code=status_code,
                host_id=host_id,
                discovered_by=context['tool'],
                discovered_at=datetime.now(),
                status=EntityStatus.DISCOVERED,
            )
            
            # Interesting paths tag
            if any(keyword in path.lower() for keyword in ['admin', 'config', 'backup', 'upload']):
                web_resource.tags.add("interesting")
            
            entities.append(web_resource)
        
        return ParseResult(entities=entities, relations=[])


# =============================================================================
# STATE UPDATER
# =============================================================================

class StateUpdater:
    """
    Tool output'u parse edip state'i günceller.
    """
    
    def __init__(self):
        # Parser registry
        self.parsers: Dict[str, OutputParser] = {
            "nmap_ping_sweep": NmapPingSweepParser(),
            "nmap_port_scan": NmapPortScanParser(),
            "gobuster": GobusterParser(),
            # ... diğer parser'lar
        }
    
    def update_state(
        self,
        state: ExecutionState,
        execution_record: ExecutionRecord
    ) -> int:
        """
        Execution sonucu state'i güncelle.
        
        Returns:
            Eklenen entity sayısı
        """
        # Parser seç
        parser_key = self._get_parser_key(execution_record.tool, execution_record.tactical_intent)
        parser = self.parsers.get(parser_key)
        
        if not parser:
            # Fallback: raw output store
            return 0
        
        # Parse
        context = {
            'tool': execution_record.tool,
            'target': execution_record.target,
            'arguments': execution_record.arguments,
        }
        
        result = parser.parse(execution_record.raw_output, context)
        
        # State'e ekle
        entity_ids = []
        for entity in result.entities:
            entity_id = state.add_entity(entity)
            entity_ids.append(entity_id)
        
        # Relations güncelle
        for relation in result.relations:
            # Entity'lerdeki relation field'ları güncelle
            pass
        
        # Execution record'u güncelle
        execution_record.entities_added = entity_ids
        execution_record.parsed_output = result.metadata
        
        return len(entity_ids)
    
    def _get_parser_key(self, tool: str, tactical_intent: str) -> str:
        """Tool + intent'ten parser key oluştur"""
        # nmap + PING_SWEEP -> nmap_ping_sweep
        return f"{tool}_{tactical_intent}".lower()
```

---

## 4. STATE-AWARE PLANNER

### Planner Decision Logic

```python
class StateAwarePlanner:
    """
    State'e bakarak dynamic plan oluşturur.
    
    Önceki execution'ların sonuçlarına göre:
    - Yeni tactic'ler ekler
    - Gereksiz stage'leri atlar
    - Execution'ı durdurur
    """
    
    def __init__(self):
        self.goal_to_tactics = GOAL_TO_TACTICS  # Base mapping
    
    def create_adaptive_plan(
        self,
        user_intent: UserIntent,
        state: ExecutionState,
        context: ExecutionContext
    ) -> ExecutionPlan:
        """
        State-aware plan oluştur.
        
        Args:
            user_intent: Kullanıcının hedefi
            state: Mevcut execution state
            context: Execution context (auth, constraints)
        
        Returns:
            Adaptive execution plan
        """
        base_tactics = self.goal_to_tactics[user_intent.goal]
        
        # State'e göre filtrele/genişlet
        adaptive_tactics = self._adapt_tactics(base_tactics, state, user_intent)
        
        # Stage'leri oluştur
        stages = self._build_stages(adaptive_tactics, state, context)
        
        return ExecutionPlan(
            goal=user_intent.goal,
            stages=stages,
            is_adaptive=True
        )
    
    def _adapt_tactics(
        self,
        base_tactics: List[TacticalIntent],
        state: ExecutionState,
        user_intent: UserIntent
    ) -> List[TacticalIntent]:
        """
        State'e göre tactic listesini adapte et.
        """
        tactics = list(base_tactics)
        
        # === RULE 1: Skip completed tactics ===
        # Eğer host discovery yapıldıysa tekrar yapma
        if state.get_alive_hosts():
            if TacticalIntent.PING_SWEEP in tactics:
                tactics.remove(TacticalIntent.PING_SWEEP)
        
        # === RULE 2: Add conditional tactics ===
        # Eğer web servisi keşfedildiyse, web enum ekle
        for host in state.get_alive_hosts():
            if state.has_web_service(host.id):
                if TacticalIntent.DIRECTORY_BRUTE_FORCE not in tactics:
                    tactics.append(TacticalIntent.DIRECTORY_BRUTE_FORCE)
        
        # === RULE 3: Priority based on findings ===
        # Critical vuln bulunduysa, exploit tactic'i önceliklendir
        critical_vulns = state.get_vulnerabilities(VulnerabilitySeverity.CRITICAL)
        if critical_vulns:
            # Exploit tactic'ini başa al
            if TacticalIntent.EXPLOIT_WEAKNESS in tactics:
                tactics.remove(TacticalIntent.EXPLOIT_WEAKNESS)
                tactics.insert(0, TacticalIntent.EXPLOIT_WEAKNESS)
        
        # === RULE 4: Skip empty targets ===
        # Eğer hiç host bulunamadıysa, port scan yapma
        if not state.get_alive_hosts():
            tactics = [t for t in tactics if t not in [
                TacticalIntent.SYN_SCAN,
                TacticalIntent.SERVICE_VERSION_DETECTION,
            ]]
        
        return tactics
    
    def _build_stages(
        self,
        tactics: List[TacticalIntent],
        state: ExecutionState,
        context: ExecutionContext
    ) -> List[Stage]:
        """
        Tactic'lerden stage'ler oluştur.
        
        Her stage:
        - Target belirleme (state'ten)
        - Dependency belirleme
        - Condition belirleme (optional)
        """
        stages = []
        
        for i, tactic in enumerate(tactics):
            # Target'leri state'ten belirle
            targets = self._determine_targets(tactic, state)
            
            if not targets:
                # Target yoksa stage atla
                continue
            
            # Her target için stage
            for target in targets:
                stage = Stage(
                    stage_id=len(stages),
                    tactical_intent=tactic,
                    target=target,
                    depends_on=[len(stages) - 1] if stages else [],
                    condition=self._build_condition(tactic, state),
                )
                stages.append(stage)
        
        return stages
    
    def _determine_targets(
        self,
        tactic: TacticalIntent,
        state: ExecutionState
    ) -> List[str]:
        """
        Tactic için target'leri state'ten belirle.
        """
        if tactic == TacticalIntent.SYN_SCAN:
            # Alive host'ların IP'leri
            return [h.ip_address for h in state.get_alive_hosts()]
        
        elif tactic == TacticalIntent.DIRECTORY_BRUTE_FORCE:
            # Web servisi olan host'ların URL'leri
            targets = []
            for host in state.get_alive_hosts():
                if state.has_web_service(host.id):
                    # HTTP/HTTPS portlarını bul
                    services = state.get_host_services(host.id)
                    for service in services:
                        if service.service_name in ["http", "https"]:
                            port = state.get_entity(service.port_id)
                            protocol = "https" if service.service_name == "https" else "http"
                            url = f"{protocol}://{host.ip_address}:{port.port_number}"
                            targets.append(url)
            return targets
        
        elif tactic == TacticalIntent.CREDENTIAL_BRUTE_FORCE:
            # SSH servisi olan host'lar
            targets = []
            for host in state.get_alive_hosts():
                services = state.get_host_services(host.id)
                for service in services:
                    if service.service_name == "ssh":
                        targets.append(f"ssh://{host.ip_address}")
            return targets
        
        # Default: tüm alive host'lar
        return [h.ip_address for h in state.get_alive_hosts()]
    
    def _build_condition(
        self,
        tactic: TacticalIntent,
        state: ExecutionState
    ) -> Optional[StageCondition]:
        """
        Stage için condition oluştur.
        
        Condition: Stage'in çalıştırılması için gerekli koşul.
        """
        if tactic == TacticalIntent.EXPLOIT_WEAKNESS:
            # Sadece exploitable vuln varsa çalıştır
            return StageCondition(
                condition_type="has_exploitable_vuln",
                check=lambda: any(v.exploitable for v in state.get_vulnerabilities())
            )
        
        elif tactic == TacticalIntent.CREDENTIAL_BRUTE_FORCE:
            # Sadece SSH servisi varsa
            return StageCondition(
                condition_type="has_ssh_service",
                check=lambda: any(
                    s.service_name == "ssh"
                    for host in state.get_alive_hosts()
                    for s in state.get_host_services(host.id)
                )
            )
        
        return None


class StageCondition(BaseModel):
    """Stage execution condition"""
    condition_type: str
    check: callable                        # Runtime check function
    
    def evaluate(self) -> bool:
        """Condition'u değerlendir"""
        return self.check()


class Stage(BaseModel):
    """Execution stage (updated)"""
    stage_id: int
    tactical_intent: TacticalIntent
    target: str
    depends_on: List[int] = []             # Stage IDs
    condition: Optional[StageCondition] = None
    
    def can_execute(self, completed_stages: Set[int]) -> bool:
        """Stage çalıştırılabilir mi?"""
        # Dependencies karşılandı mı?
        if not all(dep in completed_stages for dep in self.depends_on):
            return False
        
        # Condition var mı ve karşılanıyor mu?
        if self.condition:
            return self.condition.evaluate()
        
        return True
```

---

## 5. NEXT-STEP RECOMMENDATION ENGINE

### Öneri Motoru

```python
class RecommendationEngine:
    """
    State'e bakarak next-step önerileri üretir.
    
    "Sıradaki mantıklı adım ne?"
    """
    
    def suggest_next_actions(
        self,
        state: ExecutionState,
        context: ExecutionContext
    ) -> List[Recommendation]:
        """
        State'e göre öneriler üret.
        
        Returns:
            Öncelik sırasına göre recommendation listesi
        """
        recommendations = []
        
        # === RULE 1: Critical vulns → Exploit ===
        critical_vulns = state.get_vulnerabilities(VulnerabilitySeverity.CRITICAL)
        for vuln in critical_vulns:
            if vuln.exploit_available and not vuln.exploit_verified:
                recommendations.append(Recommendation(
                    priority=Priority.CRITICAL,
                    goal=GoalCategory.EXPLOIT_WEAKNESS,
                    reason=f"Critical vuln {vuln.vuln_id} has available exploit",
                    target=state.get_entity(vuln.affected_host).ip_address,
                    tactical_intent=TacticalIntent.EXPLOIT_CVE,
                    estimated_value=10.0,
                ))
        
        # === RULE 2: Web service → Directory enum ===
        for host in state.get_alive_hosts():
            if state.has_web_service(host.id):
                # Web enumeration yapıldı mı?
                web_resources = state.get_web_resources(host.id)
                if not web_resources:
                    recommendations.append(Recommendation(
                        priority=Priority.HIGH,
                        goal=GoalCategory.MAP_ATTACK_SURFACE,
                        reason="Web service detected, no directory enumeration yet",
                        target=host.ip_address,
                        tactical_intent=TacticalIntent.DIRECTORY_BRUTE_FORCE,
                        estimated_value=7.0,
                    ))
        
        # === RULE 3: Open ports → Service detection ===
        for host in state.get_alive_hosts():
            open_ports = state.get_open_ports(host.id)
            for port in open_ports:
                if not port.service_id:
                    # Port açık ama servis tespit edilmemiş
                    recommendations.append(Recommendation(
                        priority=Priority.MEDIUM,
                        goal=GoalCategory.MAP_ATTACK_SURFACE,
                        reason=f"Open port {port.port_number} without service detection",
                        target=host.ip_address,
                        tactical_intent=TacticalIntent.SERVICE_VERSION_DETECTION,
                        estimated_value=5.0,
                    ))
        
        # === RULE 4: Services → Vuln scan ===
        for host in state.get_alive_hosts():
            services = state.get_host_services(host.id)
            for service in services:
                if not service.vulnerabilities:
                    # Servis var ama vuln scan yok
                    recommendations.append(Recommendation(
                        priority=Priority.MEDIUM,
                        goal=GoalCategory.ASSESS_VULNERABILITIES,
                        reason=f"Service {service.service_name} not scanned for vulns",
                        target=host.ip_address,
                        tactical_intent=TacticalIntent.KNOWN_VULN_SCAN,
                        estimated_value=6.0,
                    ))
        
        # === RULE 5: SSH service → Brute force (LOW priority) ===
        for host in state.get_alive_hosts():
            services = state.get_host_services(host.id)
            ssh_services = [s for s in services if s.service_name == "ssh"]
            if ssh_services and not state.get_credentials():
                recommendations.append(Recommendation(
                    priority=Priority.LOW,
                    goal=GoalCategory.GAIN_ACCESS,
                    reason="SSH service available, no credentials yet",
                    target=host.ip_address,
                    tactical_intent=TacticalIntent.CREDENTIAL_BRUTE_FORCE,
                    estimated_value=3.0,
                ))
        
        # Priority'ye göre sırala
        recommendations.sort(key=lambda r: (r.priority.value, -r.estimated_value))
        
        return recommendations


class Priority(int, Enum):
    """Recommendation priority"""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class Recommendation(BaseModel):
    """Bir next-step önerisi"""
    priority: Priority
    goal: GoalCategory
    tactical_intent: TacticalIntent
    target: str
    reason: str
    estimated_value: float                 # 0-10 skala, kaç değerli
    
    def to_user_message(self) -> str:
        """Kullanıcıya gösterilebilir mesaj"""
        return f"[{self.priority.name}] {self.reason} → Suggested: {self.tactical_intent.value}"
```

---

## 6. TOOLDEF V2 INTEGRATION

### State-Aware ToolDef Metadata

```python
class ToolDefV2(BaseModel):
    """
    ToolDef v2 - State-aware metadata.
    
    State modeli ile entegre, karar üretir.
    """
    # V1 fields
    tool: str
    base_args: List[str]
    requires_root: bool
    risk_level: RiskLevel
    description: str
    arg_templates: Dict[str, str]
    
    # === V2: Execution Characteristics ===
    execution_time: EstimatedDuration      # SECONDS, MINUTES, HOURS
    noise_level: NoiseLevel                # SILENT, LOW, MEDIUM, HIGH, VERY_HIGH
    accuracy: AccuracyLevel                # LOW, MEDIUM, HIGH
    
    # === V2: Output & State ===
    output_format: OutputFormat            # TEXT, JSON, XML
    parser_class: str                      # "NmapPortScanParser"
    produces_entities: List[EntityType]    # [HOST, PORT, SERVICE]
    
    # === V2: Requirements ===
    requires_files: List[str] = []         # ["wordlist.txt"]
    requires_prior_knowledge: List[EntityType] = []  # [HOST] (host keşfi gerekli)
    
    # === V2: Legal/Compliance ===
    legal_risk: LegalRisk                  # SAFE, GREY_AREA, ILLEGAL
    creates_persistent_change: bool = False # Sistemde değişiklik yapar mı?
    generates_logs: bool = True            # Log oluşturur mu?
    
    # === V2: Intelligence ===
    intelligence_value: float = 5.0        # 0-10, kaç değerli bilgi üretir
    stealth_profile: StealthProfile        # PASSIVE, ACTIVE, AGGRESSIVE


class EstimatedDuration(str, Enum):
    SECONDS = "seconds"                    # < 10s
    MINUTES = "minutes"                    # 10s - 10min
    HOURS = "hours"                        # > 10min


class NoiseLevel(str, Enum):
    SILENT = "silent"                      # Tespit edilemez (DNS lookup)
    LOW = "low"                            # Az paket (ping)
    MEDIUM = "medium"                      # Normal tarama (nmap)
    HIGH = "high"                          # Yoğun tarama (dirb)
    VERY_HIGH = "very_high"                # Agresif (masscan)


class AccuracyLevel(str, Enum):
    LOW = "low"                            # Çok false positive
    MEDIUM = "medium"                      # Normal
    HIGH = "high"                          # Çok güvenilir


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    BINARY = "binary"


class LegalRisk(str, Enum):
    SAFE = "safe"                          # Kesinlikle yasal (DNS lookup)
    GREY_AREA = "grey_area"                # Bağlama bağlı (port scan)
    ILLEGAL = "illegal"                    # İzinsiz kullanım yasa dışı (exploit)


class StealthProfile(str, Enum):
    PASSIVE = "passive"                    # Hedefle etkileşim yok (OSINT)
    ACTIVE = "active"                      # Normal etkileşim (port scan)
    AGGRESSIVE = "aggressive"              # Yoğun etkileşim (brute force)
```

### Tool Selection with State Context

```python
class EnhancedToolSelector:
    """
    ToolDefV2 + State ile akıllı tool seçimi.
    """
    
    def select_tool(
        self,
        tactical_intent: TacticalIntent,
        state: ExecutionState,
        constraints: UserConstraints,
        context: ExecutionContext
    ) -> ToolExecution:
        """
        State-aware tool selection.
        """
        # Candidate tools
        candidates = self.get_tools_for_intent(tactical_intent)
        
        # State-based filtering
        candidates = self._filter_by_state(candidates, state)
        
        # Constraint-based scoring
        scored = self._score_candidates(candidates, constraints, state)
        
        # En iyi tool
        best_tool = max(scored, key=lambda x: x[1])
        
        return self._build_execution(best_tool[0], state, context)
    
    def _filter_by_state(
        self,
        candidates: List[ToolDefV2],
        state: ExecutionState
    ) -> List[ToolDefV2]:
        """
        State'e göre filtrele.
        """
        filtered = []
        
        for tool in candidates:
            # Prior knowledge requirement check
            if tool.requires_prior_knowledge:
                # Örn: PORT_SCAN için HOST gerekli
                if EntityType.HOST in tool.requires_prior_knowledge:
                    if not state.get_alive_hosts():
                        continue  # HOST yok, atla
            
            # File requirement check
            if tool.requires_files:
                # Wordlist vs. varmı kontrolü
                if not all(self._file_exists(f) for f in tool.requires_files):
                    continue
            
            filtered.append(tool)
        
        return filtered
    
    def _score_candidates(
        self,
        candidates: List[ToolDefV2],
        constraints: UserConstraints,
        state: ExecutionState
    ) -> List[Tuple[ToolDefV2, float]]:
        """
        State + constraints ile skor hesapla.
        """
        scored = []
        
        for tool in candidates:
            score = 0.0
            
            # === Speed constraint ===
            if constraints.speed == Speed.FAST:
                if tool.execution_time == EstimatedDuration.SECONDS:
                    score += 3.0
                elif tool.execution_time == EstimatedDuration.HOURS:
                    score -= 2.0
            
            # === Stealth constraint ===
            if constraints.stealth == Stealth.HIGH:
                if tool.noise_level == NoiseLevel.SILENT:
                    score += 3.0
                elif tool.noise_level == NoiseLevel.VERY_HIGH:
                    score -= 5.0
            
            # === Accuracy requirement ===
            if constraints.accuracy == Accuracy.HIGH:
                if tool.accuracy == AccuracyLevel.HIGH:
                    score += 2.0
            
            # === Intelligence value ===
            # Eğer state az bilgi varsa, high intelligence tool'ları tercih et
            if state.get_stats()["services"] < 5:
                score += tool.intelligence_value * 0.5
            
            # === Legal risk ===
            if context.authorization_level == "none":
                # İzinsiz test - yüksek legal risk'ten kaçın
                if tool.legal_risk == LegalRisk.ILLEGAL:
                    score -= 10.0  # Kesinlikle kullanma
                elif tool.legal_risk == LegalRisk.GREY_AREA:
                    score -= 3.0
            
            scored.append((tool, score))
        
        return scored
```

---

## 7. ÖRNEK SENARYO: STATE-DRIVEN WORKFLOW

### Kullanıcı: "example.com için reconnaissance yap"

#### Stage 1: Initial Goal

```python
user_intent = UserIntent(
    goal=GoalCategory.UNDERSTAND_TARGET,
    target="example.com",
    constraints=UserConstraints(speed=Speed.MEDIUM, stealth=Stealth.MEDIUM)
)
```

#### Stage 2: Base Tactics

```python
base_tactics = [
    TacticalIntent.WHOIS_QUERY,
    TacticalIntent.DNS_QUERY,
    TacticalIntent.SUBDOMAIN_ENUMERATION,
]
```

#### Stage 3: Execute & Update State

**Stage 1: WHOIS**
```
Tool: whois example.com
Output: Parsed → Domain owner, registrar, etc.
State Update:
  - DNSRecordEntity(domain="example.com", ...)
```

**Stage 2: DNS Query**
```
Tool: nslookup example.com
Output: 93.184.216.34
State Update:
  - HostEntity(ip="93.184.216.34", hostnames=["example.com"])
```

#### Stage 4: Adaptive Planning

```python
# State'de host keşfedildi → Yeni tactic ekle
state.get_alive_hosts()  # [93.184.216.34]

# Planner adapts:
new_tactics = [
    TacticalIntent.SYN_SCAN,              # Port scan
    TacticalIntent.SERVICE_VERSION_DETECTION,
]
```

**Stage 3: Port Scan**
```
Tool: nmap -sS -sV 93.184.216.34
Output: 80/tcp open http nginx 1.14.0
State Update:
  - PortEntity(port=80, state=OPEN)
  - ServiceEntity(service_name="http", product="nginx", version="1.14.0")
```

#### Stage 5: Recommendation Engine

```python
recommendations = engine.suggest_next_actions(state, context)
# Output:
# [HIGH] Web service detected, no directory enumeration yet → DIRECTORY_BRUTE_FORCE
# [MEDIUM] Service nginx 1.14.0 not scanned for vulns → KNOWN_VULN_SCAN
```

#### Stage 6: User Accepts Recommendation

```python
# User: "Evet, web dizinlerini tara"
new_goal = GoalCategory.MAP_ATTACK_SURFACE
new_tactics = [TacticalIntent.DIRECTORY_BRUTE_FORCE]

# Tool selection (state-aware)
target_url = "http://93.184.216.34"  # State'ten alındı
tool = selector.select_tool(
    TacticalIntent.DIRECTORY_BRUTE_FORCE,
    state,
    constraints,
    context
)
# Selected: gobuster (noise=MEDIUM, accuracy=HIGH)
```

---

## 8. SONUÇ: STATE MODEL KAZANIMLARI

### Bu Modelin Çözdükleri:

[OK] **Multi-tool chain** → State'te bilgi birikir, planner adapte eder  
[OK] **Conditional logic** → Stage conditions state'e bakar  
[OK] **Next-step suggestions** → State-based recommendation engine  
[OK] **Tool selection intelligence** → ToolDefV2 + state context  
[OK] **Output normalization** → Raw output → Entities  
[OK] **Knowledge retention** → Entity graph, query'lenebilir  
[OK] **Adaptive planning** → State değiştikçe plan değişir  

### ToolDef V2 Entegrasyonu:

- `produces_entities`: Parser ne üretir
- `requires_prior_knowledge`: Hangi entity'ler gerekli
- `intelligence_value`: State az bilgi varsa öncelik ver
- `noise_level`, `execution_time`: Constraint-based selection

### Minimal ama Ölçeklenebilir:

- **9 core entity type** (host, port, service, vuln, web, dns, cert, cred, file)
- **State graph** (query'lenebilir, genişletilebilir)
- **Deterministic planner** (LLM gerektirmez)
- **Rule-based recommendation** (açıklanabilir, predictable)

---

## SONRAKİ ADIM

**ToolDef v2 metadata'yı finalize edebiliriz.**

State model hazır, metadata artık **karar üretir**:
- `requires_prior_knowledge` → State'te var mı check
- `produces_entities` → Parser chain
- `intelligence_value` → Selection scoring
- `noise_level`, `execution_time` → Constraint filtering

Implementation roadmap?
