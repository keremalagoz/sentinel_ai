from __future__ import annotations

import logging
import shlex
from typing import Optional, Tuple, List

from src.ai.orchestrator import AIOrchestrator
from src.core.cleaner import get_cleaner
from src.core.process_manager import AdvancedProcessManager
from src.core.validators import InputValidator

logger = logging.getLogger(__name__)

# Izin verilen komut listesi — registry ile tutarli
_ALLOWED_COMMANDS = frozenset({
    "ping", "nmap", "openssl", "gobuster", "nslookup",
    "dig", "nikto", "hydra", "curl", "wget", "sslscan",
})

# Root gerektiren flag'ler
_ROOT_FLAGS = frozenset({"-sS", "-sU", "-O", "-A", "--privileged"})


class BackendGateway:
    """UI ile backend arasindaki tek gecit (facade)."""

    def __init__(self, model: str = "qwen2.5:3b") -> None:
        self._process_manager = AdvancedProcessManager()
        self._orchestrator = AIOrchestrator(model=model)

    @property
    def process_manager(self) -> AdvancedProcessManager:
        return self._process_manager

    def ask_ai(self, user_text: str) -> object:
        return self._orchestrator.process(user_text)

    @staticmethod
    def parse_command(command: str) -> Tuple[Optional[str], List[str], bool]:
        """Komutu parse et ve guvenlik kontrollerinden gecir.

        Returns:
            (cmd, args, requires_root) veya (None, [], False) eger reddedildiyse.
        """
        if not command or not command.strip():
            return None, [], False

        # Shell injection karakter kontrolu
        for char in InputValidator.DANGEROUS_CHARS:
            if char in command:
                logger.warning(
                    "Shell injection attempt detected in command: dangerous char %r",
                    char,
                )
                return None, [], False

        # shlex ile guvenli parse (naive split yerine)
        try:
            parts: List[str] = shlex.split(command)
        except ValueError as exc:
            logger.warning("Malformed command rejected: %s", exc)
            return None, [], False

        if not parts:
            return None, [], False

        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        # Whitelist kontrolu
        if cmd not in _ALLOWED_COMMANDS:
            logger.warning(
                "Command not in allowed list: %s  (allowed: %s)",
                cmd,
                ", ".join(sorted(_ALLOWED_COMMANDS)),
            )
            return None, [], False

        # Arguman guvenlik kontrolu
        for arg in args:
            if not InputValidator.is_safe_arg(arg):
                logger.warning(
                    "Unsafe argument rejected: %r in command %s", arg, cmd
                )
                return None, [], False

        # Root gereksinimi — flag bazli kontrol
        requires_root = bool(_ROOT_FLAGS.intersection(args))

        return cmd, args, requires_root

    def shutdown(self) -> None:
        self._process_manager.stop_process()

    def cleanup_old_sessions(self, days: int) -> int:
        cleaner = get_cleaner()
        return cleaner.cleanup_old_sessions(days=days)
