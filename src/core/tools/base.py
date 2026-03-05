"""Tool Execution Base Classes

Sprint 1 Week 2: Tool execution with QProcess integration
Async tool execution, output capture, timeout handling

Re-structured in Sprint 3.2 Track D1: Moved from monolithic tool_base.py
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Iterable
from dataclasses import dataclass
from enum import Enum
import re
import time

from PyQt6.QtCore import QProcess, QTimer, pyqtSignal, QObject


_SHELL_METACHAR_RE = re.compile(r'(?:;|\|\||&&|\||`|\$\(|\$\{|\)|\{|\}|!|<|>|\n|\r|\x00)')


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
    started = pyqtSignal(str)  # tool_id
    stdout_ready = pyqtSignal(str, str)  # tool_id, data
    stderr_ready = pyqtSignal(str, str)  # tool_id, data
    finished = pyqtSignal(str, object)  # tool_id, ToolResult
    error = pyqtSignal(str, str)  # tool_id, error_message


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
        self._effective_timeout = timeout

        self._stdout_buffer: List[str] = []
        self._stderr_buffer: List[str] = []
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

    def estimate_timeout(self, **kwargs) -> int:
        """
        Tool ozel timeout tahmini (override edilebilir).
        Varsayilan: statik self.timeout.
        """
        return int(self.timeout)

    def _compute_effective_timeout(self, kwargs: Dict[str, Any], timeout_override: Optional[int] = None) -> int:
        """Final timeout degerini hesapla (override > estimate > default)."""
        if timeout_override is not None:
            try:
                return max(5, min(3600, int(timeout_override)))
            except Exception:
                pass

        estimated = self.estimate_timeout(**kwargs)
        return max(5, min(3600, int(estimated)))

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

        local_kwargs = dict(kwargs)
        timeout_override = local_kwargs.pop("_timeout", None)
        if timeout_override is None:
            timeout_override = local_kwargs.pop("timeout_override", None)

        self._effective_timeout = self._compute_effective_timeout(local_kwargs, timeout_override)

        # Build command
        command = self.build_command(**local_kwargs)
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
        self.timer.start(self._effective_timeout * 1000)

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
            error_message=f"Execution timeout after {self._effective_timeout} seconds"
        )

        self._emit_result(result)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        """Handle process error"""
        if self.timer:
            self.timer.stop()

        error_messages = {
            QProcess.ProcessError.FailedToStart: "Failed to start process",
            QProcess.ProcessError.Crashed: "Process crashed",
            QProcess.ProcessError.Timedout: "Process timed out",
            QProcess.ProcessError.WriteError: "Write error",
            QProcess.ProcessError.ReadError: "Read error",
            QProcess.ProcessError.UnknownError: "Unknown error"
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

    def validate_target(self, target: str, field_name: str = "target") -> str:
        """Validate target-like string input and reject shell metacharacters."""
        if not isinstance(target, str) or not target.strip():
            raise ValueError(f"[{self.tool_id}] {field_name} bos olamaz")

        normalized = target.strip()
        if _SHELL_METACHAR_RE.search(normalized):
            raise ValueError(
                f"[{self.tool_id}] {field_name} icinde tehlikeli karakter bulundu: {normalized!r}"
            )

        return normalized

    def validate_port(self, port: Any, min_val: int = 1, max_val: int = 65535, name: str = "port") -> int:
        """Validate a single port value."""
        try:
            parsed = int(port)
        except Exception as exc:
            raise ValueError(f"[{self.tool_id}] {name} sayisal olmali: {port!r}") from exc

        if not (min_val <= parsed <= max_val):
            raise ValueError(f"[{self.tool_id}] {name} {min_val}-{max_val} araliginda olmali: {parsed}")

        return parsed

    def validate_range(self, value: Any, min_val: int, max_val: int, name: str) -> int:
        """Validate an integer range value."""
        try:
            parsed = int(value)
        except Exception as exc:
            raise ValueError(f"[{self.tool_id}] {name} sayisal olmali: {value!r}") from exc

        if not (min_val <= parsed <= max_val):
            raise ValueError(f"[{self.tool_id}] {name} {min_val}-{max_val} araliginda olmali: {parsed}")

        return parsed

    def validate_enum(self, value: str, allowed: Iterable[str], name: str) -> str:
        """Validate a string against allowed values."""
        allowed_set = {str(item) for item in allowed}
        normalized = str(value)
        if normalized not in allowed_set:
            allowed_text = ", ".join(sorted(allowed_set))
            raise ValueError(f"[{self.tool_id}] {name} gecersiz: {normalized!r}. Izin verilen: {allowed_text}")
        return normalized

    # ------------------------------------------------------------------
    # Relaxed validators for non-target parameters
    # ------------------------------------------------------------------

    _STRICT_SHELL_RE = re.compile(r'[`\x00\n\r]|\$\(|\$\{')

    def validate_string(self, value: str, field_name: str, max_length: int = 512) -> str:
        """Validate a free-form string parameter.

        Less restrictive than validate_target: allows characters like !, =, &,
        {, } which appear in legitimate tool arguments (hydra form_params,
        nmap script_args, fail strings, etc.).

        Blocks only the most dangerous shell expansion sequences:
        backticks, null bytes, newlines, $() and ${}.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"[{self.tool_id}] {field_name} bos olamaz")

        normalized = value.strip()
        if len(normalized) > max_length:
            raise ValueError(
                f"[{self.tool_id}] {field_name} cok uzun (max {max_length})"
            )
        if self._STRICT_SHELL_RE.search(normalized):
            raise ValueError(
                f"[{self.tool_id}] {field_name} icinde tehlikeli karakter bulundu: {normalized!r}"
            )
        return normalized

    _PORT_RANGE_RE = re.compile(r'^(\d{1,5}(-\d{1,5})?)(,\s*\d{1,5}(-\d{1,5})?)*$')

    def validate_ports(self, ports: str, field_name: str = "ports") -> str:
        """Validate a port range string (e.g. '1-1000', '80,443', '22')."""
        if not isinstance(ports, str) or not ports.strip():
            raise ValueError(f"[{self.tool_id}] {field_name} bos olamaz")

        normalized = ports.strip().replace(" ", "")
        if not self._PORT_RANGE_RE.match(normalized):
            raise ValueError(
                f"[{self.tool_id}] {field_name} gecersiz format: {normalized!r}. "
                "Beklenen: '80', '1-1000', '80,443'"
            )

        for part in normalized.split(","):
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start_val, end_val = int(start_s), int(end_s)
                if not (1 <= start_val <= 65535) or not (1 <= end_val <= 65535):
                    raise ValueError(
                        f"[{self.tool_id}] {field_name} port degeri 1-65535 araliginda olmali: {part}"
                    )
                if start_val > end_val:
                    raise ValueError(
                        f"[{self.tool_id}] {field_name} baslangic bitis'ten buyuk olamaz: {part}"
                    )
            else:
                val = int(part)
                if not (1 <= val <= 65535):
                    raise ValueError(
                        f"[{self.tool_id}] {field_name} port degeri 1-65535 araliginda olmali: {part}"
                    )

        return normalized

    _NSE_SCRIPT_RE = re.compile(r'^[a-zA-Z0-9_][a-zA-Z0-9_.\-*?]*$')

    def validate_nse_scripts(self, scripts: str) -> str:
        """Validate comma-separated NSE script names.

        Only allows alphanumeric, underscore, dot, hyphen — the characters
        that can legally appear in NSE script names.
        """
        if not isinstance(scripts, str) or not scripts.strip():
            raise ValueError(f"[{self.tool_id}] scripts bos olamaz")

        items = [s.strip() for s in scripts.split(",") if s.strip()]
        if not items:
            raise ValueError(f"[{self.tool_id}] scripts bos olamaz")

        for name in items:
            if not self._NSE_SCRIPT_RE.match(name):
                raise ValueError(
                    f"[{self.tool_id}] Gecersiz NSE script adi: {name!r}"
                )
        return ",".join(items)
