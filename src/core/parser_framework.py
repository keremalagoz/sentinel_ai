"""Parser Framework - Base Parser and Tool Integration

Sprint 1 Week 1 Implementation
Locked Design: docs/execution_history_model.md

All parsers inherit BaseParser.
Parser'lar EntityIDGenerator kullanır, override yasak.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import time
import uuid

from src.core.entity_id_generator import EntityIDGenerator
from src.core.sqlite_backend import (
    BaseEntity, ToolExecutionResult,
    EntityType, ExecutionStatus, ParseStatus
)


class ParserException(Exception):
    """Parser exception - raised when parsing fails"""
    pass


class BaseParser(ABC):
    """
    Base parser for all tool output parsers.
    
    All parsers inherit this class and implement parse() method.
    
    Features:
    - EntityIDGenerator integration (canonical IDs)
    - Helper methods for entity creation
    - Parser failure handling
    
    Design: docs/execution_history_model.md
    """
    
    def __init__(self):
        """Initialize parser with ID generator"""
        self.id_generator = EntityIDGenerator()
    
    @abstractmethod
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse tool output into entities.
        
        Args:
            output: Tool stdout/stderr output
            
        Returns:
            List of parsed entities
            
        Raises:
            ParserException: If parsing fails
            
        Note: Subclass implements this method
        """
        pass
    
    def _create_host_entity(
        self,
        ip: str,
        is_alive: bool = True,
        hostname: Optional[str] = None,
        os_type: Optional[str] = None,
        confidence: float = 1.0,
        **kwargs
    ) -> BaseEntity:
        """
        Helper: Create host entity with correct canonical ID.
        
        Args:
            ip: IP address
            is_alive: Whether host is alive
            hostname: Optional hostname
            os_type: Optional OS type
            confidence: Confidence score (0.0 - 1.0)
            **kwargs: Additional data fields
            
        Returns:
            Host entity with canonical ID
        """
        host_id = self.id_generator.host_id(ip)
        
        data = {
            "ip_address": ip,
            "is_alive": is_alive
        }
        
        if hostname:
            data["hostname"] = hostname
        if os_type:
            data["os_type"] = os_type
        
        # Add any additional fields
        data.update(kwargs)
        
        return BaseEntity(
            id=host_id,
            entity_type=EntityType.HOST,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=confidence,
            data=data
        )
    
    def _create_port_entity(
        self,
        ip: str,
        port: int,
        protocol: str,
        state: str = "open",
        confidence: float = 1.0,
        **kwargs
    ) -> BaseEntity:
        """
        Helper: Create port entity with correct canonical ID.
        
        Args:
            ip: Host IP address
            port: Port number
            protocol: Protocol (tcp, udp)
            state: Port state (open, closed, filtered)
            confidence: Confidence score
            **kwargs: Additional data fields
            
        Returns:
            Port entity with canonical ID
        """
        port_id = self.id_generator.port_id(ip, port, protocol)
        host_id = self.id_generator.host_id(ip)
        
        data = {
            "host_id": host_id,
            "port": port,
            "protocol": protocol.lower(),
            "state": state
        }
        
        data.update(kwargs)
        
        return BaseEntity(
            id=port_id,
            entity_type=EntityType.PORT,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=confidence,
            data=data
        )
    
    def _create_service_entity(
        self,
        port_id: str,
        service_name: str,
        version: Optional[str] = None,
        banner: Optional[str] = None,
        confidence: float = 1.0,
        **kwargs
    ) -> BaseEntity:
        """
        Helper: Create service entity with correct canonical ID.
        
        Args:
            port_id: Port ID (from _create_port_entity)
            service_name: Service name (http, ssh, etc.)
            version: Optional version string
            banner: Optional service banner
            confidence: Confidence score
            **kwargs: Additional data fields
            
        Returns:
            Service entity with canonical ID
        """
        service_id = self.id_generator.service_id(port_id, service_name)
        
        data = {
            "port_id": port_id,
            "service_name": service_name.lower()
        }
        
        if version:
            data["version"] = version
        if banner:
            data["banner"] = banner
        
        data.update(kwargs)
        
        return BaseEntity(
            id=service_id,
            entity_type=EntityType.SERVICE,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=confidence,
            data=data
        )
    
    def _create_vulnerability_entity(
        self,
        service_id: str,
        vuln_id: str,
        severity: str,
        description: Optional[str] = None,
        exploitable: bool = False,
        confidence: float = 1.0,
        **kwargs
    ) -> BaseEntity:
        """
        Helper: Create vulnerability entity with correct canonical ID.
        
        Args:
            service_id: Service ID
            vuln_id: CVE ID or vulnerability type
            severity: Severity (low, medium, high, critical)
            description: Optional description
            exploitable: Whether vulnerability is exploitable
            confidence: Confidence score
            **kwargs: Additional data fields
            
        Returns:
            Vulnerability entity with canonical ID
        """
        vuln_entity_id = self.id_generator.vuln_id(service_id, vuln_id)
        
        data = {
            "service_id": service_id,
            "vuln_id": vuln_id,
            "severity": severity.lower(),
            "exploitable": exploitable
        }
        
        if description:
            data["description"] = description
        
        data.update(kwargs)
        
        return BaseEntity(
            id=vuln_entity_id,
            entity_type=EntityType.VULNERABILITY,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=confidence,
            data=data
        )
    
    def _create_dns_entity(
        self,
        domain: str,
        record_type: str,
        value: str,
        confidence: float = 1.0,
        **kwargs
    ) -> BaseEntity:
        """
        Helper: Create DNS entity with correct canonical ID.
        
        Args:
            domain: Domain name
            record_type: DNS record type (A, AAAA, MX, etc.)
            value: Record value
            confidence: Confidence score
            **kwargs: Additional data fields
            
        Returns:
            DNS entity with canonical ID
        """
        dns_id = self.id_generator.dns_id(domain)
        
        data = {
            "domain": domain.lower(),
            "record_type": record_type.upper(),
            "value": value
        }
        
        data.update(kwargs)
        
        return BaseEntity(
            id=dns_id,
            entity_type=EntityType.DNS,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=confidence,
            data=data
        )


class ToolExecutor:
    """
    Tool executor with parser integration and execution history tracking.
    
    Handles:
    - Tool execution
    - Output parsing
    - PARTIAL_SUCCESS on parse failure
    - Execution history recording
    
    Design: docs/execution_history_model.md
    """
    
    def __init__(self, backend):
        """
        Initialize tool executor.
        
        Args:
            backend: SQLiteBackend instance
        """
        self.backend = backend
    
    def execute_and_parse(
        self,
        tool_id: str,
        parser: BaseParser,
        output: str,
        stage_id: Optional[int] = None
    ) -> ToolExecutionResult:
        """
        Execute parser and record execution result.
        
        Args:
            tool_id: Tool ID (nmap_ping_sweep, etc.)
            parser: Parser instance
            output: Tool output to parse
            stage_id: Optional stage ID
            
        Returns:
            Tool execution result
            
        Note: Parser failure = PARTIAL_SUCCESS, not FAILED
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        started_at = time.time()
        
        entities_created = 0
        status = ExecutionStatus.SUCCESS
        parse_status = ParseStatus.PARSED
        error_message = None
        
        try:
            # Parse output
            entities = parser.parse(output)
            
            if not entities:
                # Tool ran but no data found
                parse_status = ParseStatus.EMPTY_OUTPUT
            else:
                # Add entities to state (atomic transaction)
                entities_created = self.backend.add_entities_batch(entities)
                
        except ParserException as e:
            # Parser failed = PARTIAL_SUCCESS (tool ran, parse failed)
            status = ExecutionStatus.PARTIAL_SUCCESS
            parse_status = ParseStatus.PARSE_FAILED
            error_message = f"Parser exception: {str(e)}"
            
        except Exception as e:
            # Unexpected exception = PARTIAL_SUCCESS
            status = ExecutionStatus.PARTIAL_SUCCESS
            parse_status = ParseStatus.PARSE_FAILED
            error_message = f"Unexpected error: {str(e)}"
        
        completed_at = time.time()
        
        # Create execution result
        result = ToolExecutionResult(
            execution_id=execution_id,
            tool_id=tool_id,
            stage_id=stage_id,
            status=status,
            parse_status=parse_status,
            raw_output=output,
            started_at=started_at,
            completed_at=completed_at,
            entities_created=entities_created,
            error_message=error_message
        )
        
        # Record execution in history
        self.backend.record_execution(result)
        
        return result
    
    def has_successful_parse(self, tool_id: str) -> bool:
        """
        Check if tool has successful parse execution.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            True if tool executed and parsed successfully
        """
        last_exec = self.backend.get_last_execution(tool_id)
        
        if last_exec is None:
            return False
        
        return (
            last_exec.status == ExecutionStatus.SUCCESS and
            last_exec.parse_status == ParseStatus.PARSED
        )


# Example parser implementations (for testing)

class PingParser(BaseParser):
    """
    Simple ping parser.
    
    Parses ping output to detect alive hosts.
    """
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse ping output.
        
        Args:
            output: Ping command output
            
        Returns:
            List with single host entity if successful
            
        Example output:
            Pinging 192.168.1.10 with 32 bytes of data:
            Reply from 192.168.1.10: bytes=32 time<1ms TTL=64
        """
        found_ips = set()
        
        # Look for "Reply from" or "from" in output
        for line in output.split('\n'):
            line_lower = line.lower()
            
            if 'reply from' in line_lower or 'from' in line_lower:
                # Extract IP address
                # Simple extraction: look for pattern "from X.X.X.X"
                parts = line.split()
                
                for i, part in enumerate(parts):
                    if part.lower() in ['from', 'from:']:
                        if i + 1 < len(parts):
                            ip = parts[i + 1].rstrip(':')
                            found_ips.add(ip)
                            break
        
        if not found_ips:
            raise ParserException("No reply found in ping output")
        
        # Create one host entity per unique IP
        entities = []
        for ip in found_ips:
            host = self._create_host_entity(
                ip=ip,
                is_alive=True,
                confidence=0.95
            )
            entities.append(host)
        
        return entities


class NmapPingSweepParser(BaseParser):
    """
    Nmap ping sweep parser.
    
    Parses nmap -sn output to detect alive hosts.
    """
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse nmap ping sweep output.
        
        Args:
            output: Nmap -sn output
            
        Returns:
            List of host entities
            
        Example output:
            Nmap scan report for 192.168.1.10
            Host is up (0.00050s latency).
        """
        entities = []
        current_ip = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Look for "Nmap scan report for"
            if 'Nmap scan report for' in line:
                # Extract IP
                parts = line.split()
                if len(parts) >= 5:
                    current_ip = parts[-1]
            
            # Look for "Host is up"
            elif 'Host is up' in line and current_ip:
                # Create host entity
                host = self._create_host_entity(
                    ip=current_ip,
                    is_alive=True,
                    confidence=1.0
                )
                entities.append(host)
                current_ip = None
        
        if not entities:
            raise ParserException("No alive hosts found in nmap output")
        
        return entities


class NmapPortScanParser(BaseParser):
    """
    Nmap port scan parser.
    
    Parses nmap -sS/-sT output to detect open ports.
    """
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse nmap port scan output.
        
        Args:
            output: Nmap port scan output
            
        Returns:
            List of host and port entities
            
        Example output:
            Nmap scan report for 192.168.1.10
            PORT     STATE SERVICE
            22/tcp   open  ssh
            80/tcp   open  http
        """
        entities = []
        current_ip = None
        found_ports = False
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Look for "Nmap scan report for"
            if 'Nmap scan report for' in line:
                parts = line.split()
                if len(parts) >= 5:
                    current_ip = parts[-1]
            
            # Look for port lines (format: "80/tcp open http")
            elif current_ip and '/' in line and 'open' in line:
                parts = line.split()
                
                if len(parts) >= 3:
                    port_proto = parts[0]
                    state = parts[1]
                    service_name = parts[2] if len(parts) > 2 else "unknown"
                    
                    # Parse port/protocol
                    if '/' in port_proto:
                        port_num, protocol = port_proto.split('/')
                        
                        try:
                            port_num = int(port_num)
                            
                            # First open port: create host entity
                            if not found_ports:
                                host = self._create_host_entity(
                                    ip=current_ip,
                                    is_alive=True
                                )
                                entities.append(host)
                                found_ports = True
                            
                            # Create port entity
                            port = self._create_port_entity(
                                ip=current_ip,
                                port=port_num,
                                protocol=protocol,
                                state=state
                            )
                            entities.append(port)
                            
                            # Create service entity if service detected
                            if service_name != "unknown":
                                service = self._create_service_entity(
                                    port_id=port.id,
                                    service_name=service_name
                                )
                                entities.append(service)
                        
                        except ValueError:
                            # Invalid port number, skip
                            pass
        
        if not entities or not found_ports:
            raise ParserException("No ports found in nmap output")
        
        return entities


class NmapServiceDetectionParser(BaseParser):
    """
    Nmap service detection parser.
    
    Parses nmap -sV output to detect service versions.
    Creates host, port, and service entities with version information.
    """
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse nmap service detection output.
        
        Args:
            output: Nmap -sV output
            
        Returns:
            List of host, port, and service entities
            
        Example output:
            Nmap scan report for 192.168.1.10
            PORT     STATE SERVICE VERSION
            22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.5
            80/tcp   open  http    Apache httpd 2.4.41
            443/tcp  open  ssl/http nginx 1.18.0
        """
        entities = []
        current_ip = None
        found_services = False
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Look for "Nmap scan report for"
            if 'Nmap scan report for' in line:
                parts = line.split()
                if len(parts) >= 5:
                    current_ip = parts[-1]
            
            # Look for port/service lines
            elif current_ip and '/' in line and ('open' in line or 'filtered' in line):
                parts = line.split(None, 3)  # Split into max 4 parts
                
                if len(parts) >= 3:
                    port_proto = parts[0]
                    state = parts[1]
                    service_info = parts[2] if len(parts) > 2 else ""
                    version_info = parts[3] if len(parts) > 3 else ""
                    
                    # Parse port/protocol
                    if '/' in port_proto:
                        try:
                            port_num_str, protocol = port_proto.split('/')
                            port_num = int(port_num_str)
                            
                            # First service: create host entity
                            if not found_services:
                                host = self._create_host_entity(
                                    ip=current_ip,
                                    is_alive=True
                                )
                                entities.append(host)
                                found_services = True
                            
                            # Create port entity
                            port = self._create_port_entity(
                                ip=current_ip,
                                port=port_num,
                                protocol=protocol,
                                state=state
                            )
                            entities.append(port)
                            
                            # Create service entity with version if available
                            if service_info:
                                service_data = {
                                    "service_name": service_info
                                }
                                
                                if version_info:
                                    service_data["version"] = version_info
                                    
                                    # Try to extract product and version separately
                                    version_parts = version_info.split(None, 2)
                                    if len(version_parts) >= 1:
                                        service_data["product"] = version_parts[0]
                                    if len(version_parts) >= 2:
                                        service_data["product_version"] = version_parts[1]
                                
                                service = self._create_service_entity(
                                    port_id=port.id,
                                    service_name=service_info,
                                    **service_data
                                )
                                entities.append(service)
                        
                        except ValueError:
                            # Invalid port number, skip
                            pass
        
        if not entities or not found_services:
            raise ParserException("No services found in nmap -sV output")
        
        return entities


class NmapVulnScanParser(BaseParser):
    """
    Nmap vulnerability scan parser.
    
    Parses nmap --script vuln output to detect vulnerabilities.
    Creates host, port, service, and vulnerability entities.
    """
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse nmap vulnerability scan output.
        
        Args:
            output: Nmap --script vuln output
            
        Returns:
            List of host, port, service, and vulnerability entities
            
        Example output:
            Nmap scan report for 192.168.1.10
            PORT     STATE SERVICE
            80/tcp   open  http
            |_http-csrf: Couldn't find any CSRF vulnerabilities.
            |_http-dombased-xss: Couldn't find any DOM based XSS.
            | http-enum:
            |_  /admin/: Admin area
            443/tcp  open  https
            | ssl-heartbleed:
            |   VULNERABLE:
            |   The Heartbleed Bug is a serious vulnerability
        """
        entities = []
        current_ip = None
        current_port = None
        current_port_entity = None
        found_vulns = False
        in_vuln_block = False
        vuln_buffer = []
        
        for line in output.split('\n'):
            stripped = line.strip()
            
            # Look for "Nmap scan report for"
            if 'Nmap scan report for' in stripped:
                parts = stripped.split()
                if len(parts) >= 5:
                    current_ip = parts[-1]
                    current_port = None
                    current_port_entity = None
            
            # Look for port lines
            elif current_ip and '/' in stripped and ('open' in stripped or 'filtered' in stripped):
                # Flush previous vulnerability if exists
                if vuln_buffer and current_port_entity:
                    vuln_text = '\n'.join(vuln_buffer)
                    vuln_entity = self._create_vulnerability_entity(
                        target_id=current_port_entity.id,
                        vuln_type="nmap_script",
                        description=vuln_text,
                        severity="medium"
                    )
                    entities.append(vuln_entity)
                    vuln_buffer = []
                    in_vuln_block = False
                
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    port_proto = parts[0]
                    state = parts[1]
                    
                    if '/' in port_proto:
                        try:
                            port_num_str, protocol = port_proto.split('/')
                            port_num = int(port_num_str)
                            current_port = port_num
                            
                            # First port: create host entity
                            if not found_vulns:
                                host = self._create_host_entity(
                                    ip=current_ip,
                                    is_alive=True
                                )
                                entities.append(host)
                                found_vulns = True
                            
                            # Create port entity
                            port_entity = self._create_port_entity(
                                ip=current_ip,
                                port=port_num,
                                protocol=protocol,
                                state=state
                            )
                            entities.append(port_entity)
                            current_port_entity = port_entity
                        
                        except ValueError:
                            pass
            
            # Look for vulnerability indicators in script output
            elif current_port_entity and (stripped.startswith('|') or stripped.startswith('_')):
                # Script output line
                if 'VULNERABLE' in stripped.upper() or 'CVE-' in stripped:
                    in_vuln_block = True
                    vuln_buffer.append(stripped)
                elif in_vuln_block:
                    vuln_buffer.append(stripped)
                    # End of vuln block detection (heuristic)
                    if stripped and not stripped.startswith('|') and not stripped.startswith('_'):
                        in_vuln_block = False
        
        # Flush last vulnerability if exists
        if vuln_buffer and current_port_entity:
            vuln_text = '\n'.join(vuln_buffer)
            vuln_entity = self._create_vulnerability_entity(
                target_id=current_port_entity.id,
                vuln_type="nmap_script",
                description=vuln_text,
                severity="medium"
            )
            entities.append(vuln_entity)
        
        if not entities:
            raise ParserException("No scan results found in nmap --script vuln output")
        
        return entities


class DnsLookupParser(BaseParser):
    """
    DNS lookup parser for nslookup output.
    
    Parses nslookup output and creates DNS entities.
    """
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse nslookup output.
        
        Args:
            output: nslookup output
            
        Returns:
            List of DNS entities
            
        Example output:
            Server:  UnKnown
            Address:  192.168.1.1
            
            Non-authoritative answer:
            Name:    example.com
            Addresses:  93.184.216.34
                        2606:2800:220:1:248:1893:25c8:1946
        """
        entities = []
        domain = None
        record_type = "A"  # Default
        
        # Extract domain and record type from output
        for line in output.split('\n'):
            line = line.strip()
            
            # Look for "Name:" line
            if line.startswith('Name:'):
                domain = line.split(':', 1)[1].strip()
            
            # Look for "Addresses:" or "Address:" lines
            elif domain and ('Addresses:' in line or 'Address:' in line):
                # Parse addresses
                if ':' in line:
                    addr_part = line.split(':', 1)[1].strip()
                    if addr_part and not any(x in addr_part for x in ['UnKnown', 'Server']):
                        # This is an IP address
                        if '.' in addr_part and not '::' in addr_part:
                            # IPv4
                            dns_entity = self._create_dns_entity(
                                domain=domain,
                                record_type="A",
                                value=addr_part
                            )
                            entities.append(dns_entity)
                        elif '::' in addr_part or addr_part.count(':') > 1:
                            # IPv6
                            dns_entity = self._create_dns_entity(
                                domain=domain,
                                record_type="AAAA",
                                value=addr_part
                            )
                            entities.append(dns_entity)
            
            # Look for standalone IP addresses (after Addresses:)
            elif domain and line and not line.startswith(('Server', 'Address', 'Non-authoritative')):
                # Check if it's an IP address
                if '.' in line and not ' ' in line.strip():
                    # Likely IPv4
                    dns_entity = self._create_dns_entity(
                        domain=domain,
                        record_type="A",
                        value=line.strip()
                    )
                    entities.append(dns_entity)
                elif '::' in line or line.count(':') > 2:
                    # Likely IPv6
                    dns_entity = self._create_dns_entity(
                        domain=domain,
                        record_type="AAAA",
                        value=line.strip()
                    )
                    entities.append(dns_entity)
            
            # Look for MX records
            elif 'mail exchanger' in line.lower() or 'MX preference' in line:
                parts = line.split()
                if len(parts) >= 2:
                    mx_server = parts[-1].rstrip('.')
                    if domain and mx_server:
                        dns_entity = self._create_dns_entity(
                            domain=domain,
                            record_type="MX",
                            value=mx_server
                        )
                        entities.append(dns_entity)
            
            # Look for NS records
            elif 'nameserver' in line.lower() and '=' in line:
                ns_server = line.split('=')[1].strip().rstrip('.')
                if domain and ns_server:
                    dns_entity = self._create_dns_entity(
                        domain=domain,
                        record_type="NS",
                        value=ns_server
                    )
                    entities.append(dns_entity)
        
        if not entities:
            raise ParserException("No DNS records found in nslookup output")
        
        return entities


class SslScanParser(BaseParser):
    """
    Parser for OpenSSL s_client output.
    Extracts certificate info, cipher details, and protocol versions.
    """
    
    def __init__(self):
        super().__init__()
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse OpenSSL s_client output.
        
        Expected output format:
            CONNECTED(...)
            depth=2 ...
            verify return:1
            ---
            Certificate chain
             0 s:CN = example.com
               i:CN = Let's Encrypt Authority X3
            ...
            Server certificate
            -----BEGIN CERTIFICATE-----
            ...
            subject=CN = example.com
            issuer=CN = Let's Encrypt Authority X3
            ---
            No client certificate CA names sent
            ---
            SSL handshake has read 4345 bytes
            ...
            New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
            ...
            
        Args:
            output: OpenSSL s_client output
            
        Returns:
            List of BaseEntity (ssl_cert entities with certificate and cipher info)
        """
        entities = []
        lines = output.split('\n')
        
        # Extract certificate info
        subject = None
        issuer = None
        cert_start_date = None
        cert_end_date = None
        protocol = None
        cipher = None
        
        for line in lines:
            line = line.strip()
            
            # Extract subject (certificate owner)
            if line.startswith('subject='):
                subject = line.split('subject=')[1].strip()
            
            # Extract issuer (CA)
            elif line.startswith('issuer='):
                issuer = line.split('issuer=')[1].strip()
            
            # Extract protocol and cipher (e.g., "New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384")
            elif 'Cipher is' in line:
                parts = line.split(',')
                for part in parts:
                    if 'TLS' in part or 'SSL' in part:
                        # Extract protocol version
                        if '=' not in part and 'Cipher' not in part:
                            protocol = part.strip()
                    if 'Cipher is' in part:
                        cipher = part.split('Cipher is')[1].strip()
            
            # Alternative protocol detection
            elif line.startswith('Protocol') and ':' in line:
                protocol = line.split(':')[1].strip()
            
            # Alternative cipher detection
            elif line.startswith('Cipher') and ':' in line:
                cipher = line.split(':')[1].strip()
        
        # Create SSL certificate entity if we found info
        if subject or issuer or protocol or cipher:
            ssl_entity = self._create_ssl_cert_entity(
                subject=subject or "Unknown",
                issuer=issuer or "Unknown",
                protocol=protocol or "Unknown",
                cipher=cipher or "Unknown"
            )
            entities.append(ssl_entity)
        
        if not entities:
            raise ParserException("No SSL/TLS information found in openssl output")
        
        return entities
    
    def _create_ssl_cert_entity(
        self,
        subject: str,
        issuer: str,
        protocol: str,
        cipher: str
    ) -> BaseEntity:
        """Create SSL certificate entity."""
        entity_id = self.id_generator.generate_id(
            entity_type="ssl_cert",
            key=f"{subject}_{issuer}"
        )
        
        return BaseEntity(
            id=entity_id,
            type="ssl_cert",
            properties={
                "subject": subject,
                "issuer": issuer,
                "protocol": protocol,
                "cipher": cipher
            },
            relationships=[]
        )


class GobusterDirParser(BaseParser):
    """
    Parser for gobuster dir mode output.
    Extracts discovered directories and files.
    """
    
    def __init__(self):
        super().__init__()
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse gobuster dir output.
        
        Expected output format:
            /admin                (Status: 200) [Size: 1234]
            /backup               (Status: 403) [Size: 567]
            /login.php            (Status: 200) [Size: 890]
            /api                  (Status: 301) -> http://example.com/api/
            
        Args:
            output: Gobuster dir output
            
        Returns:
            List of BaseEntity (web_path entities with status code and size)
        """
        entities = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('=') or 'Gobuster' in line:
                continue
            
            # Parse gobuster output line
            # Format: /path (Status: 200) [Size: 1234]
            if '(Status:' in line:
                # Extract path
                path = line.split('(Status:')[0].strip()
                
                # Extract status code
                status_code = None
                if 'Status:' in line:
                    status_part = line.split('Status:')[1].split(')')[0].strip()
                    try:
                        status_code = int(status_part)
                    except ValueError:
                        status_code = None
                
                # Extract size
                size = None
                if '[Size:' in line:
                    size_part = line.split('[Size:')[1].split(']')[0].strip()
                    try:
                        size = int(size_part)
                    except ValueError:
                        size = None
                
                # Create web path entity
                if path:
                    web_path_entity = self._create_web_path_entity(
                        path=path,
                        status_code=status_code or 0,
                        size=size or 0
                    )
                    entities.append(web_path_entity)
        
        if not entities:
            raise ParserException("No web paths found in gobuster output")
        
        return entities
    
    def _create_web_path_entity(
        self,
        path: str,
        status_code: int,
        size: int
    ) -> BaseEntity:
        """Create web path entity."""
        entity_id = self.id_generator.generate_id(
            entity_type="web_path",
            key=path
        )
        
        return BaseEntity(
            id=entity_id,
            type="web_path",
            properties={
                "path": path,
                "status_code": status_code,
                "size": size
            },
            relationships=[]
        )


class SubdomainEnumParser(BaseParser):
    """
    Parser for subdomain enumeration output.
    Extracts discovered subdomains.
    """
    
    def __init__(self):
        super().__init__()
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse subdomain enumeration output.
        
        Expected output format:
            FOUND: www.example.com
            FOUND: mail.example.com
            FOUND: api.example.com
            
        Args:
            output: Subdomain enumeration output
            
        Returns:
            List of BaseEntity (subdomain entities)
        """
        entities = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for "FOUND: subdomain.domain.com" pattern
            if line.startswith('FOUND:'):
                subdomain = line.split('FOUND:')[1].strip()
                
                if subdomain:
                    subdomain_entity = self._create_subdomain_entity(subdomain)
                    entities.append(subdomain_entity)
        
        if not entities:
            raise ParserException("No subdomains found in enumeration output")
        
        return entities
    
    def _create_subdomain_entity(self, subdomain: str) -> BaseEntity:
        """Create subdomain entity."""
        entity_id = self.id_generator.generate_id(
            entity_type="subdomain",
            key=subdomain
        )
        
        return BaseEntity(
            id=entity_id,
            type="subdomain",
            properties={
                "subdomain": subdomain
            },
            relationships=[]
        )


class WebAppScanParser(BaseParser):
    """
    Parser for web application scanner output.
    Extracts server info and detected technologies.
    """
    
    def __init__(self):
        super().__init__()
    
    def parse(self, output: str) -> List[BaseEntity]:
        """
        Parse web app scan output.
        
        Expected output format:
            SERVER: Apache/2.4.41
            POWERED-BY: PHP/7.4.3
            CONTENT-TYPE: text/html; charset=UTF-8
            TECH: WordPress
            TECH: jQuery
            STATUS: 200
            
        Args:
            output: Web app scan output
            
        Returns:
            List of BaseEntity (web_app entities with detected technologies)
        """
        entities = []
        lines = output.split('\n')
        
        server = None
        powered_by = None
        content_type = None
        technologies = []
        status_code = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('SERVER:'):
                server = line.split('SERVER:')[1].strip()
            
            elif line.startswith('POWERED-BY:'):
                powered_by = line.split('POWERED-BY:')[1].strip()
            
            elif line.startswith('CONTENT-TYPE:'):
                content_type = line.split('CONTENT-TYPE:')[1].strip()
            
            elif line.startswith('TECH:'):
                tech = line.split('TECH:')[1].strip()
                technologies.append(tech)
            
            elif line.startswith('STATUS:'):
                try:
                    status_code = int(line.split('STATUS:')[1].strip())
                except ValueError:
                    status_code = None
        
        # Create web app entity
        if server or powered_by or technologies:
            web_app_entity = self._create_web_app_entity(
                server=server or "Unknown",
                powered_by=powered_by or "Unknown",
                content_type=content_type or "Unknown",
                technologies=technologies,
                status_code=status_code or 0
            )
            entities.append(web_app_entity)
        
        if not entities:
            raise ParserException("No web application information found")
        
        return entities
    
    def _create_web_app_entity(
        self,
        server: str,
        powered_by: str,
        content_type: str,
        technologies: list,
        status_code: int
    ) -> BaseEntity:
        """Create web application entity."""
        entity_id = self.id_generator.generate_id(
            entity_type="web_app",
            key=f"{server}_{powered_by}"
        )
        
        return BaseEntity(
            id=entity_id,
            type="web_app",
            properties={
                "server": server,
                "powered_by": powered_by,
                "content_type": content_type,
                "technologies": ", ".join(technologies) if technologies else "None",
                "status_code": status_code
            },
            relationships=[]
        )
