"""Nmap Vulnerability Scan Tool (--script vuln)"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.tools.nmap_port_scan import NmapPortScanTool


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
