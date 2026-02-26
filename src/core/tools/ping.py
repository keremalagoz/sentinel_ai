"""Ping Tool — ICMP echo request"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.platform_utils import get_ping_count_flag


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
