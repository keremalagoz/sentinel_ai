"""Sprint 1 Week 2 Integration Tests

End-to-end tests: Tool → Parser → State → History
Tests complete workflow with real tool execution
"""

import unittest
import tempfile
import os
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PyQt6.QtCore import QCoreApplication, QTimer

from src.core.tool_base import (
    PingTool, NmapPingSweepTool, NmapPortScanTool,
    ToolStatus, ToolExecutionSignals
)
from src.core.parser_framework import (
    PingParser, NmapPingSweepParser, NmapPortScanParser
)
from src.core.tool_integration import (
    IntegratedTool, ToolManager, IntegratedToolResult
)
from src.core.sqlite_backend import (
    SQLiteBackend, EntityType, ExecutionStatus, ParseStatus
)
from src.ai.execution_policy import ExecutionPolicy


class TestPingToolIntegration(unittest.TestCase):
    """Test ping tool end-to-end integration"""
    
    @classmethod
    def setUpClass(cls):
        """Create Qt application for async tests"""
        cls.app = QCoreApplication.instance()
        if cls.app is None:
            cls.app = QCoreApplication([])
    
    def setUp(self):
        """Create temporary database and tool"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_file.close()
        self.db_path = self.temp_file.name
        
        self.backend = SQLiteBackend(self.db_path)
        self.policy = ExecutionPolicy()
        
        # Create integrated tool
        tool = PingTool(timeout=10)
        parser = PingParser()
        self.integrated_tool = IntegratedTool(
            tool=tool,
            parser=parser,
            backend=self.backend,
            policy=self.policy
        )
        
        self.result = None
        self.completed = False
    
    def tearDown(self):
        """Clean up"""
        self.backend.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _callback(self, result: IntegratedToolResult):
        """Store result and mark completed"""
        self.result = result
        self.completed = True
        self.app.quit()
    
    def test_ping_localhost_success(self):
        """Test ping localhost (should succeed)"""
        # Execute ping
        self.integrated_tool.execute(
            callback=self._callback,
            target="127.0.0.1",
            count=2
        )
        
        # Wait for completion (with timeout)
        QTimer.singleShot(15000, self.app.quit)  # 15s timeout
        self.app.exec()
        
        # Verify callback was invoked
        self.assertTrue(self.completed, "Callback not invoked")
        self.assertIsNotNone(self.result)
        
        # Verify tool execution
        self.assertEqual(self.result.tool_status, ToolStatus.SUCCESS)
        self.assertEqual(self.result.exit_code, 0)
        self.assertGreater(len(self.result.stdout), 0)
        
        # Verify parsing
        self.assertEqual(self.result.parse_status, ParseStatus.PARSED)
        self.assertEqual(self.result.entities_created, 1)
        
        # Verify state
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 1)
        
        host = hosts[0]
        self.assertEqual(host.data["ip_address"], "127.0.0.1")
        self.assertEqual(host.data["is_alive"], True)
        
        # Verify execution history
        last_exec = self.backend.get_last_execution("ping")
        self.assertIsNotNone(last_exec)
        self.assertEqual(last_exec.status, ExecutionStatus.SUCCESS)
        self.assertEqual(last_exec.parse_status, ParseStatus.PARSED)
        self.assertEqual(last_exec.entities_created, 1)
    
    def test_ping_invalid_host_failure(self):
        """Test ping to invalid host (should fail gracefully)"""
        # Execute ping to non-existent host
        self.integrated_tool.execute(
            callback=self._callback,
            target="192.168.255.255",
            count=1
        )
        
        # Wait for completion
        QTimer.singleShot(15000, self.app.quit)
        self.app.exec()
        
        # Verify callback was invoked
        self.assertTrue(self.completed)
        self.assertIsNotNone(self.result)
        
        # Tool may succeed (exit 0) but no reply
        # Parser should raise exception → PARTIAL_SUCCESS
        if self.result.tool_status == ToolStatus.SUCCESS:
            self.assertEqual(self.result.execution_status, ExecutionStatus.PARTIAL_SUCCESS)
            self.assertEqual(self.result.parse_status, ParseStatus.PARSE_FAILED)
            self.assertEqual(self.result.entities_created, 0)
        
        # Verify no entities created
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 0)
        
        # Verify execution recorded
        last_exec = self.backend.get_last_execution("ping")
        self.assertIsNotNone(last_exec)


class TestToolManager(unittest.TestCase):
    """Test ToolManager with multiple tools"""
    
    @classmethod
    def setUpClass(cls):
        """Create Qt application"""
        cls.app = QCoreApplication.instance()
        if cls.app is None:
            cls.app = QCoreApplication([])
    
    def setUp(self):
        """Create temporary database and manager"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_file.close()
        self.db_path = self.temp_file.name
        
        self.backend = SQLiteBackend(self.db_path)
        self.manager = ToolManager(self.backend)
        
        # Register tools
        self.manager.register_tool(PingTool(timeout=10), PingParser())
        self.manager.register_tool(
            NmapPingSweepTool(timeout=30),
            NmapPingSweepParser()
        )
        self.manager.register_tool(
            NmapPortScanTool(timeout=60),
            NmapPortScanParser()
        )
        
        self.result = None
        self.completed = False
    
    def tearDown(self):
        """Clean up"""
        self.backend.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _callback(self, result: IntegratedToolResult):
        """Store result"""
        self.result = result
        self.completed = True
        self.app.quit()
    
    def test_tool_registration(self):
        """Test tool registration"""
        registered = self.manager.registered_tools
        self.assertEqual(len(registered), 3)
        self.assertIn("ping", registered)
        self.assertIn("nmap_ping_sweep", registered)
        self.assertIn("nmap_port_scan", registered)
    
    def test_get_tool(self):
        """Test getting registered tool"""
        ping_tool = self.manager.get_tool("ping")
        self.assertIsNotNone(ping_tool)
        self.assertEqual(ping_tool.tool.tool_id, "ping")
        
        invalid_tool = self.manager.get_tool("invalid")
        self.assertIsNone(invalid_tool)
    
    def test_execute_tool_via_manager(self):
        """Test executing tool via manager"""
        success = self.manager.execute_tool(
            "ping",
            callback=self._callback,
            target="127.0.0.1",
            count=2
        )
        
        self.assertTrue(success)
        
        # Wait for completion
        QTimer.singleShot(15000, self.app.quit)
        self.app.exec()
        
        # Verify execution
        self.assertTrue(self.completed)
        self.assertIsNotNone(self.result)
        self.assertEqual(self.result.tool_id, "ping")
    
    def test_execute_invalid_tool(self):
        """Test executing non-existent tool"""
        success = self.manager.execute_tool(
            "invalid_tool",
            callback=self._callback,
            target="127.0.0.1"
        )
        
        self.assertFalse(success)


class TestEntityDeduplication(unittest.TestCase):
    """Test entity deduplication with canonical IDs"""
    
    @classmethod
    def setUpClass(cls):
        """Create Qt application"""
        cls.app = QCoreApplication.instance()
        if cls.app is None:
            cls.app = QCoreApplication([])
    
    def setUp(self):
        """Create temporary database"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_file.close()
        self.db_path = self.temp_file.name
        
        self.backend = SQLiteBackend(self.db_path)
        self.manager = ToolManager(self.backend)
        self.manager.register_tool(PingTool(timeout=10), PingParser())
        
        self.results = []
        self.execution_count = 0
    
    def tearDown(self):
        """Clean up"""
        self.backend.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _callback(self, result: IntegratedToolResult):
        """Store result"""
        self.results.append(result)
        self.execution_count += 1
        
        # Quit after 2 executions
        if self.execution_count >= 2:
            self.app.quit()
    
    def test_duplicate_ping_same_host(self):
        """Test pinging same host twice (should create only 1 entity)"""
        # Execute ping twice
        self.manager.execute_tool(
            "ping",
            callback=self._callback,
            target="127.0.0.1",
            count=2
        )
        
        # Wait for first to complete, then execute second
        QTimer.singleShot(3000, lambda: self.manager.execute_tool(
            "ping",
            callback=self._callback,
            target="127.0.0.1",
            count=2
        ))
        
        # Wait for both to complete
        QTimer.singleShot(20000, self.app.quit)
        self.app.exec()
        
        # Verify both executed
        self.assertEqual(len(self.results), 2)
        
        # Verify only 1 host entity (deduplication)
        hosts = self.backend.get_entities_by_type(EntityType.HOST)
        self.assertEqual(len(hosts), 1, "Duplicate host entities created")
        
        # Verify 2 execution history records
        all_execs = self.backend.get_all_executions()
        ping_execs = [e for e in all_execs if e.tool_id == "ping"]
        self.assertEqual(len(ping_execs), 2, "Execution history missing")


class TestExecutionHistory(unittest.TestCase):
    """Test execution history tracking"""
    
    def setUp(self):
        """Create temporary database"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_file.close()
        self.db_path = self.temp_file.name
        self.backend = SQLiteBackend(self.db_path)
    
    def tearDown(self):
        """Clean up"""
        self.backend.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_execution_history_recording(self):
        """Test execution history is properly recorded"""
        from src.core.parser_framework import ToolExecutor, PingParser
        
        executor = ToolExecutor(self.backend)
        parser = PingParser()
        
        # Simulate successful execution
        output = """
Pinging 127.0.0.1 with 32 bytes of data:
Reply from 127.0.0.1: bytes=32 time<1ms TTL=128
"""
        
        result = executor.execute_and_parse(
            tool_id="ping",
            parser=parser,
            output=output
        )
        
        # Verify execution recorded
        last_exec = self.backend.get_last_execution("ping")
        self.assertIsNotNone(last_exec)
        self.assertEqual(last_exec.status, ExecutionStatus.SUCCESS)
        self.assertEqual(last_exec.parse_status, ParseStatus.PARSED)
        self.assertEqual(last_exec.entities_created, 1)
        self.assertIsNone(last_exec.stage_id)
    
    def test_get_executions_by_tool(self):
        """Test filtering execution history by tool"""
        from src.core.parser_framework import ToolExecutor, PingParser
        
        executor = ToolExecutor(self.backend)
        parser = PingParser()
        
        output = "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128"
        
        # Execute 3 times
        for _ in range(3):
            executor.execute_and_parse("ping", parser, output)
            time.sleep(0.01)  # Ensure different timestamps
        
        # Get all executions
        all_execs = self.backend.get_all_executions()
        self.assertEqual(len(all_execs), 3)
        
        # Verify all are ping
        for exec_record in all_execs:
            self.assertEqual(exec_record.tool_id, "ping")


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
