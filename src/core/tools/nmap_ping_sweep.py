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

    def estimate_timeout(self, **kwargs) -> int:
        target = str(kwargs.get("target", "")).strip()
        hosts = 256
        if "/" in target:
            try:
                prefix = int(target.rsplit("/", 1)[1])
                prefix = max(0, min(32, prefix))
                hosts = max(1, 2 ** (32 - prefix))
            except Exception:
                hosts = 256

        estimate = int(20 + (hosts / 64.0) * 10)
        return max(20, min(1200, estimate))

    def build_command(
        self,
        target: str,
        timing: Optional[int] = None,
        exclude: Optional[str] = None,
        no_dns: bool = False,
        verbose: bool = False,
        **kwargs,
    ) -> List[str]:
        """
        Build nmap ping sweep command.

        Args:
            target: Target IP/CIDR (192.168.1.0/24)

        Returns:
            Command: ["nmap", "-sn", "192.168.1.0/24"]
        """
        safe_target = self.validate_target(target)
        cmd: List[str] = ["nmap", "-sn"]

        if timing is not None:
            safe_timing = self.validate_range(timing, 0, 5, "timing")
            cmd.append(f"-T{safe_timing}")

        if exclude:
            cmd.extend(["--exclude", self.validate_target(exclude, "exclude")])

        if no_dns:
            cmd.append("-n")

        if verbose:
            cmd.append("-v")

        cmd.append(safe_target)
        return cmd
