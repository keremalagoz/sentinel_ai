from __future__ import annotations

import logging
import os
import shlex
from typing import Optional, Tuple, List, Dict, Any

from src.ai.orchestrator import AIOrchestrator
from src.core.cleaner import get_cleaner
from src.core.process_manager import AdvancedProcessManager
from src.core.sentinel_coordinator import SentinelCoordinator
from src.core.validators import InputValidator
from src.core.platform_utils import is_windows

logger = logging.getLogger(__name__)

_SECURITY_COMMANDS = frozenset({
    "ping", "nmap", "openssl", "gobuster", "nslookup", "whois",
    "dig", "nikto", "hydra", "curl", "wget", "sslscan",
    "sqlmap",
})

_PLATFORM_COMMANDS = (
    frozenset({
        "ipconfig",
        "tracert",
        "netstat",
        "systeminfo",
        "hostname",
        "arp",
        "pathping",
        "route",
    })
    if is_windows()
    else frozenset({
        "ifconfig",
        "ip",
        "traceroute",
        "netstat",
        "hostname",
        "arp",
        "ss",
        "route",
    })
)

_RAW_ALLOWED_COMMANDS = _SECURITY_COMMANDS | _PLATFORM_COMMANDS
_STRUCTURED_SHELL_COMMANDS = frozenset({"bash", "cmd", "powershell"})

_ROOT_FLAGS = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})


def _normalize_executable_name(command: str) -> str:
    normalized = os.path.basename(str(command or "").strip().strip('"')).lower()
    for suffix in (".exe", ".cmd", ".bat", ".com"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _normalize_risk_level(risk_level: Any) -> str:
    value = getattr(risk_level, "value", risk_level)
    normalized = str(value or "low").strip().lower()
    if normalized.endswith(".high"):
        return "high"
    if normalized.endswith(".medium"):
        return "medium"
    if normalized.endswith(".low"):
        return "low"
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "low"


class BackendGateway:
    """UI ile backend arasindaki tek gecit (facade)."""

    def __init__(self, model: str = "qwen2.5:3b") -> None:
        self._process_manager = AdvancedProcessManager()
        self._coordinator = SentinelCoordinator()
        self._orchestrator = AIOrchestrator(model=model, coordinator=self._coordinator)
        self._secure_delete = True

    @property
    def process_manager(self) -> AdvancedProcessManager:
        return self._process_manager

    def create_session(self, session_id: Optional[str] = None) -> str:
        return self._orchestrator.create_session(session_id=session_id)

    def ask_ai(self, user_text: str) -> object:
        return self._orchestrator.process(user_text)

    def ask_ai_with_session(
        self,
        user_text: str,
        session_id: Optional[str],
        target: Optional[str] = None,
    ) -> dict:
        return self._orchestrator.process_v2(
            user_input=user_text,
            target=target,
            session_id=session_id,
        )

    def ask_ai_with_session_compat(
        self,
        user_text: str,
        session_id: Optional[str],
        target: Optional[str] = None,
    ) -> object:
        return self._orchestrator.process_with_session(
            user_input=user_text,
            target=target,
            session_id=session_id,
        )

    @staticmethod
    def prepare_structured_command(
        command: Any,
    ) -> Tuple[Optional[str], List[str], bool, str]:
        """Validate an orchestrator-built structured command."""
        if command is None:
            return None, [], False, "high"

        if isinstance(command, dict):
            executable = command.get("executable") or command.get("tool")
            arguments = command.get("arguments", [])
            requires_root = bool(command.get("requires_root", False))
            risk_level = command.get("risk_level", "low")
        else:
            executable = getattr(command, "executable", None) or getattr(command, "tool", None)
            arguments = getattr(command, "arguments", [])
            requires_root = bool(getattr(command, "requires_root", False))
            risk_level = getattr(command, "risk_level", "low")

        if not executable:
            return None, [], False, "high"

        if not isinstance(arguments, list):
            logger.warning("Structured command rejected: arguments is not a list")
            return None, [], False, "high"

        args = [str(arg) for arg in arguments]
        executable = str(executable).strip()
        if not executable:
            return None, [], False, "high"

        cmd_name = _normalize_executable_name(executable)
        risk = _normalize_risk_level(risk_level)

        if cmd_name in _STRUCTURED_SHELL_COMMANDS:
            if not args or args[0].lower() not in {"-c", "-command", "/c"}:
                logger.warning("Structured shell wrapper rejected: invalid exec flag")
                return None, [], False, "high"
            validator = InputValidator.is_safe_shell_wrapper_arg
        else:
            if cmd_name not in _RAW_ALLOWED_COMMANDS:
                logger.warning("Structured command rejected: unsupported executable %s", executable)
                return None, [], False, "high"
            validator = InputValidator.is_safe_structured_arg

        for arg in args:
            if not validator(arg):
                logger.warning(
                    "Structured command rejected: unsafe arg %r for executable %s",
                    arg,
                    executable,
                )
                return None, [], False, "high"

        if requires_root:
            risk = "high"
        elif risk == "low" and cmd_name in {"hydra", "sqlmap"}:
            risk = "high"
        elif risk == "low" and cmd_name in {"nmap", "nikto", "gobuster", "sslscan", "bash", "cmd", "powershell"}:
            risk = "medium"

        return executable, args, requires_root, risk

    @staticmethod
    def parse_command_with_risk(command: str) -> Tuple[Optional[str], List[str], bool, str]:
        """Parse and validate a raw manual command."""
        if not command or not command.strip():
            return None, [], False, "high"

        for char in InputValidator.DANGEROUS_CHARS:
            if char in command:
                logger.warning(
                    "Shell injection attempt detected in command: dangerous char %r",
                    char,
                )
                return None, [], False, "high"

        try:
            parts: List[str] = shlex.split(command, posix=not is_windows())
        except ValueError as exc:
            logger.warning("Malformed command rejected: %s", exc)
            return None, [], False, "high"

        if not parts:
            return None, [], False, "high"

        raw_cmd = parts[0]
        cmd = _normalize_executable_name(raw_cmd)
        args = parts[1:] if len(parts) > 1 else []

        if cmd not in _RAW_ALLOWED_COMMANDS:
            logger.warning(
                "Command not in allowed list: %s  (allowed: %s)",
                cmd,
                ", ".join(sorted(_RAW_ALLOWED_COMMANDS)),
            )
            return None, [], False, "high"

        for arg in args:
            if not InputValidator.is_safe_arg(arg):
                logger.warning("Unsafe argument rejected: %r in command %s", arg, cmd)
                return None, [], False, "high"

        requires_root = bool(_ROOT_FLAGS.intersection(args))

        risk_level = "low"
        if requires_root or cmd in {"hydra", "sqlmap"}:
            risk_level = "high"
        elif cmd in {"nmap", "nikto", "gobuster", "sslscan"}:
            risk_level = "medium"

        return cmd, args, requires_root, risk_level

    @staticmethod
    def parse_command(command: str) -> Tuple[Optional[str], List[str], bool]:
        cmd, args, requires_root, _ = BackendGateway.parse_command_with_risk(command)
        return cmd, args, requires_root

    def shutdown(self) -> None:
        self._process_manager.stop_process()

    def cleanup_old_sessions(self, days: int, secure_delete: Optional[bool] = None) -> int:
        cleaner = get_cleaner()
        secure_flag = self._secure_delete if secure_delete is None else bool(secure_delete)
        return cleaner.cleanup_old_sessions(days=days, secure_delete=secure_flag)

    def set_secure_delete(self, enabled: bool) -> None:
        self._secure_delete = bool(enabled)

    def get_runtime_metrics(self) -> Dict[str, Any]:
        tool_manager = getattr(self._process_manager, "_tool_manager", None)
        if tool_manager and hasattr(tool_manager, "get_runtime_metrics"):
            return tool_manager.get_runtime_metrics()
        return {
            "active_executions": 0,
            "queued_executions": 0,
            "per_tool_active": {},
            "avg_queue_wait_ms": 0.0,
            "avg_tool_run_ms": 0.0,
            "recent_count": 0,
        }

    def is_docker_running(self) -> bool:
        try:
            from src.core.docker_runner import is_container_running

            return is_container_running()
        except Exception:
            return False
