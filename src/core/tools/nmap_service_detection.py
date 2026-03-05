"""Nmap Service Detection Tool (-sV)"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.tools.nmap_port_scan import NmapPortScanTool


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
        intensity = int(kwargs.get("intensity", kwargs.get("version_intensity", 5)))
        port_count = NmapPortScanTool._estimate_port_count(ports) if ports else 1000

        estimate = int(30 + port_count * 0.18 + intensity * 8)
        return max(30, min(1200, estimate))

    def build_command(
        self,
        target: str,
        ports: Optional[str] = None,
        intensity: int = 5,
        version_intensity: Optional[int] = None,
        timing: Optional[int] = None,
        version_mode: str = "default",
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
        safe_target = self.validate_target(target)
        safe_intensity = self.validate_range(
            version_intensity if version_intensity is not None else intensity,
            0,
            9,
            "version_intensity",
        )

        cmd: List[str] = ["nmap", "-sV", "--version-intensity", str(safe_intensity)]

        safe_mode = self.validate_enum(version_mode, {"default", "light", "all"}, "version_mode")
        if safe_mode == "light":
            cmd.append("--version-light")
        elif safe_mode == "all":
            cmd.append("--version-all")

        if timing is not None:
            safe_timing = self.validate_range(timing, 0, 5, "timing")
            cmd.append(f"-T{safe_timing}")

        if ports:
            safe_ports = self.validate_ports(ports)
            cmd.extend(["-p", safe_ports])

        cmd.append(safe_target)
        return cmd
