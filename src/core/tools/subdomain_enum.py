"""Subdomain Enumeration Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class SubdomainEnumTool(BaseTool):
    """
    Subdomain enumeration using DNS queries.
    Uses nslookup to test common subdomain prefixes.
    """

    def __init__(self, timeout: int = 120, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("subdomain_enum", timeout, signals)

    def build_command(
        self,
        domain: str,
        wordlist: str = "subdomains.txt",
        **kwargs
    ) -> List[str]:
        """
        Build subdomain enumeration command (cross-platform).

        Args:
            domain: Target domain (e.g., example.com)
            wordlist: Path to subdomain wordlist (default: subdomains.txt)

        Returns:
            Platform-uyumlu shell komutu
        """
        safe_domain = self.validate_target(domain, "domain")
        safe_wordlist = self.validate_target(wordlist, "wordlist")

        bash_script = (
            "DOMAIN=\"$1\"; "
            "WORDLIST=\"$2\"; "
            "COMMON='www mail ftp admin api blog shop dev test staging'; "
            "if [ -f \"$WORDLIST\" ]; then SUBS=$(cat \"$WORDLIST\"); else SUBS=\"$COMMON\"; fi; "
            "for SUB in $SUBS; do "
            "  FQDN=\"$SUB.$DOMAIN\"; "
            "  RESULT=$(nslookup \"$FQDN\" 2>&1); "
            "  if echo \"$RESULT\" | grep -qE '[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+'; then "
            "    echo \"FOUND: $FQDN\"; "
            "  fi; "
            "done"
        )
        return ["bash", "-c", bash_script, "--", safe_domain, safe_wordlist]
