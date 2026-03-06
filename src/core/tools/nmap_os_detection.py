"""Nmap OS Detection Tool (-O)"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.tools.nmap_port_scan import NmapPortScanTool


class NmapOsDetectionTool(BaseTool):
    """Nmap OS detection tool."""

    def __init__(self, timeout: int = 240, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("nmap_os_detection", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        ports = kwargs.get("ports")
        port_count = NmapPortScanTool._estimate_port_count(ports) if ports else 1000
        estimate = int(45 + port_count * 0.18)
        return max(45, min(1800, estimate))

    def build_command(
        self,
        target: str,
        ports: Optional[str] = None,
        timing: Optional[int] = None,
        osscan_guess: bool = False,
        service_detection: bool = False,
        verbose: bool = False,
        top_ports: Optional[int] = None,
        no_ping: bool = False,
        **kwargs,
    ) -> List[str]:
        safe_target = self.validate_target(target)
        cmd: List[str] = ["nmap", "-O"]

        if service_detection:
            cmd.append("-sV")

        if osscan_guess:
            cmd.append("--osscan-guess")

        if top_ports is not None:
            safe_top_ports = self.validate_range(top_ports, 1, 65535, "top_ports")
            cmd.extend(["--top-ports", str(safe_top_ports)])
        elif ports:
            safe_ports = self.validate_ports(ports)
            cmd.extend(["-p", safe_ports])

        if timing is not None:
            safe_timing = self.validate_range(timing, 0, 5, "timing")
            cmd.append(f"-T{safe_timing}")

        if no_ping:
            cmd.append("-Pn")

        if verbose:
            cmd.append("-v")

        cmd.append(safe_target)
        return cmd
