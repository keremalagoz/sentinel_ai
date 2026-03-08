"""WHOIS Lookup Tool."""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.validators import InputValidator


class WhoisLookupTool(BaseTool):
    """WHOIS query tool for domain registration data."""

    def __init__(self, timeout: int = 45, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("whois_lookup", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        return 45

    def build_command(
        self,
        domain: str,
        **kwargs
    ) -> List[str]:
        raw_domain = str(domain or "").strip().lower()
        normalized_domain = InputValidator.sanitize(raw_domain)
        if normalized_domain != raw_domain:
            raise ValueError("Invalid domain")
        if not InputValidator.validate_hostname(normalized_domain):
            raise ValueError("Invalid domain")
        return ["whois", normalized_domain]