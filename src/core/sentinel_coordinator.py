"""Sentinel Coordinator - UI + ToolManager Bridge

Action Planner v2.1 - UI Integration
Connects ToolManager with TerminalView for complete workflow
"""

from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal

from src.core.tool_integration import ToolManager, IntegratedToolResult
from src.core.tool_base import PingTool, NmapPingSweepTool, NmapPortScanTool
from src.core.parser_framework import PingParser, NmapPingSweepParser, NmapPortScanParser
from src.core.sqlite_backend import SQLiteBackend
from src.ai.execution_policy import ExecutionPolicy


class SentinelCoordinator(QObject):
    """
    Coordinates between UI (TerminalView) and core systems (ToolManager).
    
    Responsibilities:
    - Initialize ToolManager with backend
    - Register available tools
    - Route terminal commands to appropriate tools
    - Emit UI-friendly signals
    - Maintain execution state
    
    Signal Flow:
    TerminalView → Coordinator → ToolManager → Tool → Parser → Backend
                                              ↓
                    UI Update ← Signal ← Result
    """
    
    # Signals for UI
    tool_started = Signal(str, str)  # tool_id, execution_id
    tool_output = Signal(str, str)  # tool_id, output_chunk
    tool_completed = Signal(str, object)  # tool_id, IntegratedToolResult
    tool_error = Signal(str, str)  # tool_id, error_message
    
    def __init__(self, db_path: str = "sentinel_state.db", parent: Optional[QObject] = None):
        """
        Initialize coordinator.
        
        Args:
            db_path: SQLite database path (default: "sentinel_state.db")
            parent: Optional Qt parent
        """
        super().__init__(parent)
        
        # Backend
        self.backend = SQLiteBackend(db_path)
        
        # Policy
        self.policy = ExecutionPolicy()
        
        # Tool Manager
        self.manager = ToolManager(
            backend=self.backend,
            policy=self.policy
        )
        
        # Register tools
        self._register_default_tools()
        
        # Connect ToolManager signals to coordinator signals
        self.manager.signals.started.connect(self._on_tool_started)
        self.manager.signals.completed.connect(self._on_tool_completed)
        self.manager.signals.error.connect(self._on_tool_error)
    
    def _register_default_tools(self):
        """Register Action Planner v2.1 tools"""
        # Ping
        self.manager.register_tool(
            tool=PingTool(timeout=10),
            parser=PingParser()
        )
        
        # Nmap Ping Sweep
        self.manager.register_tool(
            tool=NmapPingSweepTool(timeout=30),
            parser=NmapPingSweepParser()
        )
        
        # Nmap Port Scan
        self.manager.register_tool(
            tool=NmapPortScanTool(timeout=120),
            parser=NmapPortScanParser()
        )
    
    def execute_ping(self, target: str, count: int = 4) -> bool:
        """
        Execute ping tool.
        
        Args:
            target: IP or hostname
            count: Number of pings
            
        Returns:
            True if started successfully
        """
        return self.manager.execute_tool(
            "ping",
            callback=None,  # Use signals instead
            target=target,
            count=count
        )
    
    def execute_ping_sweep(self, target: str = None, target_range: str = None) -> bool:
        """
        Execute nmap ping sweep.
        
        Args:
            target: CIDR notation (192.168.1.0/24) - deprecated, use target_range
            target_range: CIDR notation (192.168.1.0/24)
            
        Returns:
            True if started successfully
        """
        # Backward compatibility
        final_target = target_range or target
        if not final_target:
            raise ValueError("Either target or target_range must be provided")
        
        return self.manager.execute_tool(
            "nmap_ping_sweep",
            callback=None,
            target=final_target
        )
    
    def execute_port_scan(self, target: str, ports: str = "1-1000", scan_type: str = "sT") -> bool:
        """
        Execute nmap port scan.
        
        Args:
            target: IP address
            ports: Port range (1-1000, 80,443, etc.)
            scan_type: Scan type (sT, sS, sU)
            
        Returns:
            True if started successfully
        """
        return self.manager.execute_tool(
            "nmap_port_scan",
            callback=None,
            target=target,
            ports=ports,
            scan_type=scan_type
        )
    
    def cancel_tool(self, tool_id: str) -> bool:
        """
        Cancel running tool.
        
        Args:
            tool_id: Tool ID to cancel
            
        Returns:
            True if tool found and cancelled
        """
        return self.manager.cancel_tool(tool_id)
    
    def get_available_tools(self) -> list:
        """Get list of registered tool IDs"""
        return self.manager.registered_tools
    
    def get_backend_stats(self) -> dict:
        """Get backend statistics"""
        return self.backend.get_stats()
    
    def _on_tool_started(self, tool_id: str, execution_id: str):
        """Forward tool started event to UI"""
        self.tool_started.emit(tool_id, execution_id)
    
    def _on_tool_completed(self, tool_id: str, result: IntegratedToolResult):
        """Forward tool completion to UI"""
        self.tool_completed.emit(tool_id, result)
    
    def _on_tool_error(self, tool_id: str, error_message: str):
        """Forward tool error to UI"""
        self.tool_error.emit(tool_id, error_message)
    
    def cleanup(self):
        """Clean up resources"""
        if self.backend:
            self.backend.close()
