"""SQLMap Scan Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class SqlmapScanTool(BaseTool):
    """SQLMap command builder."""

    def __init__(self, timeout: int = 900, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("sqlmap_scan", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        level = int(kwargs.get("level", 1) or 1)
        risk = int(kwargs.get("risk", 1) or 1)
        threads = int(kwargs.get("threads", 1) or 1)
        estimate = int(240 + level * 90 + risk * 60 - (threads - 1) * 20)
        return max(120, min(7200, estimate))

    def build_command(
        self,
        url: str,
        level: int = 1,
        risk: int = 1,
        batch: bool = True,
        forms: bool = False,
        dbs: bool = False,
        threads: int = 1,
        **kwargs,
    ) -> List[str]:
        safe_url = self.validate_target(url, "url")
        if not (safe_url.startswith("http://") or safe_url.startswith("https://")):
            raise ValueError(f"[{self.tool_id}] url http:// veya https:// ile baslamali: {safe_url!r}")

        safe_level = self.validate_range(level, 1, 5, "level")
        safe_risk = self.validate_range(risk, 1, 3, "risk")
        safe_threads = self.validate_range(threads, 1, 10, "threads")

        cmd: List[str] = ["sqlmap", "-u", safe_url]

        if batch:
            cmd.append("--batch")

        if forms:
            cmd.append("--forms")

        if safe_level != 1:
            cmd.extend(["--level", str(safe_level)])

        if safe_risk != 1:
            cmd.extend(["--risk", str(safe_risk)])

        if dbs:
            cmd.append("--dbs")

        if safe_threads > 1:
            cmd.extend(["--threads", str(safe_threads)])

        return cmd
