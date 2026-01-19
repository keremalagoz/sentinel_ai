"""Unit Tests - SQLite Backend and EntityIDGenerator

Sprint 1 Week 1 Testing
Target: 80%+ coverage
"""

import unittest
import tempfile
import os
import time
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.sqlite_backend import (
    SQLiteBackend, BaseEntity, ToolExecutionResult,
    EntityType, RelationshipType, ExecutionStatus, ParseStatus
)
from src.core.entity_id_generator import EntityIDGenerator, IDValidator


class TestEntityIDGenerator(unittest.TestCase):
    """Test EntityIDGenerator canonical ID generation"""
    
    def setUp(self):
        self.gen = EntityIDGenerator()
    
    def test_host_id_ipv4(self):
        """Test IPv4 host ID generation"""
        host_id = self.gen.host_id("192.168.1.10")
        self.assertEqual(host_id, "host_192_168_1_10")
        self.assertTrue(IDValidator.validate_host_id(host_id))
    
    def test_host_id_ipv6(self):
        """Test IPv6 host ID generation"""
        host_id = self.gen.host_id("::1")
        self.assertEqual(host_id, "host___1")
        self.assertTrue(IDValidator.validate_host_id(host_id))
    
    def test_port_id_tcp(self):
        """Test TCP port ID generation"""
        port_id = self.gen.port_id("192.168.1.10", 80, "tcp")
        self.assertEqual(port_id, "host_192_168_1_10_port_80_tcp")
        self.assertTrue(IDValidator.validate_port_id(port_id))
    
    def test_port_id_udp(self):
        """Test UDP port ID generation"""
        port_id = self.gen.port_id("192.168.1.10", 53, "udp")
        self.assertEqual(port_id, "host_192_168_1_10_port_53_udp")
        self.assertTrue(IDValidator.validate_port_id(port_id))
    
    def test_port_id_case_insensitive(self):
        """Test protocol normalization (case insensitive)"""
        port_id1 = self.gen.port_id("192.168.1.10", 80, "TCP")
        port_id2 = self.gen.port_id("192.168.1.10", 80, "tcp")
        self.assertEqual(port_id1, port_id2)
    
    def test_service_id(self):
        """Test service ID generation"""
        port_id = self.gen.port_id("192.168.1.10", 80, "tcp")
        service_id = self.gen.service_id(port_id, "http")
        self.assertEqual(service_id, "host_192_168_1_10_port_80_tcp_service_http")
        self.assertTrue(IDValidator.validate_service_id(service_id))
    
    def test_service_id_space_normalization(self):
        """Test service name with spaces"""
        port_id = self.gen.port_id("192.168.1.10", 80, "tcp")
        service_id = self.gen.service_id(port_id, "Apache httpd")
        self.assertIn("apache_httpd", service_id)
    
    def test_vuln_id_cve(self):
        """Test vulnerability ID with CVE"""
        service_id = "host_192_168_1_10_port_80_tcp_service_http"
        vuln_id = self.gen.vuln_id(service_id, "CVE-2024-1234")
        self.assertIn("vuln_cve_2024_1234", vuln_id)
        self.assertTrue(IDValidator.validate_vuln_id(vuln_id))
    
    def test_vuln_id_generic(self):
        """Test vulnerability ID with generic type"""
        service_id = "host_192_168_1_10_port_22_tcp_service_ssh"
        vuln_id = self.gen.vuln_id(service_id, "weak_cipher")
        self.assertIn("vuln_weak_cipher", vuln_id)
    
    def test_web_resource_id(self):
        """Test web resource ID with hash"""
        service_id = "host_192_168_1_10_port_80_tcp_service_http"
        web_id = self.gen.web_resource_id(service_id, "http://192.168.1.10/admin")
        self.assertIn("web_hash_", web_id)
        self.assertTrue(IDValidator.validate_web_resource_id(web_id))
    
    def test_web_resource_id_deterministic(self):
        """Test web resource ID is deterministic (same URL -> same ID)"""
        service_id = "host_192_168_1_10_port_80_tcp_service_http"
        web_id1 = self.gen.web_resource_id(service_id, "http://example.com/admin")
        web_id2 = self.gen.web_resource_id(service_id, "http://example.com/admin")
        self.assertEqual(web_id1, web_id2)
    
    def test_dns_id(self):
        """Test DNS ID generation"""
        dns_id = self.gen.dns_id("example.com")
        self.assertEqual(dns_id, "dns_example_com")
        self.assertTrue(IDValidator.validate_dns_id(dns_id))
    
    def test_dns_id_subdomain(self):
        """Test DNS ID with subdomain"""
        dns_id = self.gen.dns_id("sub.example.com")
        self.assertEqual(dns_id, "dns_sub_example_com")
    
    def test_cert_id(self):
        """Test certificate ID generation"""
        cert_id = self.gen.cert_id("AB:CD:EF:12:34")
        self.assertEqual(cert_id, "cert_abcdef1234")
        self.assertTrue(IDValidator.validate_cert_id(cert_id))
    
    def test_credential_id(self):
        """Test credential ID generation"""
        service_id = "host_192_168_1_10_port_22_tcp_service_ssh"
        cred_id = self.gen.credential_id("admin", service_id)
        self.assertEqual(cred_id, f"cred_admin_{service_id}")
        self.assertTrue(IDValidator.validate_cred_id(cred_id))
    
    def test_file_id(self):
        """Test file ID generation"""
        host_id = self.gen.host_id("192.168.1.10")
        file_id = self.gen.file_id(host_id, "/etc/passwd")
        self.assertIn("file_host_192_168_1_10_hash_", file_id)
        self.assertTrue(IDValidator.validate_file_id(file_id))


class TestSQLiteBackend(unittest.TestCase):
    """Test SQLite backend storage and queries"""
    
    def setUp(self):
        """Create temporary database for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_file.close()
        self.db_path = self.temp_file.name
        self.backend = SQLiteBackend(self.db_path)
    
    def tearDown(self):
        """Clean up temporary database"""
        self.backend.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_database_creation(self):
        """Test database and tables are created"""
        self.assertTrue(os.path.exists(self.db_path))
        
        # Verify tables exist
        cursor = self.backend.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        self.assertIn('entities', tables)
        self.assertIn('entity_relationships', tables)
        self.assertIn('tool_executions', tables)
    
    def test_insert_single_entity(self):
        """Test inserting a single entity"""
        entity = BaseEntity(
            id="host_192_168_1_10",
            entity_type=EntityType.HOST,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=0.95,
            data={"ip_address": "192.168.1.10", "is_alive": True}
        )
        
        self.backend.insert_entity(entity)
        
        # Verify entity is in database
        retrieved = self.backend.get_entity("host_192_168_1_10")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, entity.id)
        self.assertEqual(retrieved.data["ip_address"], "192.168.1.10")
    
    def test_batch_insert_transaction(self):
        """Test atomic batch insert with transaction"""
        entities = [
            BaseEntity(
                id=f"host_192_168_1_{i}",
                entity_type=EntityType.HOST,
                created_at=time.time(),
                updated_at=time.time(),
                confidence=1.0,
                data={"ip_address": f"192.168.1.{i}"}
            )
            for i in range(10, 20)
        ]
        
        count = self.backend.add_entities_batch(entities)
        
        self.assertEqual(count, 10)
        
        # Verify all entities are in database
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 10)
    
    def test_batch_insert_rollback_on_exception(self):
        """Test transaction rollback on exception during batch insert"""
        # Create entities
        entities = [
            BaseEntity(
                id=f"host_192_168_1_{i}",
                entity_type=EntityType.HOST,
                created_at=time.time(),
                updated_at=time.time(),
                confidence=1.0,
                data={"ip_address": f"192.168.1.{i}"}
            )
            for i in range(10, 15)
        ]
        
        # Simulate exception during batch insert
        # Inject invalid entity to cause exception
        try:
            with self.backend.transaction():
                cursor = self.backend.connection.cursor()
                
                # Insert first 3 entities
                for entity in entities[:3]:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO entities 
                        (id, entity_type, created_at, updated_at, confidence, data)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entity.id,
                            entity.entity_type,
                            entity.created_at,
                            entity.updated_at,
                            entity.confidence,
                            json.dumps(entity.data)
                        )
                    )
                
                # Simulate parser exception
                raise Exception("Simulated parser exception")
        except Exception:
            pass
        
        # Verify NO entities were inserted (rollback)
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 0)
    
    def test_entity_replacement(self):
        """Test entity replacement (INSERT OR REPLACE)"""
        entity1 = BaseEntity(
            id="host_192_168_1_10",
            entity_type=EntityType.HOST,
            created_at=time.time(),
            updated_at=time.time(),
            confidence=0.8,
            data={"ip_address": "192.168.1.10", "hostname": "old"}
        )
        
        self.backend.insert_entity(entity1)
        
        # Update entity
        entity2 = BaseEntity(
            id="host_192_168_1_10",
            entity_type=EntityType.HOST,
            created_at=entity1.created_at,
            updated_at=time.time(),
            confidence=0.95,
            data={"ip_address": "192.168.1.10", "hostname": "new"}
        )
        
        self.backend.insert_entity(entity2)
        
        # Verify entity was replaced (not duplicated)
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 1)
        
        retrieved = self.backend.get_entity("host_192_168_1_10")
        self.assertEqual(retrieved.data["hostname"], "new")
        self.assertEqual(retrieved.confidence, 0.95)
    
    def test_add_relationship(self):
        """Test adding entity relationships"""
        # Create host and port entities
        host = BaseEntity(
            id="host_192_168_1_10",
            entity_type=EntityType.HOST,
            created_at=time.time(),
            updated_at=time.time(),
            data={"ip_address": "192.168.1.10"}
        )
        
        port = BaseEntity(
            id="host_192_168_1_10_port_80_tcp",
            entity_type=EntityType.PORT,
            created_at=time.time(),
            updated_at=time.time(),
            data={"port": 80, "protocol": "tcp", "state": "open"}
        )
        
        self.backend.insert_entity(host)
        self.backend.insert_entity(port)
        
        # Add relationship
        self.backend.add_relationship(
            host.id, port.id, RelationshipType.HAS_PORT
        )
        
        # Verify relationship
        ports = self.backend.get_children(host.id, RelationshipType.HAS_PORT)
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0].id, port.id)
    
    def test_get_children_query(self):
        """Test querying child entities"""
        # Create host with multiple ports
        host_id = "host_192_168_1_10"
        host = BaseEntity(
            id=host_id,
            entity_type=EntityType.HOST,
            created_at=time.time(),
            updated_at=time.time(),
            data={"ip_address": "192.168.1.10"}
        )
        self.backend.insert_entity(host)
        
        # Create 3 ports
        for port_num in [80, 443, 8080]:
            port_id = f"{host_id}_port_{port_num}_tcp"
            port = BaseEntity(
                id=port_id,
                entity_type=EntityType.PORT,
                created_at=time.time(),
                updated_at=time.time(),
                data={"port": port_num, "protocol": "tcp"}
            )
            self.backend.insert_entity(port)
            self.backend.add_relationship(host_id, port_id, RelationshipType.HAS_PORT)
        
        # Query ports
        ports = self.backend.get_children(host_id, RelationshipType.HAS_PORT)
        self.assertEqual(len(ports), 3)
        
        port_numbers = {p.data["port"] for p in ports}
        self.assertEqual(port_numbers, {80, 443, 8080})
    
    def test_record_execution(self):
        """Test recording tool execution"""
        result = ToolExecutionResult(
            execution_id="exec_123",
            tool_id="nmap_ping_sweep",
            stage_id=1,
            status=ExecutionStatus.SUCCESS,
            parse_status=ParseStatus.PARSED,
            raw_output="Nmap output...",
            started_at=time.time(),
            completed_at=time.time() + 5,
            entities_created=54
        )
        
        self.backend.record_execution(result)
        
        # Verify execution is recorded
        last_exec = self.backend.get_last_execution("nmap_ping_sweep")
        self.assertIsNotNone(last_exec)
        self.assertEqual(last_exec.execution_id, "exec_123")
        self.assertEqual(last_exec.entities_created, 54)
    
    def test_has_tool_executed(self):
        """Test checking if tool has executed"""
        # Tool not executed
        self.assertFalse(self.backend.has_tool_executed("nmap_port_scan"))
        
        # Execute tool
        result = ToolExecutionResult(
            execution_id="exec_456",
            tool_id="nmap_port_scan",
            status=ExecutionStatus.SUCCESS,
            parse_status=ParseStatus.PARSED,
            raw_output="Output...",
            started_at=time.time(),
            completed_at=time.time()
        )
        self.backend.record_execution(result)
        
        # Tool executed
        self.assertTrue(self.backend.has_tool_executed("nmap_port_scan"))
    
    def test_partial_success_execution(self):
        """Test PARTIAL_SUCCESS execution (tool ran, parse failed)"""
        result = ToolExecutionResult(
            execution_id="exec_789",
            tool_id="nmap_vuln_scan",
            status=ExecutionStatus.PARTIAL_SUCCESS,
            parse_status=ParseStatus.PARSE_FAILED,
            raw_output="Weird output...",
            started_at=time.time(),
            completed_at=time.time() + 10,
            entities_created=0,
            error_message="Parser exception: Unexpected format"
        )
        
        self.backend.record_execution(result)
        
        # Verify partial success is recorded
        last_exec = self.backend.get_last_execution("nmap_vuln_scan")
        self.assertEqual(last_exec.status, ExecutionStatus.PARTIAL_SUCCESS)
        self.assertEqual(last_exec.parse_status, ParseStatus.PARSE_FAILED)
        self.assertEqual(last_exec.entities_created, 0)
        
        # has_tool_executed should return True (tool ran)
        self.assertTrue(self.backend.has_tool_executed("nmap_vuln_scan"))
    
    def test_prune_stale_entities(self):
        """Test TTL-based entity pruning"""
        # Create old entities (2 hours ago)
        old_time = time.time() - 7200
        old_entities = [
            BaseEntity(
                id=f"host_192_168_1_{i}",
                entity_type=EntityType.HOST,
                created_at=old_time,
                updated_at=old_time,
                data={"ip_address": f"192.168.1.{i}"}
            )
            for i in range(10, 15)
        ]
        
        # Create new entities (now)
        new_entities = [
            BaseEntity(
                id=f"host_192_168_1_{i}",
                entity_type=EntityType.HOST,
                created_at=time.time(),
                updated_at=time.time(),
                data={"ip_address": f"192.168.1.{i}"}
            )
            for i in range(15, 20)
        ]
        
        self.backend.add_entities_batch(old_entities + new_entities)
        
        # Prune entities older than 1 hour
        deleted_count = self.backend.prune_stale_entities(ttl_seconds=3600)
        
        self.assertEqual(deleted_count, 5)  # 5 old entities deleted
        
        # Verify only new entities remain
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 5)
    
    def test_checkpoint_and_restore(self):
        """Test state checkpoint and restore"""
        # Create some entities
        entities = [
            BaseEntity(
                id=f"host_192_168_1_{i}",
                entity_type=EntityType.HOST,
                created_at=time.time(),
                updated_at=time.time(),
                data={"ip_address": f"192.168.1.{i}"}
            )
            for i in range(10, 15)
        ]
        self.backend.add_entities_batch(entities)
        
        # Checkpoint
        checkpoint_path = self.db_path + ".checkpoint"
        self.backend.checkpoint(checkpoint_path)
        
        # Verify checkpoint file exists
        self.assertTrue(os.path.exists(checkpoint_path))
        
        # Delete all entities
        cursor = self.backend.connection.cursor()
        cursor.execute("DELETE FROM entities")
        self.backend.connection.commit()
        
        # Verify entities deleted
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 0)
        
        # Restore from checkpoint
        self.backend.restore(checkpoint_path)
        
        # Verify entities restored
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 5)
        
        # Cleanup checkpoint file
        os.unlink(checkpoint_path)
    
    def test_stats(self):
        """Test database statistics"""
        # Create mixed entities
        entities = [
            BaseEntity(
                id=f"host_192_168_1_{i}",
                entity_type=EntityType.HOST,
                created_at=time.time(),
                updated_at=time.time(),
                data={}
            )
            for i in range(10, 15)
        ]
        
        entities += [
            BaseEntity(
                id=f"host_192_168_1_10_port_{port}_tcp",
                entity_type=EntityType.PORT,
                created_at=time.time(),
                updated_at=time.time(),
                data={}
            )
            for port in [80, 443, 8080]
        ]
        
        self.backend.add_entities_batch(entities)
        
        # Record execution
        self.backend.record_execution(ToolExecutionResult(
            execution_id="exec_1",
            tool_id="nmap",
            status=ExecutionStatus.SUCCESS,
            parse_status=ParseStatus.PARSED,
            raw_output="",
            started_at=time.time(),
            completed_at=time.time()
        ))
        
        # Get stats
        stats = self.backend.get_stats()
        
        self.assertEqual(stats["entities"][EntityType.HOST], 5)
        self.assertEqual(stats["entities"][EntityType.PORT], 3)
        self.assertEqual(stats["total_executions"], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
