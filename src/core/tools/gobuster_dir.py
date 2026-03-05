"""Gobuster Directory Enumeration Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class GobusterDirTool(BaseTool):
    """
    Web directory and file enumeration.
    Uses gobuster dir mode to discover hidden paths.
    """

    def __init__(self, timeout: int = 300, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("gobuster_dir", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        extensions = kwargs.get("extensions")
        ext_count = 0
        if extensions:
            ext_count = len([e for e in str(extensions).split(",") if e.strip()])

        estimate = 120 + (ext_count * 20)
        return max(60, min(1800, estimate))

    def build_command(
        self,
        url: str,
        wordlist: str = "/usr/share/wordlists/dirb/common.txt",
        extensions: Optional[str] = None,
        threads: Optional[int] = None,
        status_codes: Optional[str] = None,
        no_tls_validation: bool = False,
        follow_redirect: bool = False,
        **kwargs
    ) -> List[str]:
        """
        Build gobuster dir command.

        Args:
            url: Target URL (e.g., http://example.com)
            wordlist: Path to wordlist file (default: common.txt)
            extensions: File extensions to check (e.g., "php,html,txt")

        Returns:
            Command: ["gobuster", "dir", "-u", "http://example.com", "-w", "wordlist.txt", "-x", "php,html"]
        """
        safe_url = self.validate_target(url, "url")
        if not (safe_url.startswith("http://") or safe_url.startswith("https://")):
            raise ValueError(f"[{self.tool_id}] url http:// veya https:// ile baslamali: {safe_url!r}")

        safe_wordlist = self.validate_target(wordlist, "wordlist")

        cmd: List[str] = ["gobuster", "dir", "-u", safe_url, "-w", safe_wordlist]

        if extensions:
            cmd.extend(["-x", extensions])

        if threads is not None:
            safe_threads = self.validate_range(threads, 1, 256, "threads")
            cmd.extend(["-t", str(safe_threads)])

        if status_codes:
            cmd.extend(["-s", self.validate_target(status_codes, "status_codes")])

        if no_tls_validation:
            cmd.append("-k")

        if follow_redirect:
            cmd.append("-r")

        # Quiet output for better parsing
        cmd.append("-q")

        return cmd
