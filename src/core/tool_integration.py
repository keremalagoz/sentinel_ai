"""Tool Integration Layer

Sprint 1 Week 2: Tool + Parser + State integration
Complete workflow: execute → parse → store → history
"""

from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import time

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.tool_base import (
    BaseTool, ToolResult, ToolStatus, ToolExecutionSignals
)
from src.core.parser_framework import BaseParser, ToolExecutor as ParserExecutor
from src.core.sqlite_backend import SQLiteBackend, ExecutionStatus, ParseStatus
from src.ai.execution_policy import ExecutionPolicy


@dataclass
class IntegratedToolResult:
    """Integrated tool execution result with parsing and state"""
    tool_id: str
    execution_id: str
    tool_status: ToolStatus
    execution_status: ExecutionStatus
    parse_status: ParseStatus
    entities_created: int
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    error_message: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if execution and parsing succeeded"""
        return (
            self.tool_status == ToolStatus.SUCCESS and
            self.execution_status == ExecutionStatus.SUCCESS
        )


class IntegratedToolSignals(QObject):
    """Qt signals for integrated tool execution"""
    started = pyqtSignal(str, str)  # tool_id, execution_id
    tool_finished = pyqtSignal(str, object)  # tool_id, ToolResult
    parsed = pyqtSignal(str, int)  # tool_id, entities_created
    completed = pyqtSignal(str, object)  # tool_id, IntegratedToolResult
    error = pyqtSignal(str, str)  # tool_id, error_message


class IntegratedTool:
    """
    Integrated tool: combines tool execution, parsing, and state management.
    
    Workflow:
    1. Execute tool (QProcess)
    2. Parse output (Parser)
    3. Store entities (SQLiteBackend)
    4. Record execution history
    
    Usage:
        tool = IntegratedTool(ping_tool, ping_parser, backend)
        tool.execute(callback=my_callback, target="192.168.1.10")
    """
    
    def __init__(
        self,
        tool: BaseTool,
        parser: BaseParser,
        backend: SQLiteBackend,
        policy: Optional[ExecutionPolicy] = None,
        signals: Optional[IntegratedToolSignals] = None
    ):
        """
        Initialize integrated tool.
        
        Args:
            tool: Tool instance (PingTool, etc.)
            parser: Parser instance (PingParser, etc.)
            backend: SQLite backend for state management
            policy: Execution policy (default: safe policy)
            signals: Optional Qt signals
        """
        self.tool = tool
        self.parser = parser
        self.backend = backend
        self.policy = policy or ExecutionPolicy()
        self.signals = signals or IntegratedToolSignals()
        
        # Parser executor for state integration
        self.parser_executor = ParserExecutor(backend)
        
        # Current execution context
        self._current_execution_id: Optional[str] = None
        self._current_callback: Optional[Callable[[IntegratedToolResult], None]] = None
        self._started_at: Optional[float] = None
    
    def execute(
        self,
        callback: Optional[Callable[[IntegratedToolResult], None]] = None,
        stage_id: Optional[int] = None,
        **tool_kwargs
    ) -> None:
        """
        Execute tool with full integration.
        
        Args:
            callback: Completion callback
            stage_id: Optional tactical stage ID
            **tool_kwargs: Tool-specific parameters (target, ports, etc.)
        """
        self._current_callback = callback
        self._started_at = time.time()
        
        # Generate execution ID
        import uuid
        self._current_execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # Emit started signal
        self.signals.started.emit(self.tool.tool_id, self._current_execution_id)
        
        # Execute tool with callback
        self.tool.execute(callback=self._on_tool_finished, **tool_kwargs)
    
    def cancel(self) -> None:
        """Cancel running execution"""
        self.tool.cancel()
    
    def _on_tool_finished(self, tool_result: ToolResult) -> None:
        """
        Handle tool execution completion.
        
        Parse output and store entities.
        """
        # Emit tool finished signal
        self.signals.tool_finished.emit(self.tool.tool_id, tool_result)
        
        # If tool failed, create failed integrated result
        if tool_result.status != ToolStatus.SUCCESS:
            # Record failed execution in history
            from src.core.sqlite_backend import ToolExecutionResult as ToolExecResult
            
            failed_exec = ToolExecResult(
                execution_id=self._current_execution_id or "unknown",
                tool_id=self.tool.tool_id,
                stage_id=None,
                status=ExecutionStatus.FAILED,
                parse_status=ParseStatus.EMPTY_OUTPUT,
                raw_output=tool_result.stdout,
                started_at=tool_result.started_at,
                completed_at=tool_result.finished_at,
                entities_created=0,
                error_message=tool_result.error_message
            )
            
            self.backend.record_execution(failed_exec)
            
            integrated_result = IntegratedToolResult(
                tool_id=self.tool.tool_id,
                execution_id=self._current_execution_id or "unknown",
                tool_status=tool_result.status,
                execution_status=ExecutionStatus.FAILED,
                parse_status=ParseStatus.EMPTY_OUTPUT,
                entities_created=0,
                stdout=tool_result.stdout,
                stderr=tool_result.stderr,
                exit_code=tool_result.exit_code,
                duration=tool_result.duration,
                error_message=tool_result.error_message
            )
            
            self._emit_completed(integrated_result)
            return
        
        # Tool succeeded, parse output
        try:
            parse_result = self.parser_executor.execute_and_parse(
                tool_id=self.tool.tool_id,
                parser=self.parser,
                output=tool_result.stdout,
                stage_id=None  # Stage tracking TBD
            )
            
            # Emit parsed signal
            self.signals.parsed.emit(self.tool.tool_id, parse_result.entities_created)
            
            # Create integrated result
            integrated_result = IntegratedToolResult(
                tool_id=self.tool.tool_id,
                execution_id=parse_result.execution_id,
                tool_status=tool_result.status,
                execution_status=parse_result.status,
                parse_status=parse_result.parse_status,
                entities_created=parse_result.entities_created,
                stdout=tool_result.stdout,
                stderr=tool_result.stderr,
                exit_code=tool_result.exit_code,
                duration=tool_result.duration,
                error_message=parse_result.error_message
            )
            
            self._emit_completed(integrated_result)
        
        except Exception as e:
            # Unexpected error during parsing
            integrated_result = IntegratedToolResult(
                tool_id=self.tool.tool_id,
                execution_id=self._current_execution_id or "unknown",
                tool_status=tool_result.status,
                execution_status=ExecutionStatus.FAILED,
                parse_status=ParseStatus.PARSE_FAILED,
                entities_created=0,
                stdout=tool_result.stdout,
                stderr=tool_result.stderr,
                exit_code=tool_result.exit_code,
                duration=tool_result.duration,
                error_message=f"Unexpected parsing error: {str(e)}"
            )
            
            self.signals.error.emit(self.tool.tool_id, str(e))
            self._emit_completed(integrated_result)
    
    def _emit_completed(self, result: IntegratedToolResult) -> None:
        """Emit completion signal and invoke callback"""
        self.signals.completed.emit(self.tool.tool_id, result)
        
        if self._current_callback:
            self._current_callback(result)


class ToolManager:
    """
    Manages multiple integrated tools.
    
    Provides tool registry and execution coordination.
    """
    
    def __init__(
        self,
        backend: SQLiteBackend,
        policy: Optional[ExecutionPolicy] = None,
        signals: Optional[IntegratedToolSignals] = None
    ):
        """
        Initialize tool manager.
        
        Args:
            backend: SQLite backend
            policy: Execution policy
            signals: Optional shared signals
        """
        self.backend = backend
        self.policy = policy or ExecutionPolicy()
        self.signals = signals or IntegratedToolSignals()
        
        self._tools: Dict[str, IntegratedTool] = {}
    
    def register_tool(
        self,
        tool: BaseTool,
        parser: BaseParser
    ) -> None:
        """
        Register integrated tool.
        
        Args:
            tool: Tool instance
            parser: Parser instance
        """
        integrated = IntegratedTool(
            tool=tool,
            parser=parser,
            backend=self.backend,
            policy=self.policy,
            signals=self.signals
        )
        
        self._tools[tool.tool_id] = integrated
    
    def get_tool(self, tool_id: str) -> Optional[IntegratedTool]:
        """Get registered tool by ID"""
        return self._tools.get(tool_id)
    
    def execute_tool(
        self,
        tool_id: str,
        callback: Optional[Callable[[IntegratedToolResult], None]] = None,
        **tool_kwargs
    ) -> bool:
        """
        Execute registered tool.
        
        Args:
            tool_id: Tool ID
            callback: Completion callback
            **tool_kwargs: Tool parameters
            
        Returns:
            True if tool found and started, False otherwise
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return False
        
        tool.execute(callback=callback, **tool_kwargs)
        return True
    
    def cancel_tool(self, tool_id: str) -> bool:
        """
        Cancel running tool.
        
        Returns:
            True if tool found, False otherwise
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return False
        
        tool.cancel()
        return True
    
    @property
    def registered_tools(self) -> list[str]:
        """Get list of registered tool IDs"""
        return list(self._tools.keys())
