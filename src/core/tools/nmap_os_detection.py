"""Nmap OS Detection Tool (-O)."""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.tools.nmap_port_scan import NmapPortScanTool


class NmapOsDetectionTool(BaseTool):
    """Nmap operating system detection tool."""

    def __init__(self, timeout: int = 180, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_os_detection", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        ports = kwargs.get("ports")
        port_count = NmapPortScanTool._estimate_port_count(NmapPortScanTool._normalize_ports(ports)) if ports else 1000
        estimate = int(45 + port_count * 0.15)
        return max(45, min(1200, estimate))

    def build_command(
        self,
        target: str,
        ports: Optional[str] = None,
        aggressive: bool = False,
        **kwargs
    ) -> List[str]:
        normalized_target = NmapPortScanTool._normalize_target(target)
        cmd = ["nmap", "-O", "-sV"]

        if aggressive:
            cmd.append("--osscan-guess")

        if ports:
            cmd.extend(["-p", NmapPortScanTool._normalize_ports(ports)])

        cmd.append(normalized_target)
        return cmd