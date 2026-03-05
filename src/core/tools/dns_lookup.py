"""DNS Lookup Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


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
        dns_server: Optional[str] = None,
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
        safe_domain = self.validate_target(domain, "domain")
        safe_record_type = self.validate_enum(
            str(record_type).upper(),
            {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "SRV"},
            "record_type",
        )

        cmd: List[str] = ["nslookup", f"-type={safe_record_type}", safe_domain]
        if dns_server:
            cmd.append(self.validate_target(dns_server, "dns_server"))

        return cmd
