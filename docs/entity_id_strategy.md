# Entity ID Generation Strategy

## Purpose

Merkezi, canonical ve deterministik entity ID üretim stratejisi. Parser'lar bu stratejiye uymak zorundadır.

**Kritik İlke:** Entity deduplication bu ID stratejisine dayanır. Yanlış ID = Duplicate entity = State explosion.

---

## Core Principles

1. **Merkezi ID Üretimi**
   - Tüm parser'lar `EntityIDGenerator` class'ını kullanır
   - Parser ID üretimi yapamaz, override edemez
   - ID format değişiklikleri merkezi olarak yönetilir

2. **Canonical Format**
   - Her entity type için tek bir ID formatı
   - Normalizasyon zorunlu (IP, domain, port, protocol)
   - Case-insensitive (lowercase normalize)

3. **Deterministic**
   - Aynı girdi → Aynı ID
   - Parser'dan bağımsız (nmap vs masscan → aynı ID)
   - Timestamp, random value yasak

---

## Entity ID Formats

### 1. HostEntity

**Format:** `host_<normalized_ip>`

**Normalization:**
```python
def normalize_ip(ip: str) -> str:
    """192.168.1.10 → 192_168_1_10"""
    return ip.replace('.', '_')
```

**Examples:**
- `192.168.1.10` → `host_192_168_1_10`
- `10.0.0.1` → `host_10_0_0_1`
- `::1` (IPv6) → `host_0_0_0_0_0_0_0_1`

**Collision Resolution:**
- DNS name + IP aynı entity
- `example.com` (resolved to 192.168.1.10) → `host_192_168_1_10`
- Hostname metadata'ya eklenir, ID'ye değil

---

### 2. PortEntity

**Format:** `host_<ip>_port_<num>_<protocol>`

**Normalization:**
```python
def normalize_protocol(proto: str) -> str:
    """TCP, tcp, Tcp → tcp"""
    return proto.lower()
```

**Examples:**
- `192.168.1.10:80/tcp` → `host_192_168_1_10_port_80_tcp`
- `192.168.1.10:53/udp` → `host_192_168_1_10_port_53_udp`

**Collision Resolution:**
- Aynı host + port + protocol → Merge
- State: OPEN vs FILTERED → OPEN overwrites FILTERED

---

### 3. ServiceEntity

**Format:** `<port_id>_service_<normalized_name>`

**Normalization:**
```python
def normalize_service_name(name: str) -> str:
    """HTTP, http, Http → http"""
    return name.lower().replace(' ', '_')
```

**Examples:**
- Port `host_192_168_1_10_port_80_tcp` + service `http` → `host_192_168_1_10_port_80_tcp_service_http`
- Port `host_192_168_1_10_port_22_tcp` + service `ssh` → `host_192_168_1_10_port_22_tcp_service_ssh`

**Collision Resolution:**
- Aynı port + service name → Merge
- Version info metadata'ya eklenir

---

### 4. VulnerabilityEntity

**Format:** `<service_id>_vuln_<cve_or_type>`

**Normalization:**
```python
def normalize_vuln_id(vuln: str) -> str:
    """CVE-2024-1234, cve-2024-1234 → cve_2024_1234"""
    return vuln.lower().replace('-', '_')
```

**Examples:**
- Service `host_192_168_1_10_port_80_tcp_service_http` + CVE-2024-1234 → `host_192_168_1_10_port_80_tcp_service_http_vuln_cve_2024_1234`
- Service + generic vuln → `host_192_168_1_10_port_22_tcp_service_ssh_vuln_weak_cipher`

---

### 5. WebResourceEntity

**Format:** `<service_id>_web_<path_hash>`

**Path Hashing:**
```python
import hashlib

def path_hash(url: str) -> str:
    """http://192.168.1.10/admin/login.php → hash_abc123"""
    normalized = url.lower().rstrip('/')
    return f"hash_{hashlib.md5(normalized.encode()).hexdigest()[:8]}"
```

**Examples:**
- `http://192.168.1.10/admin` → `host_192_168_1_10_port_80_tcp_service_http_web_hash_abc12345`
- `https://192.168.1.10:443/api/v1` → `host_192_168_1_10_port_443_tcp_service_https_web_hash_def67890`

**Why Hash?**
- Path can be arbitrarily long
- Special characters (/, ?, &) in path
- Hash = Fixed length, safe for DB keys

---

### 6. DNSEntity

**Format:** `dns_<normalized_domain>`

**Normalization:**
```python
def normalize_domain(domain: str) -> str:
    """Example.COM, example.com → example_com"""
    return domain.lower().replace('.', '_')
```

**Examples:**
- `example.com` → `dns_example_com`
- `sub.example.com` → `dns_sub_example_com`

**Collision Resolution:**
- Domain → IP relationship separate table (entity_relationships)
- `example.com` + `192.168.1.10` → FK relationship

---

### 7. CertificateEntity

**Format:** `cert_<fingerprint>`

**Normalization:**
```python
def normalize_fingerprint(fp: str) -> str:
    """SHA256 fingerprint lowercase, no colons"""
    return fp.lower().replace(':', '')
```

**Examples:**
- SHA256 fingerprint → `cert_abc123def456...`

---

### 8. CredentialEntity

**Format:** `cred_<username>_<service_id>`

**Normalization:**
```python
def normalize_username(user: str) -> str:
    """Admin, admin, ADMIN → admin"""
    return user.lower()
```

**Examples:**
- `admin` @ `host_192_168_1_10_port_22_tcp_service_ssh` → `cred_admin_host_192_168_1_10_port_22_tcp_service_ssh`

**Security Note:**
- Password **NEVER** in ID
- Password stored encrypted in entity data

---

### 9. FileEntity

**Format:** `file_<host_id>_<path_hash>`

**Path Hashing:**
```python
def file_path_hash(path: str) -> str:
    """Absolute path → hash"""
    return f"hash_{hashlib.md5(path.encode()).hexdigest()[:8]}"
```

**Examples:**
- `/etc/passwd` on `192.168.1.10` → `file_host_192_168_1_10_hash_abc12345`

---

## EntityIDGenerator Implementation

```python
import hashlib
from typing import Optional

class EntityIDGenerator:
    """Merkezi entity ID üretimi - Parser'lar bunu kullanır"""
    
    @staticmethod
    def host_id(ip: str) -> str:
        """192.168.1.10 → host_192_168_1_10"""
        normalized = ip.replace('.', '_').replace(':', '_')
        return f"host_{normalized}"
    
    @staticmethod
    def port_id(ip: str, port: int, protocol: str) -> str:
        """192.168.1.10:80/tcp → host_192_168_1_10_port_80_tcp"""
        host_id = EntityIDGenerator.host_id(ip)
        proto = protocol.lower()
        return f"{host_id}_port_{port}_{proto}"
    
    @staticmethod
    def service_id(port_id: str, service_name: str) -> str:
        """port_id + http → host_..._service_http"""
        normalized_name = service_name.lower().replace(' ', '_')
        return f"{port_id}_service_{normalized_name}"
    
    @staticmethod
    def vuln_id(service_id: str, cve_or_type: str) -> str:
        """service_id + CVE-2024-1234 → ..._vuln_cve_2024_1234"""
        normalized = cve_or_type.lower().replace('-', '_')
        return f"{service_id}_vuln_{normalized}"
    
    @staticmethod
    def web_resource_id(service_id: str, url: str) -> str:
        """service_id + URL → ..._web_hash_abc123"""
        normalized_url = url.lower().rstrip('/')
        hash_value = hashlib.md5(normalized_url.encode()).hexdigest()[:8]
        return f"{service_id}_web_hash_{hash_value}"
    
    @staticmethod
    def dns_id(domain: str) -> str:
        """example.com → dns_example_com"""
        normalized = domain.lower().replace('.', '_')
        return f"dns_{normalized}"
    
    @staticmethod
    def cert_id(fingerprint: str) -> str:
        """SHA256 fingerprint → cert_abc123..."""
        normalized = fingerprint.lower().replace(':', '')
        return f"cert_{normalized}"
    
    @staticmethod
    def credential_id(username: str, service_id: str) -> str:
        """admin @ service → cred_admin_service_id"""
        normalized_user = username.lower()
        return f"cred_{normalized_user}_{service_id}"
    
    @staticmethod
    def file_id(host_id: str, file_path: str) -> str:
        """/etc/passwd @ host → file_host_..._hash_abc123"""
        hash_value = hashlib.md5(file_path.encode()).hexdigest()[:8]
        return f"file_{host_id}_hash_{hash_value}"
```

---

## Collision Handling Policy

### When Duplicate ID Detected

```python
def add_entity(self, entity: BaseEntity) -> str:
    """Add or merge entity"""
    entity_id = entity.id
    
    existing = self.backend.get_entity(entity_id)
    
    if existing:
        # Collision detected → MERGE
        merged = self._merge_entity(existing, entity)
        self.backend.update(merged)
        return entity_id
    else:
        # New entity
        self.backend.insert(entity)
        return entity_id
```

### Merge Logic

**Rule 1: Higher Confidence Wins**
```python
if new_entity.confidence > existing.confidence:
    merged.data = new_entity.data
    merged.confidence = new_entity.confidence
```

**Rule 2: Newer Timestamp Wins (for mutable fields)**
```python
if new_entity.updated_at > existing.updated_at:
    merged.status = new_entity.status  # OPEN vs CLOSED
```

**Rule 3: Merge Metadata (additive)**
```python
# DNS: Multiple A records
existing.ip_addresses = [192.168.1.10]
new_entity.ip_addresses = [192.168.1.11]
merged.ip_addresses = [192.168.1.10, 192.168.1.11]  # Union
```

---

## Parser Integration

### Parser Base Class

```python
from abc import ABC, abstractmethod

class BaseParser(ABC):
    """All parsers inherit this"""
    
    def __init__(self):
        self.id_generator = EntityIDGenerator()
    
    @abstractmethod
    def parse(self, output: str) -> List[BaseEntity]:
        """Subclass implements this"""
        pass
    
    def _create_host_entity(self, ip: str, **kwargs) -> HostEntity:
        """Helper: Create host with correct ID"""
        host_id = self.id_generator.host_id(ip)
        return HostEntity(id=host_id, ip_address=ip, **kwargs)
    
    def _create_port_entity(self, ip: str, port: int, protocol: str, **kwargs) -> PortEntity:
        """Helper: Create port with correct ID"""
        port_id = self.id_generator.port_id(ip, port, protocol)
        host_id = self.id_generator.host_id(ip)
        return PortEntity(id=port_id, host_id=host_id, port=port, protocol=protocol, **kwargs)
```

### Example: NmapPingSweepParser

```python
class NmapPingSweepParser(BaseParser):
    def parse(self, output: str) -> List[BaseEntity]:
        entities = []
        
        for line in output.split('\n'):
            if 'Host is up' in line:
                ip = self._extract_ip(line)
                
                # CORRECT: Use ID generator
                host = self._create_host_entity(
                    ip=ip,
                    is_alive=True,
                    confidence=0.95
                )
                entities.append(host)
        
        return entities
    
    def _extract_ip(self, line: str) -> str:
        # ... IP extraction logic
        pass
```

### Anti-Pattern (FORBIDDEN)

```python
# WRONG: Parser creates ID directly
class BadParser(BaseParser):
    def parse(self, output: str) -> List[BaseEntity]:
        host = HostEntity(
            id=f"my_custom_{ip}",  # WRONG: Non-canonical ID
            ip_address=ip
        )
        return [host]
```

---

## Validation Rules

### Sprint 1 Enforcement

1. **Parser Test:** Her parser output → ID format validation
2. **Duplicate Test:** Aynı entity iki parser'dan → ID match?
3. **Merge Test:** Collision detection working?

### ID Format Validation

```python
import re

class IDValidator:
    HOST_PATTERN = r'^host_[\d_]+$'
    PORT_PATTERN = r'^host_[\d_]+_port_\d+_(tcp|udp)$'
    SERVICE_PATTERN = r'^host_[\d_]+_port_\d+_(tcp|udp)_service_[a-z_]+$'
    
    @staticmethod
    def validate_host_id(entity_id: str) -> bool:
        return bool(re.match(IDValidator.HOST_PATTERN, entity_id))
    
    @staticmethod
    def validate_port_id(entity_id: str) -> bool:
        return bool(re.match(IDValidator.PORT_PATTERN, entity_id))
```

---

## Migration & Backward Compatibility

**Sprint 1:** New parsers use `EntityIDGenerator`

**Sprint 2:** Old parsers refactored to use generator

**No** backward compatibility for old ID formats - fresh state, fresh IDs.

---

## Summary

| Entity Type | ID Format | Example |
|-------------|-----------|---------|
| Host | `host_<ip>` | `host_192_168_1_10` |
| Port | `host_<ip>_port_<num>_<proto>` | `host_192_168_1_10_port_80_tcp` |
| Service | `<port_id>_service_<name>` | `host_192_168_1_10_port_80_tcp_service_http` |
| Vulnerability | `<service_id>_vuln_<cve>` | `..._service_http_vuln_cve_2024_1234` |
| WebResource | `<service_id>_web_hash_<hash>` | `..._service_http_web_hash_abc12345` |
| DNS | `dns_<domain>` | `dns_example_com` |
| Certificate | `cert_<fingerprint>` | `cert_abc123def456...` |
| Credential | `cred_<user>_<service_id>` | `cred_admin_host_..._service_ssh` |
| File | `file_<host_id>_hash_<hash>` | `file_host_192_168_1_10_hash_abc123` |

**Critical Rule:** Parser'lar `EntityIDGenerator` kullanır, override yasak.
