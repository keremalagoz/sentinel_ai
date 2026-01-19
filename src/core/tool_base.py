"""Tool Execution Base Classes

Sprint 1 Week 2: Tool execution with QProcess integration
Async tool execution, output capture, timeout handling
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import time

from PySide6.QtCore import QProcess, QTimer, Signal, QObject


class ToolStatus(str, Enum):
    """Tool execution status"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    """Tool execution result"""
    tool_id: str
    status: ToolStatus
    stdout: str
    stderr: str
    exit_code: int
    started_at: float
    finished_at: float
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Execution duration in seconds"""
        return self.finished_at - self.started_at
    
    @property
    def success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ToolStatus.SUCCESS


class ToolExecutionSignals(QObject):
    """Qt signals for tool execution events"""
    started = Signal(str)  # tool_id
    stdout_ready = Signal(str, str)  # tool_id, data
    stderr_ready = Signal(str, str)  # tool_id, data
    finished = Signal(str, object)  # tool_id, ToolResult
    error = Signal(str, str)  # tool_id, error_message


class BaseTool(ABC):
    """
    Base class for all tools.
    
    Provides QProcess integration for async execution.
    Subclasses implement build_command() for specific tools.
    """
    
    def __init__(
        self,
        tool_id: str,
        timeout: int = 30,
        signals: Optional[ToolExecutionSignals] = None
    ):
        """
        Initialize tool.
        
        Args:
            tool_id: Unique tool identifier
            timeout: Execution timeout in seconds
            signals: Optional Qt signals for event handling
        """
        self.tool_id = tool_id
        self.timeout = timeout
        self.signals = signals or ToolExecutionSignals()
        
        self.process: Optional[QProcess] = None
        self.timer: Optional[QTimer] = None
        self.status = ToolStatus.IDLE
        self.started_at: Optional[float] = None
        
        self._stdout_buffer = []
        self._stderr_buffer = []
        self._result_callback: Optional[Callable[[ToolResult], None]] = None
    
    @abstractmethod
    def build_command(self, **kwargs) -> List[str]:
        """
        Build command line arguments.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            List of command line arguments [program, arg1, arg2, ...]
        """
        pass
    
    def execute(
        self,
        callback: Optional[Callable[[ToolResult], None]] = None,
        **kwargs
    ) -> None:
        """
        Execute tool asynchronously.
        
        Args:
            callback: Optional callback for result
            **kwargs: Tool-specific parameters
        """
        if self.status == ToolStatus.RUNNING:
            raise RuntimeError(f"Tool {self.tool_id} is already running")
        
        self._result_callback = callback
        self._stdout_buffer = []
        self._stderr_buffer = []
        
        # Build command
        command = self.build_command(**kwargs)
        if not command:
            self._handle_error("Empty command")
            return
        
        program = command[0]
        args = command[1:]
        
        # Create QProcess
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        
        # Create timeout timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timeout)
        self.timer.setSingleShot(True)
        
        # Start execution
        self.status = ToolStatus.RUNNING
        self.started_at = time.time()
        
        self.process.start(program, args)
        self.timer.start(self.timeout * 1000)
        
        self.signals.started.emit(self.tool_id)
    
    def cancel(self) -> None:
        """Cancel running execution"""
        if self.status != ToolStatus.RUNNING:
            return
        
        if self.process:
            self.process.kill()
        
        if self.timer:
            self.timer.stop()
        
        self.status = ToolStatus.CANCELLED
        
        result = ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.CANCELLED,
            stdout="".join(self._stdout_buffer),
            stderr="".join(self._stderr_buffer),
            exit_code=-1,
            started_at=self.started_at or time.time(),
            finished_at=time.time(),
            error_message="Execution cancelled by user"
        )
        
        self._emit_result(result)
    
    def _on_stdout(self) -> None:
        """Handle stdout data"""
        if not self.process:
            return
        
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self._stdout_buffer.append(data)
        self.signals.stdout_ready.emit(self.tool_id, data)
    
    def _on_stderr(self) -> None:
        """Handle stderr data"""
        if not self.process:
            return
        
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self._stderr_buffer.append(data)
        self.signals.stderr_ready.emit(self.tool_id, data)
    
    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle process finished"""
        if self.timer:
            self.timer.stop()
        
        if self.status == ToolStatus.CANCELLED:
            return
        
        self.status = ToolStatus.SUCCESS if exit_code == 0 else ToolStatus.FAILED
        
        result = ToolResult(
            tool_id=self.tool_id,
            status=self.status,
            stdout="".join(self._stdout_buffer),
            stderr="".join(self._stderr_buffer),
            exit_code=exit_code,
            started_at=self.started_at or time.time(),
            finished_at=time.time(),
            error_message=None if exit_code == 0 else f"Process exited with code {exit_code}"
        )
        
        self._emit_result(result)
    
    def _on_timeout(self) -> None:
        """Handle execution timeout"""
        if self.process:
            self.process.kill()
        
        self.status = ToolStatus.TIMEOUT
        
        result = ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.TIMEOUT,
            stdout="".join(self._stdout_buffer),
            stderr="".join(self._stderr_buffer),
            exit_code=-1,
            started_at=self.started_at or time.time(),
            finished_at=time.time(),
            error_message=f"Execution timeout after {self.timeout} seconds"
        )
        
        self._emit_result(result)
    
    def _on_error(self, error: QProcess.ProcessError) -> None:
        """Handle process error"""
        if self.timer:
            self.timer.stop()
        
        error_messages = {
            QProcess.FailedToStart: "Failed to start process",
            QProcess.Crashed: "Process crashed",
            QProcess.Timedout: "Process timed out",
            QProcess.WriteError: "Write error",
            QProcess.ReadError: "Read error",
            QProcess.UnknownError: "Unknown error"
        }
        
        error_message = error_messages.get(error, "Unknown error")
        self._handle_error(error_message)
    
    def _handle_error(self, error_message: str) -> None:
        """Handle execution error"""
        self.status = ToolStatus.FAILED
        
        result = ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.FAILED,
            stdout="".join(self._stdout_buffer),
            stderr="".join(self._stderr_buffer),
            exit_code=-1,
            started_at=self.started_at or time.time(),
            finished_at=time.time(),
            error_message=error_message
        )
        
        self._emit_result(result)
        self.signals.error.emit(self.tool_id, error_message)
    
    def _emit_result(self, result: ToolResult) -> None:
        """Emit result via signal and callback"""
        self.signals.finished.emit(self.tool_id, result)
        
        if self._result_callback:
            self._result_callback(result)


class PingTool(BaseTool):
    """
    Ping tool implementation.
    
    Usage:
        tool = PingTool()
        tool.execute(callback=my_callback, target="192.168.1.10", count=4)
    """
    
    def __init__(self, timeout: int = 30, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("ping", timeout, signals)
    
    def build_command(self, target: str, count: int = 4, **kwargs) -> List[str]:
        """
        Build ping command.
        
        Args:
            target: Target IP or hostname
            count: Number of pings
            
        Returns:
            Command: ["ping", "-n", "4", "192.168.1.10"]
        """
        return ["ping", "-n", str(count), target]


class NmapPingSweepTool(BaseTool):
    """
    Nmap ping sweep tool (-sn).
    
    Usage:
        tool = NmapPingSweepTool()
        tool.execute(callback=my_callback, target="192.168.1.0/24")
    """
    
    def __init__(self, timeout: int = 60, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_ping_sweep", timeout, signals)
    
    def build_command(self, target: str, **kwargs) -> List[str]:
        """
        Build nmap ping sweep command.
        
        Args:
            target: Target IP/CIDR (192.168.1.0/24)
            
        Returns:
            Command: ["nmap", "-sn", "192.168.1.0/24"]
        """
        return ["nmap", "-sn", target]


class NmapPortScanTool(BaseTool):
    """
    Nmap port scan tool (-sS/-sT).
    
    Usage:
        tool = NmapPortScanTool()
        tool.execute(callback=my_callback, target="192.168.1.10", ports="1-1000")
    """
    
    def __init__(self, timeout: int = 120, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_port_scan", timeout, signals)
    
    def build_command(
        self,
        target: str,
        ports: str = "1-1000",
        scan_type: str = "sT",
        **kwargs
    ) -> List[str]:
        """
        Build nmap port scan command.
        
        Args:
            target: Target IP
            ports: Port range (1-1000, 80,443, etc.)
            scan_type: Scan type (sT, sS, sU)
            
        Returns:
            Command: ["nmap", "-sT", "-p", "1-1000", "192.168.1.10"]
        """
        return ["nmap", f"-{scan_type}", "-p", ports, target]
