"""Nmap Ping Sweep Tool (-sn)"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


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
