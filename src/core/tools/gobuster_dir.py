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
        wordlist: str = "common.txt",
        extensions: Optional[str] = None,
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
        cmd = ["gobuster", "dir", "-u", url, "-w", wordlist]

        if extensions:
            cmd.extend(["-x", extensions])

        # Quiet output for better parsing
        cmd.append("-q")

        return cmd
