"""Nmap Port Scan Tool (-sS/-sT/-sU)"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


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
