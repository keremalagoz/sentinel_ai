"""Hydra SSH Brute Force Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class HydraSshTool(BaseTool):
    """Hydra SSH brute force command builder."""

    def __init__(self, timeout: int = 600, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("hydra_ssh", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        threads = int(kwargs.get("threads", 4) or 4)
        estimate = int(300 + (120 / max(1, threads)))
        return max(120, min(3600, estimate))

    def build_command(
        self,
        target: str,
        username: str,
        wordlist: str,
        port: int = 22,
        threads: int = 4,
        verbose: bool = False,
        **kwargs,
    ) -> List[str]:
        safe_target = self.validate_target(target)
        safe_username = self.validate_target(username, "username")
        safe_wordlist = self.validate_target(wordlist, "wordlist")
        safe_port = self.validate_port(port)
        safe_threads = self.validate_range(threads, 1, 128, "threads")

        cmd: List[str] = [
            "hydra",
            "-l",
            safe_username,
            "-P",
            safe_wordlist,
            "-t",
            str(safe_threads),
        ]

        if safe_port != 22:
            cmd.extend(["-s", str(safe_port)])

        if verbose:
            cmd.append("-V")

        cmd.append(f"ssh://{safe_target}")
        return cmd
