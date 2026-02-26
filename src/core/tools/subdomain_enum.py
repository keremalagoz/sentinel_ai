"""Subdomain Enumeration Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.platform_utils import is_windows


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
        common_subs = "www mail ftp admin api blog shop dev test staging"

        if is_windows():
            ps_script = (
                f"$domain='{domain}'; $wl='{wordlist}'; "
                f"$common=@({','.join(repr(s) for s in common_subs.split())}); "
                "$subs = if (Test-Path $wl) { Get-Content $wl } else { $common }; "
                "foreach ($s in $subs) { "
                "  $fqdn=\"$s.$domain\"; "
                "  try { $r = nslookup $fqdn 2>&1; "
                "    if ($r -match '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}') "
                "    { Write-Output \"FOUND: $fqdn\" } "
                "  } catch {} "
                "}"
            )
            return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-Command", ps_script]

        # Linux / macOS — bash + nslookup
        bash_script = (
            f'DOMAIN="{domain}"; WORDLIST="{wordlist}"; '
            f'COMMON="{common_subs}"; '
            'if [ -f "$WORDLIST" ]; then SUBS=$(cat "$WORDLIST"); '
            'else SUBS="$COMMON"; fi; '
            'for SUB in $SUBS; do '
            '  FQDN="$SUB.$DOMAIN"; '
            '  RESULT=$(nslookup "$FQDN" 2>&1); '
            '  if echo "$RESULT" | grep -qE "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+"; then '
            '    echo "FOUND: $FQDN"; '
            '  fi; '
            'done'
        )
        return ["bash", "-c", bash_script]
