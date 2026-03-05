"""SSL/TLS Certificate and Cipher Analysis Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class SslScanTool(BaseTool):
    """
    SSL/TLS certificate and cipher analysis.
    Uses OpenSSL s_client for SSL/TLS handshake and certificate inspection.
    """

    def __init__(self, timeout: int = 60, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("ssl_scan", timeout, signals)

    def build_command(
        self,
        target: str,
        port: int = 443,
        servername: Optional[str] = None,
        tls_version: Optional[str] = None,
        starttls: Optional[str] = None,
        **kwargs
    ) -> List[str]:
        """
        Build OpenSSL s_client command for SSL/TLS analysis.

        Args:
            target: Target hostname or IP
            port: SSL/TLS port (default: 443)

        Returns:
            Command: ["openssl", "s_client", "-connect", "example.com:443", "-showcerts"]
        """
        safe_target = self.validate_target(target)
        safe_port = self.validate_port(port)

        cmd: List[str] = [
            "openssl",
            "s_client",
            "-connect",
            f"{safe_target}:{safe_port}",
            "-showcerts",
        ]

        if servername:
            cmd.extend(["-servername", self.validate_target(servername, "servername")])

        if tls_version:
            tls_value = self.validate_enum(tls_version, {"1.2", "1.3"}, "tls_version")
            cmd.append("-tls1_2" if tls_value == "1.2" else "-tls1_3")

        if starttls:
            starttls_value = self.validate_enum(
                str(starttls).lower(),
                {"smtp", "imap", "pop3", "ftp", "xmpp", "postgres", "mysql"},
                "starttls",
            )
            cmd.extend(["-starttls", starttls_value])

        return cmd
