"""DNS Lookup Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.validators import InputValidator


_ALLOWED_RECORD_TYPES = {"A", "AAAA", "CNAME", "MX", "NS", "PTR", "SOA", "SRV", "TXT"}


class DnsLookupTool(BaseTool):
    """
    DNS lookup tool using nslookup (Windows compatible).

    Queries DNS records (A, AAAA, MX, NS, TXT, etc.)

    Usage:
        tool = DnsLookupTool()
        tool.execute(callback=my_callback, domain="example.com", record_type="A")
    """

    def __init__(self, timeout: int = 30, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("dns_lookup", timeout, signals)

    def build_command(
        self,
        domain: str,
        record_type: str = "A",
        **kwargs
    ) -> List[str]:
        """
        Build nslookup command.

        Args:
            domain: Domain name to query
            record_type: DNS record type (A, AAAA, MX, NS, TXT, etc.)

        Returns:
            Command: ["nslookup", "-type=A", "example.com"]
        """
        raw_domain = str(domain or "").strip().lower()
        normalized_domain = InputValidator.sanitize(raw_domain)
        if normalized_domain != raw_domain:
            raise ValueError("Invalid domain")
        if not InputValidator.validate_hostname(normalized_domain):
            raise ValueError("Invalid domain")

        normalized_record_type = str(record_type or "A").strip().upper()
        if normalized_record_type not in _ALLOWED_RECORD_TYPES:
            raise ValueError("Invalid DNS record type")

        return ["nslookup", f"-type={normalized_record_type}", normalized_domain]
