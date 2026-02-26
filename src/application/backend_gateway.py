from __future__ import annotations

from src.ai.orchestrator import AIOrchestrator
from src.core.cleaner import get_cleaner
from src.core.process_manager import AdvancedProcessManager


class BackendGateway:
    """UI ile backend arasındaki tek geçit (façade)."""

    def __init__(self, model: str = "whiterabbitneo"):
        self._process_manager = AdvancedProcessManager()
        self._orchestrator = AIOrchestrator(model=model)

    @property
    def process_manager(self) -> AdvancedProcessManager:
        return self._process_manager

    def ask_ai(self, user_text: str):
        return self._orchestrator.process(user_text)

    @staticmethod
    def parse_command(command: str):
        parts = command.split()
        if not parts:
            return None, [], False

        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        requires_root = any(flag in command for flag in ["sudo", "-sS", "-sU", "--privileged"])
        return cmd, args, requires_root

    def shutdown(self) -> None:
        self._process_manager.stop_process()

    def cleanup_old_sessions(self, days: int) -> int:
        cleaner = get_cleaner()
        return cleaner.cleanup_old_sessions(days=days)
