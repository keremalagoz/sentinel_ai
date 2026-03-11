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

    def estimate_timeout(self, **kwargs) -> int:
        count = self.validate_range(kwargs.get("count", 4), 1, 100, "count")
        estimated = int(5 + (count * 1.5))
        return max(5, min(300, estimated))

    def build_command(
        self,
        target: str,
        count: int = 4,
        timeout: Optional[int] = None,
        packet_size: Optional[int] = None,
        **kwargs,
    ) -> List[str]:
        """
        Build ping command.

        Args:
            target: Target IP or hostname
            count: Number of pings

        Returns:
            Windows: ["ping", "-n", "4", "192.168.1.10"]
            Linux:   ["ping", "-c", "4", "192.168.1.10"]
        """
        safe_target = self.validate_target(target)
        safe_count = self.validate_range(count, 1, 100, "count")

        cmd: List[str] = ["ping", get_ping_count_flag(), str(safe_count)]

        if timeout is not None:
            safe_timeout = self.validate_range(timeout, 1, 120, "timeout")
            cmd.extend(["-W", str(safe_timeout)])

        if packet_size is not None:
            safe_packet_size = self.validate_range(packet_size, 1, 65500, "packet_size")
            cmd.extend(["-s", str(safe_packet_size)])

        cmd.append(safe_target)
        return cmd
