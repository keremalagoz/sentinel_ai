"""Web Application Scanner Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals
from src.core.platform_utils import get_shell, get_shell_exec_flag


class WebAppScanTool(BaseTool):
    """
    Web application scanner for technology fingerprinting.
    Uses curl and shell to detect web technologies.
    """

    def __init__(self, timeout: int = 60, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("web_app_scan", timeout, signals)

    def build_command(
        self,
        url: str,
        **kwargs
    ) -> List[str]:
        """
        Build curl-based web app scan command (cross-platform).

        Args:
            url: Target URL (e.g., http://example.com)

        Returns:
            Platform-uyumlu shell komutu (curl tabanli)
        """
        safe_url = self.validate_target(url, "url")

        # Technology detection patterns
        tech_patterns = [
            ("WordPress|wp-content|wp-includes", "WordPress"),
            ("Joomla", "Joomla"),
            ("Drupal", "Drupal"),
            ("Laravel", "Laravel"),
            ("React", "React"),
            ("Angular|ng-app", "Angular"),
            ("Vue\\.js|v-app", "Vue.js"),
            ("jQuery", "jQuery"),
        ]

        grep_checks = "; ".join(
            f'echo "$BODY" | grep -qiE "{pat}" && echo "TECH: {name}"'
            for pat, name in tech_patterns
        )

        bash_script = (
            'URL="$1"; '
            'HEADERS=$(curl -sI -m 30 "$URL" 2>&1); '
            'echo "$HEADERS" | grep -i "^Server:" | sed "s/^/SERVER: /"; '
            'echo "$HEADERS" | grep -i "^X-Powered-By:" | sed "s/^/POWERED-BY: /"; '
            'echo "$HEADERS" | grep -i "^Content-Type:" | sed "s/^/CONTENT-TYPE: /"; '
            'STATUS=$(echo "$HEADERS" | head -1 | awk \'{print $2}\'); '
            'echo "STATUS: $STATUS"; '
            'BODY=$(curl -sL -m 30 "$URL" 2>&1); '
            f'{grep_checks}'
        )

        return [get_shell(), get_shell_exec_flag(), bash_script, "--", safe_url]
