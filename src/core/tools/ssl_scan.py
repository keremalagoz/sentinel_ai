"""SSL/TLS Certificate and Cipher Analysis Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.platform_utils import build_echo_pipe_command


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
        payload = f"openssl s_client -connect {target}:{port} -showcerts 2>&1"
        return build_echo_pipe_command(payload)
