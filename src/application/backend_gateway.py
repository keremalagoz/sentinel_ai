from __future__ import annotations

import logging
import shlex
from typing import Optional, Tuple, List, Dict, Any

from src.ai.orchestrator import AIOrchestrator
from src.core.cleaner import get_cleaner
from src.core.process_manager import AdvancedProcessManager
from src.core.validators import InputValidator

from src.core.platform_utils import is_windows

logger = logging.getLogger(__name__)

# Izin verilen komut listesi — registry ile tutarli
_SECURITY_COMMANDS = frozenset({
    "ping", "nmap", "openssl", "gobuster", "nslookup", "whois",
    "dig", "nikto", "hydra", "curl", "wget", "sslscan",
})

# Platforma ozgu tanisal komutlar
_PLATFORM_COMMANDS = frozenset({
    "ipconfig", "tracert", "netstat", "systeminfo", "hostname",
    "arp", "pathping", "route",
}) if is_windows() else frozenset({
    "ifconfig", "ip", "traceroute", "netstat", "hostname",
    "arp", "ss", "route",
})

_ALLOWED_COMMANDS = _SECURITY_COMMANDS | _PLATFORM_COMMANDS

# Root gerektiren flag'ler
_ROOT_FLAGS = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})


class BackendGateway:
    """UI ile backend arasindaki tek gecit (facade)."""

    def __init__(self, model: str = "qwen2.5:3b") -> None:
        self._process_manager = AdvancedProcessManager()
        self._orchestrator = AIOrchestrator(model=model)
        self._secure_delete = True

    @property
    def process_manager(self) -> AdvancedProcessManager:
        return self._process_manager

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

    @staticmethod
    def parse_command_with_risk(command: str) -> Tuple[Optional[str], List[str], bool, str]:
        """Komutu parse et ve guvenlik kontrollerinden gecir.

        Returns:
            (cmd, args, requires_root, risk_level) veya (None, [], False, "high") eger reddedildiyse.
        """
        if not command or not command.strip():
            return None, [], False, "high"

        # Shell injection karakter kontrolu
        for char in InputValidator.DANGEROUS_CHARS:
            if char in command:
                logger.warning(
                    "Shell injection attempt detected in command: dangerous char %r",
                    char,
                )
                return None, [], False, "high"

        # shlex ile guvenli parse (naive split yerine)
        try:
            parts: List[str] = shlex.split(command)
        except ValueError as exc:
            logger.warning("Malformed command rejected: %s", exc)
            return None, [], False, "high"

        if not parts:
            return None, [], False, "high"

        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        # Whitelist kontrolu
        if cmd not in _ALLOWED_COMMANDS:
            logger.warning(
                "Command not in allowed list: %s  (allowed: %s)",
                cmd,
                ", ".join(sorted(_ALLOWED_COMMANDS)),
            )
            return None, [], False, "high"

        # Arguman guvenlik kontrolu
        for arg in args:
            if not InputValidator.is_safe_arg(arg):
                logger.warning(
                    "Unsafe argument rejected: %r in command %s", arg, cmd
                )
                return None, [], False, "high"

        # Root gereksinimi — flag bazli kontrol
        requires_root = bool(_ROOT_FLAGS.intersection(args))

        risk_level = "low"
        if requires_root:
            risk_level = "high"
        elif cmd in {"nmap", "nikto", "hydra", "gobuster", "sslscan"}:
            risk_level = "medium"

        return cmd, args, requires_root, risk_level

    @staticmethod
    def parse_command(command: str) -> Tuple[Optional[str], List[str], bool]:
        """Backward-compatible parse API.

        Returns:
            (cmd, args, requires_root) veya (None, [], False) eger reddedildiyse.
        """
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
