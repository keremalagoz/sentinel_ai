"""Sentinel Coordinator - UI + ToolManager Bridge

Action Planner v2.1 - UI Integration
Connects ToolManager with TerminalView for complete workflow
"""

from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.tool_integration import ToolManager, IntegratedToolResult
from src.core.tool_base import (
    PingTool, NmapPingSweepTool, NmapPortScanTool,
    NmapServiceDetectionTool, NmapVulnScanTool, DnsLookupTool,
    SslScanTool, GobusterDirTool, SubdomainEnumTool, WebAppScanTool,
    NmapOsDetectionTool, WhoisLookupTool, HydraSshTool, HydraHttpTool, SqlmapScanTool,
)
from src.core.parser_framework import (
    PingParser, NmapPingSweepParser, NmapPortScanParser,
    NmapServiceDetectionParser, NmapVulnScanParser, DnsLookupParser,
    SslScanParser, GobusterDirParser, SubdomainEnumParser, WebAppScanParser,
    NmapOsDetectionParser, WhoisLookupParser, HydraSshParser, HydraHttpParser, SqlmapScanParser,
)
from src.core.sqlite_backend import SQLiteBackend
from src.ai.tool_registry import validate_execution_registry


DEFAULT_TOOL_CATALOG = [
    (PingTool, PingParser, 10, 2),
    (NmapPingSweepTool, NmapPingSweepParser, 30, 1),
    (NmapPortScanTool, NmapPortScanParser, 120, 1),
    (NmapServiceDetectionTool, NmapServiceDetectionParser, 180, 1),
    (NmapVulnScanTool, NmapVulnScanParser, 300, 1),
    (DnsLookupTool, DnsLookupParser, 30, 2),
    (SslScanTool, SslScanParser, 60, 2),
    (GobusterDirTool, GobusterDirParser, 300, 1),
    (SubdomainEnumTool, SubdomainEnumParser, 120, 1),
    (WebAppScanTool, WebAppScanParser, 60, 2),
    (NmapOsDetectionTool, NmapOsDetectionParser, 240, 1),
    (WhoisLookupTool, WhoisLookupParser, 60, 2),
    (HydraSshTool, HydraSshParser, 600, 1),
    (HydraHttpTool, HydraHttpParser, 600, 1),
    (SqlmapScanTool, SqlmapScanParser, 900, 1),
]


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
    tool_started = pyqtSignal(str, str)  # tool_id, execution_id
    tool_output = pyqtSignal(str, str)  # tool_id, output_chunk
    tool_completed = pyqtSignal(str, object)  # tool_id, IntegratedToolResult
    tool_error = pyqtSignal(str, str)  # tool_id, error_message
    
    def __init__(self, db_path: str = "data/databases/sentinel_state.db", parent: Optional[QObject] = None):
        """
        Initialize coordinator.
        
        Args:
            db_path: SQLite database path (default: "data/databases/sentinel_state.db")
            parent: Optional Qt parent
        """
        super().__init__(parent)
        
        # Backend
        self.backend = SQLiteBackend(db_path)
        
        # Tool Manager
        self.manager = ToolManager(
            backend=self.backend
        )
        
        # Register tools
        self._register_default_tools()
        
        # Connect ToolManager signals to coordinator signals
        self.manager.signals.started.connect(self._on_tool_started)
        self.manager.signals.completed.connect(self._on_tool_completed)
        self.manager.signals.error.connect(self._on_tool_error)
    
    def _register_default_tools(self):
        """Register Action Planner v2.1 tools"""
        for tool_cls, parser_cls, timeout, tool_limit in DEFAULT_TOOL_CATALOG:
            self.manager.register_tool(
                tool=tool_cls(timeout=timeout),
                parser=parser_cls(),
                max_concurrent=tool_limit,
            )

        # Drift guard: AI execution mapping <-> registered tools
        is_valid, errors = validate_execution_registry(set(self.manager.registered_tools))
        if not is_valid:
            raise RuntimeError("Registry consistency check failed: " + "; ".join(errors))
    
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
    
    def execute_service_detection(self, target: str, ports: Optional[str] = None, intensity: int = 5) -> bool:
        """
        Execute nmap service detection.
        
        Args:
            target: IP address
            ports: Optional port range (if not specified, scans common ports)
            intensity: Version detection intensity 0-9 (default: 5)
            
        Returns:
            True if started successfully
        """
        kwargs = {
            "target": target,
            "intensity": intensity
        }
        
        if ports:
            kwargs["ports"] = ports
        
        return self.manager.execute_tool(
            "nmap_service_detection",
            callback=None,
            **kwargs
        )
    
    def execute_vuln_scan(self, target: str, ports: Optional[str] = None, scripts: str = "vuln") -> bool:
        """
        Execute nmap vulnerability scan.
        
        Args:
            target: IP address
            ports: Optional port range (if not specified, scans all discovered ports)
            scripts: NSE script category (default: "vuln")
            
        Returns:
            True if started successfully
        """
        kwargs = {
            "target": target,
            "scripts": scripts
        }
        
        if ports:
            kwargs["ports"] = ports
        
        return self.manager.execute_tool(
            "nmap_vuln_scan",
            callback=None,
            **kwargs
        )
    
    def execute_dns_lookup(self, domain: str, record_type: str = "A") -> bool:
        """
        Execute DNS lookup.
        
        Args:
            domain: Domain name to query
            record_type: DNS record type (A, AAAA, MX, NS, TXT, etc.)
            
        Returns:
            True if started successfully
        """
        return self.manager.execute_tool(
            "dns_lookup",
            callback=None,
            domain=domain,
            record_type=record_type
        )
    
    def execute_ssl_scan(self, target: str, port: int = 443) -> bool:
        """
        Execute SSL/TLS scan.
        
        Args:
            target: Target hostname or IP
            port: SSL/TLS port (default: 443 for HTTPS)
            
        Returns:
            True if started successfully
        """
        return self.manager.execute_tool(
            "ssl_scan",
            callback=None,
            target=target,
            port=port
        )
    
    def execute_web_dir_enum(self, url: str, wordlist: str = "common.txt", extensions: Optional[str] = None) -> bool:
        """
        Execute web directory enumeration.
        
        Args:
            url: Target URL (e.g., http://example.com)
            wordlist: Path to wordlist file
            extensions: Optional file extensions (e.g., "php,html,txt")
            
        Returns:
            True if started successfully
        """
        kwargs = {
            "url": url,
            "wordlist": wordlist
        }
        
        if extensions:
            kwargs["extensions"] = extensions
        
        return self.manager.execute_tool(
            "gobuster_dir",
            callback=None,
            **kwargs
        )
    
    def execute_subdomain_enum(self, domain: str, wordlist: str = "subdomains.txt") -> bool:
        """
        Execute subdomain enumeration.
        
        Args:
            domain: Target domain (e.g., example.com)
            wordlist: Path to subdomain wordlist
            
        Returns:
            True if started successfully
        """
        return self.manager.execute_tool(
            "subdomain_enum",
            callback=None,
            domain=domain,
            wordlist=wordlist
        )
    
    def execute_web_app_scan(self, url: str) -> bool:
        """
        Execute web application scanner.
        
        Args:
            url: Target URL (e.g., http://example.com)
            
        Returns:
            True if started successfully
        """
        return self.manager.execute_tool(
            "web_app_scan",
            callback=None,
            url=url
        )

    def execute_os_detection(self, target: str, ports: Optional[str] = None, timing: Optional[int] = None) -> bool:
        kwargs = {"target": target}
        if ports:
            kwargs["ports"] = ports
        if timing is not None:
            kwargs["timing"] = timing
        return self.manager.execute_tool("nmap_os_detection", callback=None, **kwargs)

    def execute_whois_lookup(self, target: str) -> bool:
        return self.manager.execute_tool("whois_lookup", callback=None, target=target)

    def execute_hydra_ssh(
        self,
        target: str,
        username: str,
        wordlist: str,
        port: int = 22,
        threads: int = 4,
    ) -> bool:
        return self.manager.execute_tool(
            "hydra_ssh",
            callback=None,
            target=target,
            username=username,
            wordlist=wordlist,
            port=port,
            threads=threads,
        )

    def execute_hydra_http(
        self,
        target: str,
        username: str,
        wordlist: str,
        form_path: str,
        form_params: str,
        fail_string: str,
        port: int = 80,
        threads: int = 4,
        method: str = "http-form-post",
    ) -> bool:
        return self.manager.execute_tool(
            "hydra_http",
            callback=None,
            target=target,
            username=username,
            wordlist=wordlist,
            form_path=form_path,
            form_params=form_params,
            fail_string=fail_string,
            port=port,
            threads=threads,
            method=method,
        )

    def execute_sqlmap_scan(
        self,
        url: str,
        level: int = 1,
        risk: int = 1,
        batch: bool = True,
        forms: bool = False,
        dbs: bool = False,
        threads: int = 1,
    ) -> bool:
        return self.manager.execute_tool(
            "sqlmap_scan",
            callback=None,
            url=url,
            level=level,
            risk=risk,
            batch=batch,
            forms=forms,
            dbs=dbs,
            threads=threads,
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

    def get_runtime_metrics(self) -> dict:
        """ToolManager runtime performans metriklerini getir."""
        return self.manager.get_runtime_metrics()
    
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
