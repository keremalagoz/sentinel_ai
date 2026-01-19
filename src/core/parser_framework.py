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
