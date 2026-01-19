"""Parser Framework Tests

Sprint 1 Week 1 Testing
Coverage: BaseParser, ToolExecutor, example parsers
"""

import unittest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.parser_framework import (
    BaseParser, ToolExecutor, ParserException,
    PingParser, NmapPingSweepParser, NmapPortScanParser
)
from src.core.sqlite_backend import (
    SQLiteBackend, EntityType, ExecutionStatus, ParseStatus
)
from src.core.entity_id_generator import EntityIDGenerator, IDValidator


class TestPingParser(unittest.TestCase):
    """Test PingParser"""
    
    def setUp(self):
        self.parser = PingParser()
    
    def test_parse_successful_ping(self):
        """Test parsing successful ping output"""
        output = """
Pinging 192.168.1.10 with 32 bytes of data:
Reply from 192.168.1.10: bytes=32 time<1ms TTL=64
Reply from 192.168.1.10: bytes=32 time<1ms TTL=64

Ping statistics for 192.168.1.10:
    Packets: Sent = 2, Received = 2, Lost = 0 (0% loss),
"""
        entities = self.parser.parse(output)
        
        self.assertEqual(len(entities), 1)
        
        host = entities[0]
        self.assertEqual(host.entity_type, EntityType.HOST)
        self.assertEqual(host.data["ip_address"], "192.168.1.10")
        self.assertEqual(host.data["is_alive"], True)
        self.assertTrue(IDValidator.validate_host_id(host.id))
    
    def test_parse_failed_ping(self):
        """Test parsing failed ping output (no reply)"""
        output = """
Pinging 192.168.1.99 with 32 bytes of data:
Request timed out.
Request timed out.

Ping statistics for 192.168.1.99:
    Packets: Sent = 2, Received = 0, Lost = 2 (100% loss),
"""
        with self.assertRaises(ParserException):
            self.parser.parse(output)
    
    def test_parse_empty_output(self):
        """Test parsing empty output"""
        with self.assertRaises(ParserException):
            self.parser.parse("")


class TestNmapPingSweepParser(unittest.TestCase):
    """Test NmapPingSweepParser"""
    
    def setUp(self):
        self.parser = NmapPingSweepParser()
    
    def test_parse_single_host(self):
        """Test parsing single alive host"""
        output = """
Starting Nmap 7.80 ( https://nmap.org ) at 2026-01-20 10:00 UTC
Nmap scan report for 192.168.1.10
Host is up (0.00050s latency).

Nmap done: 1 IP address (1 host up) scanned in 0.10 seconds
"""
        entities = self.parser.parse(output)
        
        self.assertEqual(len(entities), 1)
        
        host = entities[0]
        self.assertEqual(host.entity_type, EntityType.HOST)
        self.assertEqual(host.data["ip_address"], "192.168.1.10")
        self.assertEqual(host.data["is_alive"], True)
        self.assertEqual(host.confidence, 1.0)
    
    def test_parse_multiple_hosts(self):
        """Test parsing multiple alive hosts"""
        output = """
Starting Nmap 7.80 ( https://nmap.org ) at 2026-01-20 10:00 UTC
Nmap scan report for 192.168.1.10
Host is up (0.00050s latency).

Nmap scan report for 192.168.1.11
Host is up (0.00070s latency).

Nmap scan report for 192.168.1.12
Host is up (0.00090s latency).

Nmap done: 256 IP addresses (3 hosts up) scanned in 5.20 seconds
"""
        entities = self.parser.parse(output)
        
        self.assertEqual(len(entities), 3)
        
        ips = {e.data["ip_address"] for e in entities}
        self.assertEqual(ips, {"192.168.1.10", "192.168.1.11", "192.168.1.12"})
    
    def test_parse_no_hosts_up(self):
        """Test parsing output with no alive hosts"""
        output = """
Starting Nmap 7.80 ( https://nmap.org ) at 2026-01-20 10:00 UTC

Nmap done: 256 IP addresses (0 hosts up) scanned in 5.20 seconds
"""
        with self.assertRaises(ParserException):
            self.parser.parse(output)


class TestNmapPortScanParser(unittest.TestCase):
    """Test NmapPortScanParser"""
    
    def setUp(self):
        self.parser = NmapPortScanParser()
    
    def test_parse_single_host_single_port(self):
        """Test parsing single host with one open port"""
        output = """
Starting Nmap 7.80 ( https://nmap.org ) at 2026-01-20 10:00 UTC
Nmap scan report for 192.168.1.10
Host is up (0.00050s latency).

PORT   STATE SERVICE
80/tcp open  http

Nmap done: 1 IP address (1 host up) scanned in 0.20 seconds
"""
        entities = self.parser.parse(output)
        
        # Should have: 1 host + 1 port + 1 service
        self.assertEqual(len(entities), 3)
        
        host = entities[0]
        port = entities[1]
        service = entities[2]
        
        self.assertEqual(host.entity_type, EntityType.HOST)
        self.assertEqual(host.data["ip_address"], "192.168.1.10")
        
        self.assertEqual(port.entity_type, EntityType.PORT)
        self.assertEqual(port.data["port"], 80)
        self.assertEqual(port.data["protocol"], "tcp")
        self.assertEqual(port.data["state"], "open")
        
        self.assertEqual(service.entity_type, EntityType.SERVICE)
        self.assertEqual(service.data["service_name"], "http")
    
    def test_parse_multiple_ports(self):
        """Test parsing multiple open ports"""
        output = """
Starting Nmap 7.80 ( https://nmap.org ) at 2026-01-20 10:00 UTC
Nmap scan report for 192.168.1.10
Host is up (0.00050s latency).

PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
443/tcp  open  https
8080/tcp open  http-proxy

Nmap done: 1 IP address (1 host up) scanned in 0.30 seconds
"""
        entities = self.parser.parse(output)
        
        # Should have: 1 host + 4 ports + 4 services = 9 entities
        self.assertEqual(len(entities), 9)
        
        # Check entity types
        hosts = [e for e in entities if e.entity_type == EntityType.HOST]
        ports = [e for e in entities if e.entity_type == EntityType.PORT]
        services = [e for e in entities if e.entity_type == EntityType.SERVICE]
        
        self.assertEqual(len(hosts), 1)
        self.assertEqual(len(ports), 4)
        self.assertEqual(len(services), 4)
        
        # Check port numbers
        port_numbers = {p.data["port"] for p in ports}
        self.assertEqual(port_numbers, {22, 80, 443, 8080})
    
    def test_parse_id_validation(self):
        """Test that all generated IDs are valid"""
        output = """
Nmap scan report for 192.168.1.10
Host is up.

PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
"""
        entities = self.parser.parse(output)
        
        for entity in entities:
            if entity.entity_type == EntityType.HOST:
                self.assertTrue(IDValidator.validate_host_id(entity.id))
            elif entity.entity_type == EntityType.PORT:
                self.assertTrue(IDValidator.validate_port_id(entity.id))
            elif entity.entity_type == EntityType.SERVICE:
                self.assertTrue(IDValidator.validate_service_id(entity.id))
    
    def test_parse_no_ports_open(self):
        """Test parsing output with no open ports"""
        output = """
Nmap scan report for 192.168.1.10
Host is up.

All 1000 scanned ports on 192.168.1.10 are closed

Nmap done: 1 IP address (1 host up) scanned in 0.30 seconds
"""
        with self.assertRaises(ParserException):
            self.parser.parse(output)


class TestToolExecutor(unittest.TestCase):
    """Test ToolExecutor with parser integration"""
    
    def setUp(self):
        """Create temporary database for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_file.close()
        self.db_path = self.temp_file.name
        self.backend = SQLiteBackend(self.db_path)
        self.executor = ToolExecutor(self.backend)
    
    def tearDown(self):
        """Clean up temporary database"""
        self.backend.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_execute_and_parse_success(self):
        """Test successful execution and parsing"""
        parser = PingParser()
        output = """
Reply from 192.168.1.10: bytes=32 time<1ms TTL=64
"""
        
        result = self.executor.execute_and_parse(
            tool_id="ping",
            parser=parser,
            output=output,
            stage_id=1
        )
        
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.parse_status, ParseStatus.PARSED)
        self.assertEqual(result.entities_created, 1)
        self.assertIsNone(result.error_message)
        
        # Verify entity was added to state
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 1)
        
        # Verify execution was recorded
        last_exec = self.backend.get_last_execution("ping")
        self.assertIsNotNone(last_exec)
        self.assertEqual(last_exec.execution_id, result.execution_id)
    
    def test_execute_and_parse_failure(self):
        """Test parser failure (PARTIAL_SUCCESS)"""
        parser = PingParser()
        output = """
Request timed out.
Request timed out.
"""
        
        result = self.executor.execute_and_parse(
            tool_id="ping",
            parser=parser,
            output=output
        )
        
        self.assertEqual(result.status, ExecutionStatus.PARTIAL_SUCCESS)
        self.assertEqual(result.parse_status, ParseStatus.PARSE_FAILED)
        self.assertEqual(result.entities_created, 0)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Parser exception", result.error_message)
        
        # Verify NO entities were added to state
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 0)
        
        # Verify execution was still recorded
        last_exec = self.backend.get_last_execution("ping")
        self.assertIsNotNone(last_exec)
    
    def test_execute_and_parse_empty_output(self):
        """Test empty output handling"""
        parser = NmapPingSweepParser()
        output = """
Starting Nmap 7.80
Nmap done: 0 hosts up
"""
        
        result = self.executor.execute_and_parse(
            tool_id="nmap_ping_sweep",
            parser=parser,
            output=output
        )
        
        self.assertEqual(result.status, ExecutionStatus.PARTIAL_SUCCESS)
        self.assertEqual(result.parse_status, ParseStatus.PARSE_FAILED)
        self.assertEqual(result.entities_created, 0)
    
    def test_has_successful_parse(self):
        """Test checking successful parse"""
        # Initially no execution
        self.assertFalse(self.executor.has_successful_parse("nmap_port_scan"))
        
        # Execute with success
        parser = NmapPortScanParser()
        output = """
Nmap scan report for 192.168.1.10
Host is up.
PORT   STATE SERVICE
80/tcp open  http
"""
        
        self.executor.execute_and_parse(
            tool_id="nmap_port_scan",
            parser=parser,
            output=output
        )
        
        # Now should return True
        self.assertTrue(self.executor.has_successful_parse("nmap_port_scan"))
    
    def test_has_successful_parse_after_failure(self):
        """Test has_successful_parse returns False after parse failure"""
        parser = PingParser()
        output = "Request timed out."
        
        self.executor.execute_and_parse(
            tool_id="ping",
            parser=parser,
            output=output
        )
        
        # Parse failed, should return False
        self.assertFalse(self.executor.has_successful_parse("ping"))
    
    def test_batch_entities_transaction(self):
        """Test batch entity insert is transactional"""
        parser = NmapPortScanParser()
        output = """
Nmap scan report for 192.168.1.10
Host is up.
PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
443/tcp  open  https
"""
        
        result = self.executor.execute_and_parse(
            tool_id="nmap_port_scan",
            parser=parser,
            output=output
        )
        
        # Should have multiple entities (host + ports + services)
        self.assertGreater(result.entities_created, 1)
        
        # Verify all entities were added
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        ports = self.backend.get_entities_by_type(EntityType.PORT)
        services = self.backend.get_entities_by_type(EntityType.SERVICE)
        
        self.assertEqual(len(hosts), 1)
        self.assertEqual(len(ports), 3)
        self.assertEqual(len(services), 3)


class TestParserHelpers(unittest.TestCase):
    """Test BaseParser helper methods"""
    
    def setUp(self):
        self.parser = PingParser()  # Use concrete implementation for testing
    
    def test_create_host_entity(self):
        """Test _create_host_entity helper"""
        host = self.parser._create_host_entity(
            ip="192.168.1.10",
            is_alive=True,
            hostname="test.local",
            os_type="Linux"
        )
        
        self.assertEqual(host.entity_type, EntityType.HOST)
        self.assertEqual(host.data["ip_address"], "192.168.1.10")
        self.assertEqual(host.data["is_alive"], True)
        self.assertEqual(host.data["hostname"], "test.local")
        self.assertEqual(host.data["os_type"], "Linux")
        self.assertTrue(IDValidator.validate_host_id(host.id))
    
    def test_create_port_entity(self):
        """Test _create_port_entity helper"""
        port = self.parser._create_port_entity(
            ip="192.168.1.10",
            port=80,
            protocol="tcp",
            state="open"
        )
        
        self.assertEqual(port.entity_type, EntityType.PORT)
        self.assertEqual(port.data["port"], 80)
        self.assertEqual(port.data["protocol"], "tcp")
        self.assertEqual(port.data["state"], "open")
        self.assertTrue(IDValidator.validate_port_id(port.id))
    
    def test_create_service_entity(self):
        """Test _create_service_entity helper"""
        port_id = "host_192_168_1_10_port_80_tcp"
        service = self.parser._create_service_entity(
            port_id=port_id,
            service_name="http",
            version="Apache 2.4.41",
            banner="Apache/2.4.41 (Ubuntu)"
        )
        
        self.assertEqual(service.entity_type, EntityType.SERVICE)
        self.assertEqual(service.data["service_name"], "http")
        self.assertEqual(service.data["version"], "Apache 2.4.41")
        self.assertEqual(service.data["banner"], "Apache/2.4.41 (Ubuntu)")
        self.assertTrue(IDValidator.validate_service_id(service.id))
    
    def test_create_vulnerability_entity(self):
        """Test _create_vulnerability_entity helper"""
        service_id = "host_192_168_1_10_port_80_tcp_service_http"
        vuln = self.parser._create_vulnerability_entity(
            service_id=service_id,
            vuln_id="CVE-2024-1234",
            severity="high",
            description="SQL Injection",
            exploitable=True
        )
        
        self.assertEqual(vuln.entity_type, EntityType.VULNERABILITY)
        self.assertEqual(vuln.data["vuln_id"], "CVE-2024-1234")
        self.assertEqual(vuln.data["severity"], "high")
        self.assertEqual(vuln.data["exploitable"], True)
        self.assertTrue(IDValidator.validate_vuln_id(vuln.id))
    
    def test_create_dns_entity(self):
        """Test _create_dns_entity helper"""
        dns = self.parser._create_dns_entity(
            domain="example.com",
            record_type="A",
            value="192.168.1.10"
        )
        
        self.assertEqual(dns.entity_type, EntityType.DNS)
        self.assertEqual(dns.data["domain"], "example.com")
        self.assertEqual(dns.data["record_type"], "A")
        self.assertEqual(dns.data["value"], "192.168.1.10")
        self.assertTrue(IDValidator.validate_dns_id(dns.id))


if __name__ == '__main__':
    unittest.main(verbosity=2)
