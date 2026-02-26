"""Tool Execution Base Classes

Sprint 1 Week 2: Tool execution with QProcess integration
Async tool execution, output capture, timeout handling
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import time

from PyQt6.QtCore import QProcess, QTimer, pyqtSignal, QObject

from src.core.platform_utils import (
    get_ping_count_flag,
    build_echo_pipe_command,
    get_shell,
    get_shell_exec_flag,
    is_windows,
)


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

    def estimate_timeout(self, **kwargs) -> int:
        """
        Tool özel timeout tahmini (override edilebilir).
        Varsayılan: statik self.timeout.
        """
        return int(self.timeout)

    def _compute_effective_timeout(self, kwargs: Dict[str, Any], timeout_override: Optional[int] = None) -> int:
        """Final timeout değerini hesapla (override > estimate > default)."""
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
            Windows: ["ping", "-n", "4", "192.168.1.10"]
            Linux:   ["ping", "-c", "4", "192.168.1.10"]
        """
        return ["ping", get_ping_count_flag(), str(count), target]


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

    @staticmethod
    def _estimate_port_count(ports: str) -> int:
        if not ports:
            return 1000

        total = 0
        for part in str(ports).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    total += max(0, int(end) - int(start) + 1)
                except Exception:
                    total += 1
            else:
                total += 1

        return max(1, min(total, 65535))

    def estimate_timeout(self, **kwargs) -> int:
        ports = kwargs.get("ports", "1-1000")
        scan_type = str(kwargs.get("scan_type", "sT"))

        port_count = self._estimate_port_count(ports)
        factor = {"sT": 1.0, "sS": 0.8, "sU": 1.6}.get(scan_type, 1.1)
        estimate = int((20 + port_count * 0.12) * factor)

        return max(20, min(900, estimate))
    
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


class NmapServiceDetectionTool(BaseTool):
    """
    Nmap service detection tool (-sV).
    
    Detects service versions on open ports.
    Can be combined with port scan or run independently.
    
    Usage:
        tool = NmapServiceDetectionTool()
        tool.execute(callback=my_callback, target="192.168.1.10", ports="80,443")
    """
    
    def __init__(self, timeout: int = 180, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_service_detection", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        ports = kwargs.get("ports")
        intensity = int(kwargs.get("intensity", 5))
        port_count = NmapPortScanTool._estimate_port_count(ports) if ports else 1000

        estimate = int(30 + port_count * 0.18 + intensity * 8)
        return max(30, min(1200, estimate))
    
    def build_command(
        self,
        target: str,
        ports: Optional[str] = None,
        intensity: int = 5,
        **kwargs
    ) -> List[str]:
        """
        Build nmap service detection command.
        
        Args:
            target: Target IP
            ports: Optional port range (if not specified, scans common ports)
            intensity: Version detection intensity 0-9 (default: 5)
            
        Returns:
            Command: ["nmap", "-sV", "--version-intensity", "5", "-p", "80,443", "192.168.1.10"]
        """
        cmd = ["nmap", "-sV", "--version-intensity", str(intensity)]
        
        if ports:
            cmd.extend(["-p", ports])
        
        cmd.append(target)
        return cmd


class NmapVulnScanTool(BaseTool):
    """
    Nmap vulnerability scan tool (--script vuln).
    
    Uses NSE (Nmap Scripting Engine) vulnerability scripts.
    Comprehensive scan, can take significant time.
    
    Usage:
        tool = NmapVulnScanTool()
        tool.execute(callback=my_callback, target="192.168.1.10", ports="80,443")
    """
    
    def __init__(self, timeout: int = 300, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_vuln_scan", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        ports = kwargs.get("ports")
        scripts = str(kwargs.get("scripts", "vuln"))
        port_count = NmapPortScanTool._estimate_port_count(ports) if ports else 1000

        script_factor = 1.0 if scripts == "vuln" else 1.3
        estimate = int((60 + port_count * 0.25) * script_factor)
        return max(60, min(1800, estimate))
    
    def build_command(
        self,
        target: str,
        ports: Optional[str] = None,
        scripts: str = "vuln",
        **kwargs
    ) -> List[str]:
        """
        Build nmap vulnerability scan command.
        
        Args:
            target: Target IP
            ports: Optional port range (if not specified, scans all open ports)
            scripts: NSE script category (default: "vuln")
            
        Returns:
            Command: ["nmap", "--script", "vuln", "-p", "80,443", "192.168.1.10"]
        """
        cmd = ["nmap", "--script", scripts]
        
        if ports:
            cmd.extend(["-p", ports])
        
        cmd.append(target)
        return cmd


class SslScanTool(BaseTool):
    """
    SSL/TLS certificate and cipher analysis.
    Uses OpenSSL s_client for SSL/TLS handshake and certificate inspection.
    """
    
    def __init__(self, timeout: int = 60, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("ssl_scan", timeout, signals)
    
    def build_command(
        self,
        target: str,
        port: int = 443,
        **kwargs
    ) -> List[str]:
        """
        Build OpenSSL s_client command for SSL/TLS analysis.
        
        Args:
            target: Target hostname or IP
            port: SSL/TLS port (default: 443)
            
        Returns:
            Command: ["openssl", "s_client", "-connect", "example.com:443", "-showcerts"]
        """
        # OpenSSL s_client with certificate details
        # Using echo to automatically close connection
        payload = f"openssl s_client -connect {target}:{port} -showcerts 2>&1"
        return build_echo_pipe_command(payload)


class GobusterDirTool(BaseTool):
    """
    Web directory and file enumeration.
    Uses gobuster dir mode to discover hidden paths.
    """
    
    def __init__(self, timeout: int = 300, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("gobuster_dir", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        extensions = kwargs.get("extensions")
        ext_count = 0
        if extensions:
            ext_count = len([e for e in str(extensions).split(",") if e.strip()])

        estimate = 120 + (ext_count * 20)
        return max(60, min(1800, estimate))
    
    def build_command(
        self,
        url: str,
        wordlist: str = "common.txt",
        extensions: Optional[str] = None,
        **kwargs
    ) -> List[str]:
        """
        Build gobuster dir command.
        
        Args:
            url: Target URL (e.g., http://example.com)
            wordlist: Path to wordlist file (default: common.txt)
            extensions: File extensions to check (e.g., "php,html,txt")
            
        Returns:
            Command: ["gobuster", "dir", "-u", "http://example.com", "-w", "wordlist.txt", "-x", "php,html"]
        """
        cmd = ["gobuster", "dir", "-u", url, "-w", wordlist]
        
        if extensions:
            cmd.extend(["-x", extensions])
        
        # Quiet output for better parsing
        cmd.append("-q")
        
        return cmd


class SubdomainEnumTool(BaseTool):
    """
    Subdomain enumeration using DNS queries.
    Uses nslookup to test common subdomain prefixes.
    """
    
    def __init__(self, timeout: int = 120, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("subdomain_enum", timeout, signals)
    
    def build_command(
        self,
        domain: str,
        wordlist: str = "subdomains.txt",
        **kwargs
    ) -> List[str]:
        """
        Build subdomain enumeration command (cross-platform).
        
        Args:
            domain: Target domain (e.g., example.com)
            wordlist: Path to subdomain wordlist (default: subdomains.txt)
            
        Returns:
            Platform-uyumlu shell komutu
        """
        common_subs = "www mail ftp admin api blog shop dev test staging"

        if is_windows():
            ps_script = (
                f"$domain='{domain}'; $wl='{wordlist}'; "
                f"$common=@({','.join(repr(s) for s in common_subs.split())}); "
                "$subs = if (Test-Path $wl) { Get-Content $wl } else { $common }; "
                "foreach ($s in $subs) { "
                "  $fqdn=\"$s.$domain\"; "
                "  try { $r = nslookup $fqdn 2>&1; "
                "    if ($r -match '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}') "
                "    { Write-Output \"FOUND: $fqdn\" } "
                "  } catch {} "
                "}"
            )
            return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-Command", ps_script]

        # Linux / macOS — bash + nslookup
        bash_script = (
            f'DOMAIN="{domain}"; WORDLIST="{wordlist}"; '
            f'COMMON="{common_subs}"; '
            'if [ -f "$WORDLIST" ]; then SUBS=$(cat "$WORDLIST"); '
            'else SUBS="$COMMON"; fi; '
            'for SUB in $SUBS; do '
            '  FQDN="$SUB.$DOMAIN"; '
            '  RESULT=$(nslookup "$FQDN" 2>&1); '
            '  if echo "$RESULT" | grep -qE "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+"; then '
            '    echo "FOUND: $FQDN"; '
            '  fi; '
            'done'
        )
        return ["bash", "-c", bash_script]


class DnsLookupTool(BaseTool):
    """
    DNS lookup tool using nslookup (Windows compatible).
    
    Queries DNS records (A, AAAA, MX, NS, TXT, etc.)
    
    Usage:
        tool = DnsLookupTool()
        tool.execute(callback=my_callback, domain="example.com", record_type="A")
    """
    
    def __init__(self, timeout: int = 30, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("dns_lookup", timeout, signals)
    
    def build_command(
        self,
        domain: str,
        record_type: str = "A",
        **kwargs
    ) -> List[str]:
        """
        Build nslookup command.
        
        Args:
            domain: Domain name to query
            record_type: DNS record type (A, AAAA, MX, NS, TXT, etc.)
            
        Returns:
            Command: ["nslookup", "-type=A", "example.com"]
        """
        return ["nslookup", f"-type={record_type.upper()}", domain]


class WebAppScanTool(BaseTool):
    """
    Web application scanner for technology fingerprinting.
    Uses curl and PowerShell to detect web technologies.
    """
    
    def __init__(self, timeout: int = 60, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("web_app_scan", timeout, signals)
    
    def build_command(
        self,
        url: str,
        **kwargs
    ) -> List[str]:
        """
        Build curl-based web app scan command (cross-platform).
        
        Args:
            url: Target URL (e.g., http://example.com)
            
        Returns:
            Platform-uyumlu shell komutu (curl tabanli)
        """
        # Technology detection patterns
        tech_patterns = [
            ("WordPress|wp-content|wp-includes", "WordPress"),
            ("Joomla", "Joomla"),
            ("Drupal", "Drupal"),
            ("Laravel", "Laravel"),
            ("React", "React"),
            ("Angular|ng-app", "Angular"),
            ("Vue\\.js|v-app", "Vue.js"),
            ("jQuery", "jQuery"),
        ]

        grep_checks = "; ".join(
            f'echo "$BODY" | grep -qiE "{pat}" && echo "TECH: {name}"'
            for pat, name in tech_patterns
        )

        bash_script = (
            f'URL="{url}"; '
            'HEADERS=$(curl -sI -m 30 "$URL" 2>&1); '
            'echo "$HEADERS" | grep -i "^Server:" | sed "s/^/SERVER: /"; '
            'echo "$HEADERS" | grep -i "^X-Powered-By:" | sed "s/^/POWERED-BY: /"; '
            'echo "$HEADERS" | grep -i "^Content-Type:" | sed "s/^/CONTENT-TYPE: /"; '
            'STATUS=$(echo "$HEADERS" | head -1 | awk \'{print $2}\'); '
            'echo "STATUS: $STATUS"; '
            'BODY=$(curl -sL -m 30 "$URL" 2>&1); '
            f'{grep_checks}'
        )

        return [get_shell(), get_shell_exec_flag(), bash_script]
