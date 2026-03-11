"""Hydra HTTP Brute Force Tool"""

from typing import Optional, List

from src.core.tools.base import BaseTool, ToolExecutionSignals


class HydraHttpTool(BaseTool):
    """Hydra HTTP form brute force command builder."""

    def __init__(self, timeout: int = 600, signals: Optional[ToolExecutionSignals] = None):
        super().__init__("hydra_http", timeout, signals)

    def estimate_timeout(self, **kwargs) -> int:
        threads = int(kwargs.get("threads", 4) or 4)
        estimate = int(300 + (180 / max(1, threads)))
        return max(120, min(3600, estimate))

    def build_command(
        self,
        target: str,
        username: str = "[USER]",
        wordlist: str = "/path/to/wordlist.txt",
        form_path: str = "/login.php",
        form_params: str = "user=^USER^&pass=^PASS^",
        fail_string: str = "[FAIL_STR]",
        port: int = 80,
        threads: int = 4,
        method: str = "http-form-post",
        **kwargs,
    ) -> List[str]:
        safe_target = self.validate_target(target)
        safe_username = self.validate_target(username, "username")
        safe_wordlist = self.validate_target(wordlist, "wordlist")
        safe_form_path = self.validate_target(form_path, "form_path")
        safe_form_params = self.validate_string(form_params, "form_params")
        safe_fail_string = self.validate_string(fail_string, "fail_string")
        safe_port = self.validate_port(port)
        safe_threads = self.validate_range(threads, 1, 128, "threads")
        safe_method = self.validate_enum(
            method,
            {"http-form-post", "https-form-post", "http-get", "https-get"},
            "method",
        )

        cmd: List[str] = [
            "hydra",
            "-l",
            safe_username,
            "-P",
            safe_wordlist,
            "-t",
            str(safe_threads),
        ]

        if safe_port not in (80, 443):
            cmd.extend(["-s", str(safe_port)])

        cmd.append(safe_target)
        cmd.append(safe_method)
        cmd.append(f"{safe_form_path}:{safe_form_params}:{safe_fail_string}")
        return cmd
