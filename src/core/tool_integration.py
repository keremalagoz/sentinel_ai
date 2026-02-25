"""Tool Integration Layer

Sprint 1 Week 2: Tool + Parser + State integration
Complete workflow: execute → parse → store → history
"""

from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass
import time

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.tool_base import (
    BaseTool, ToolResult, ToolStatus, ToolExecutionSignals
)
from src.core.parser_framework import BaseParser, ToolExecutor as ParserExecutor
from src.core.sqlite_backend import SQLiteBackend, ExecutionStatus, ParseStatus


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
        signals: Optional[IntegratedToolSignals] = None
    ):
        """
        Initialize integrated tool.
        
        Args:
            tool: Tool instance (PingTool, etc.)
            parser: Parser instance (PingParser, etc.)
            backend: SQLite backend for state management
            signals: Optional Qt signals
        """
        self.tool = tool
        self.parser = parser
        self.backend = backend
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
        signals: Optional[IntegratedToolSignals] = None,
        max_concurrent: int = 2,
        max_queue_size: int = 100,
        default_per_tool_limit: int = 1,
    ):
        """
        Initialize tool manager.
        
        Args:
            backend: SQLite backend
            signals: Optional shared signals
            max_concurrent: Aynı anda çalışabilecek maksimum tool sayısı
            max_queue_size: Bekleyen iş kuyruğu üst limiti
            default_per_tool_limit: Tool başına aynı anda çalışabilecek iş limiti
        """
        self.backend = backend
        self.signals = signals or IntegratedToolSignals()
        self.max_concurrent = max(1, int(max_concurrent))
        self.max_queue_size = max(1, int(max_queue_size))
        self.default_per_tool_limit = max(1, int(default_per_tool_limit))
        
        self._tools: Dict[str, IntegratedTool] = {}
        self._active_count = 0
        self._queue: List[Tuple[str, Optional[Callable[[IntegratedToolResult], None]], Dict[str, Any], float]] = []
        self._tool_active_counts: Dict[str, int] = {}
        self._tool_limits: Dict[str, int] = {}
    
    def register_tool(
        self,
        tool: BaseTool,
        parser: BaseParser,
        max_concurrent: Optional[int] = None,
    ) -> None:
        """
        Register integrated tool.
        
        Args:
            tool: Tool instance
            parser: Parser instance
            max_concurrent: Tool başına aynı anda çalışabilecek maksimum iş
        """
        integrated = IntegratedTool(
            tool=tool,
            parser=parser,
            backend=self.backend,
            signals=self.signals
        )
        
        self._tools[tool.tool_id] = integrated
        self._tool_active_counts.setdefault(tool.tool_id, 0)
        self._tool_limits[tool.tool_id] = max(1, int(max_concurrent or self.default_per_tool_limit))

    def _can_start(self, tool_id: str) -> bool:
        """Global ve per-tool limit kontrolü."""
        if self._active_count >= self.max_concurrent:
            return False

        active_for_tool = self._tool_active_counts.get(tool_id, 0)
        limit_for_tool = self._tool_limits.get(tool_id, self.default_per_tool_limit)
        return active_for_tool < limit_for_tool
    
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
            True if tool found and started/queued, False otherwise
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        # Müsait slot varsa hemen başlat
        if self._can_start(tool_id):
            return self._start_tool(tool_id, callback, tool_kwargs)

        # Aksi halde kuyruğa al
        if len(self._queue) >= self.max_queue_size:
            return False

        self._queue.append((tool_id, callback, dict(tool_kwargs), time.time()))
        return True

    def _start_tool(
        self,
        tool_id: str,
        callback: Optional[Callable[[IntegratedToolResult], None]],
        tool_kwargs: Dict[str, Any],
    ) -> bool:
        """Tool çalıştırmayı başlat ve tamamlanınca kuyruğu ilerlet."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        if not self._can_start(tool_id):
            return False

        self._active_count += 1
        self._tool_active_counts[tool_id] = self._tool_active_counts.get(tool_id, 0) + 1

        def _wrapped_callback(result: IntegratedToolResult):
            try:
                if callback:
                    callback(result)
            finally:
                self._active_count = max(0, self._active_count - 1)
                self._tool_active_counts[tool_id] = max(0, self._tool_active_counts.get(tool_id, 1) - 1)
                self._drain_queue()

        try:
            tool.execute(callback=_wrapped_callback, **tool_kwargs)
            return True
        except Exception:
            self._active_count = max(0, self._active_count - 1)
            self._tool_active_counts[tool_id] = max(0, self._tool_active_counts.get(tool_id, 1) - 1)
            return False

    def _drain_queue(self) -> None:
        """Müsait kapasite oldukça kuyruktaki işleri başlat."""
        while self._queue and self._active_count < self.max_concurrent:
            runnable_index = None
            for i, item in enumerate(self._queue):
                tool_id, _, _, _ = item
                if self._can_start(tool_id):
                    runnable_index = i
                    break

            if runnable_index is None:
                # Global slot boş olsa bile per-tool limitler nedeniyle runnable iş yok
                break

            tool_id, callback, kwargs, _enqueued_at = self._queue.pop(runnable_index)
            started = self._start_tool(tool_id, callback, kwargs)
            if not started:
                continue
    
    def cancel_tool(self, tool_id: str) -> bool:
        """
        Cancel running tool.
        
        Returns:
            True if tool found, False otherwise
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        # Kuyruktaki bekleyen işleri de temizle
        self._queue = [
            (t_id, cb, kwargs, ts)
            for (t_id, cb, kwargs, ts) in self._queue
            if t_id != tool_id
        ]
        
        tool.cancel()
        return True

    @property
    def active_executions(self) -> int:
        """Aktif çalışan tool sayısı"""
        return self._active_count

    @property
    def queued_executions(self) -> int:
        """Kuyrukta bekleyen iş sayısı"""
        return len(self._queue)

    @property
    def per_tool_active_executions(self) -> Dict[str, int]:
        """Tool bazlı aktif çalışan iş sayısı."""
        return dict(self._tool_active_counts)
    
    @property
    def registered_tools(self) -> list[str]:
        """Get list of registered tool IDs"""
        return list(self._tools.keys())
