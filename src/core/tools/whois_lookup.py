"""WHOIS Lookup Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class WhoisLookupTool(BaseTool):
    """Domain/IP WHOIS lookup."""

    def __init__(self, timeout: int = 60, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("whois_lookup", timeout, signals)

    def build_command(self, target: str, **kwargs) -> List[str]:
        safe_target = self.validate_target(target)
        return ["whois", safe_target]
