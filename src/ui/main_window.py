"""
SENTINEL AI - Main Window (Unified Design)
Single header, cohesive layout
"""

import json
import os
import uuid

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from src.ui.styles import Colors, Fonts, GLOBAL_STYLE, STATUS_BAR_STYLE
from src.ui.terminal_view import TerminalView
from src.ui.chat_interface import ChatInterface
from src.ui.settings_dialog import SecuritySettingsDialog
from src.ui.i18n import t, set_language
from src.application.backend_gateway import BackendGateway

# Pre-built status dot styles (M11 optimization)
_DOT_STYLES = {
    "idle": f"background-color: {Colors.STATUS_IDLE}; border-radius: 4px; border: none;",
    "running": f"background-color: {Colors.STATUS_RUNNING}; border-radius: 4px; border: none;",
    "root": f"background-color: {Colors.STATUS_ROOT}; border-radius: 4px; border: none;",
}
_BADGE_STYLES = {
    "idle": f"color: {Colors.TEXT_DIM}; background-color: {Colors.BG_TERTIARY}; padding: 2px 8px; border-radius: 4px; border: none;",
    "running": f"color: {Colors.ACCENT_PRIMARY}; background-color: {Colors.ACCENT_SUBTLE}; padding: 2px 8px; border-radius: 4px; border: none;",
    "root": f"color: #ffffff; background-color: {Colors.DANGER}; padding: 2px 8px; border-radius: 4px; border: none;",
}


SECURITY_SETTINGS_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'temp', 'security_settings.json'
)


class AIWorker(QThread):
    """AI sorgularını UI'yi bloklamadan arka planda çalıştırır."""

    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, gateway: BackendGateway, user_text: str, session_id: str | None = None):
        super().__init__()
        self._gateway = gateway
        self._user_text = user_text
        self._session_id = session_id

    def run(self):
        try:
            if self._session_id:
                response = self._gateway.ask_ai_with_session_compat(
                    self._user_text, self._session_id
                )
            else:
                response = self._gateway.ask_ai(self._user_text)
            self.result_ready.emit(response)
        except Exception as error:
            self.error_occurred.emit(str(error))


class MainWindow(QMainWindow):
    """
    SENTINEL AI Main Window - Unified Design
    
    Features:
    - Single unified header with all controls
    - No sub-headers (clean look)
    - Terminal + Chat splitter
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTINEL AI")
        self.setMinimumSize(1200, 700)
        
        self.backend = BackendGateway(model="qwen2.5:3b")
        self.process_manager = self.backend.process_manager
        self._ai_worker = None
        self._is_horizontal_layout = False
        self._is_swapped = False
        self._awaiting_root_confirmation = False
        self._awaiting_terminal_yesno = False
        self._pending_command = None
        self._pending_correlation_id = ""
        self._security_settings = self._load_security_settings()
        self._risk_level = "low"
        self._ai_state = "checking"   # checking | online | offline
        self._ai_model_name = ""
        # Backend conversation session — multi-turn context enrichment icin
        self._chat_session_id: str = self.backend._orchestrator.create_session()
        set_language(self._security_settings.get("language", "en"))
        self.backend.set_secure_delete(self._security_settings.get("secure_delete", True))
        self.backend.cleanup_old_sessions(
            self._security_settings.get("cleanup_days", 7),
            secure_delete=self._security_settings.get("secure_delete", True),
        )
        
        self.setStyleSheet(GLOBAL_STYLE)
        self._setup_ui()
        self._connect_signals()
        self._apply_text_settings(self._security_settings)
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ── Unified Header ──────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.GRADIENT_START},
                    stop:1 {Colors.GRADIENT_END}
                );
                border-bottom: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        header.setFixedHeight(48)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(4)
        
        # Logo/Title -- unified
        title = QLabel("SENTINEL AI")
        title_font = QFont(Fonts.UI)
        title_font.setPixelSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none; letter-spacing: 3px;")
        
        title_glow = QGraphicsDropShadowEffect()
        title_glow.setBlurRadius(12)
        title_glow.setColor(QColor(59, 130, 246, 60))
        title_glow.setOffset(0, 0)
        title.setGraphicsEffect(title_glow)
        header_layout.addWidget(title)
        
        # Status dot (tooltip with connection info)
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(8, 8)
        self._status_dot.setToolTip(t("header.disconnected"))
        self._status_dot.setStyleSheet(f"""
            background-color: {Colors.STATUS_IDLE};
            border-radius: 4px;
            border: none;
        """)
        header_layout.addWidget(self._status_dot)
        
        # Execution status badge (READY/RUNNING/ROOT) -- in header
        self._header_badge = QLabel(t("badge.ready"))
        badge_font = QFont(Fonts.UI)
        badge_font.setPixelSize(9)
        badge_font.setBold(True)
        self._header_badge.setFont(badge_font)
        self._header_badge.setStyleSheet(f"""
            color: {Colors.TEXT_DIM};
            background-color: {Colors.BG_TERTIARY};
            padding: 2px 8px;
            border-radius: 4px;
            border: none;
        """)
        header_layout.addWidget(self._header_badge)
        
        header_layout.addStretch()
        
        # -- Chat controls --
        self._history_btn = self._make_header_btn(t("btn.hist"), tooltip=t("tooltip.history"))
        self._history_btn.clicked.connect(self._show_history)
        header_layout.addWidget(self._history_btn)
        
        self._new_chat_btn = self._make_header_btn(t("btn.new_chat"), tooltip=t("tooltip.new_chat"), bold=True)
        self._new_chat_btn.clicked.connect(self._new_chat)
        header_layout.addWidget(self._new_chat_btn)
        
        # -- Terminal controls --
        self._new_terminal_btn = self._make_header_btn(t("btn.new_terminal"), tooltip=t("tooltip.new_terminal"), bold=True)
        self._new_terminal_btn.clicked.connect(self._add_terminal)
        header_layout.addWidget(self._new_terminal_btn)

        self._swap_btn = self._make_header_btn(t("btn.swap"), tooltip=t("tooltip.swap"))
        self._swap_btn.clicked.connect(self._swap_chat_terminal)
        header_layout.addWidget(self._swap_btn)

        self._layout_btn = self._make_header_btn(t("btn.layout"), tooltip=t("tooltip.layout"))
        self._layout_btn.clicked.connect(self._toggle_layout_orientation)
        header_layout.addWidget(self._layout_btn)
        
        # Settings
        self._settings_btn = self._make_header_btn(t("btn.settings"), tooltip=t("tooltip.settings"))
        self._settings_btn.clicked.connect(self._on_settings)
        header_layout.addWidget(self._settings_btn)
        
        main_layout.addWidget(header)
        
        # ── Content Splitter ────────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(2)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)
        
        # Chat (Top)
        self.chat_interface = ChatInterface()
        self.chat_interface.setMinimumHeight(280)
        self.splitter.addWidget(self.chat_interface)

        # Terminal (Bottom - tabbed)
        self.terminal_view = TerminalView(self.process_manager)
        self.terminal_view.setMinimumHeight(220)
        self.splitter.addWidget(self.terminal_view)
        
        # Chat 70% / Terminal 30%
        self.splitter.setSizes([620, 260])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setOpaqueResize(False)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        
        main_layout.addWidget(self.splitter, stretch=1)
        
        # ── Status Bar ──────────────────────────────────────
        self._status_bar = QFrame()
        self._status_bar.setObjectName("StatusBar")
        self._status_bar.setFixedHeight(24)
        self._status_bar.setStyleSheet(STATUS_BAR_STYLE)
        
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)
        status_layout.setSpacing(16)
        
        exec_mode = self.backend.process_manager._exec_mgr.mode.value.upper()
        self._mode_label = QLabel(f"{t('status.mode')}: {exec_mode}")
        status_layout.addWidget(self._mode_label)
        
        self._ai_label = QLabel(f"AI: {t('status.checking')}")
        self._ai_label.setStyleSheet(f"color: {Colors.WARNING};")
        status_layout.addWidget(self._ai_label)
        
        self._session_label = QLabel(t("status.session_default"))
        status_layout.addWidget(self._session_label)

        self._telemetry_label = QLabel("Q:0 | Wait:0ms | Run:0ms")
        status_layout.addWidget(self._telemetry_label)
        
        status_layout.addStretch()
        
        self._version_label = QLabel("v0.4.0-dev")
        status_layout.addWidget(self._version_label)
        
        main_layout.addWidget(self._status_bar)
        
        # Check AI connectivity after UI is ready
        QTimer.singleShot(500, self._check_ai_status)

        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(2000)
        self._telemetry_timer.timeout.connect(self._refresh_runtime_metrics)
        self._telemetry_timer.start()
        self._refresh_runtime_metrics()
    
    def _make_header_btn(self, text: str, tooltip: str = "", bold: bool = False) -> QPushButton:
        """Create a consistent header button (auto-width for i18n)."""
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        
        font = QFont()
        font.setPixelSize(11)
        if bold:
            font.setBold(True)
        btn.setFont(font)
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                border-radius: 4px;
                padding: 3px 6px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_TERTIARY};
            }}
        """)
        return btn
    
    def _connect_signals(self):
        # Chat -> Terminal
        self.chat_interface.command_requested.connect(self._execute_command)
        self.chat_interface.stop_requested.connect(self.terminal_view.stop_command)
        self.chat_interface.input_sent.connect(self.terminal_view.send_input)
        self.chat_interface.action_response.connect(self._handle_action_response)
        self.chat_interface.message_sent.connect(self._handle_user_message)
        
        # Terminal -> Chat
        self.terminal_view.sig_status_changed.connect(self._on_terminal_status)
        self.terminal_view.sig_prompt_detected.connect(self._on_prompt_detected)
        self.terminal_view.sig_process_finished.connect(self._on_process_finished)
        self.terminal_view.sig_command_submitted.connect(self._execute_command_from_terminal)
    
    # ── Header Actions ──
    
    def _show_history(self):
        self.chat_interface._show_history()
    
    def _new_chat(self):
        self.chat_interface._new_chat()
        # Yeni sohbet basladiginda yeni backend session olustur
        self._chat_session_id = self.backend._orchestrator.create_session()
    
    def _add_terminal(self):
        self.terminal_view._add_terminal()

    def _toggle_layout_orientation(self):
        self._is_horizontal_layout = not self._is_horizontal_layout
        if self._is_horizontal_layout:
            self.splitter.setOrientation(Qt.Orientation.Horizontal)
            self.splitter.setSizes([420, 780])
        else:
            self.splitter.setOrientation(Qt.Orientation.Vertical)
            self.splitter.setSizes([620, 260])

    def _swap_chat_terminal(self):
        """Swap the positions of Chat and Terminal in the splitter."""
        self._is_swapped = not self._is_swapped
        sizes = self.splitter.sizes()
        if self._is_swapped:
            self.splitter.insertWidget(0, self.terminal_view)
        else:
            self.splitter.insertWidget(0, self.chat_interface)
        self.splitter.setSizes(list(reversed(sizes)))

    def _on_splitter_moved(self, pos: int, index: int):
        self.chat_interface.keep_scroll_position()
    
    # ── Command Execution ──

    @staticmethod
    def _next_correlation_id() -> str:
        return f"cid_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def _normalize_risk(risk_level: str) -> str:
        value = (risk_level or "low").lower()
        if value.endswith(".high"):
            return "high"
        if value.endswith(".medium"):
            return "medium"
        if value.endswith(".low"):
            return "low"
        if value in {"high", "medium", "low"}:
            return value
        return "low"

    def _risk_to_ui(self, risk_level: str) -> str:
        normalized = self._normalize_risk(risk_level)
        if normalized == "high":
            return t("risk.root_required")
        if normalized == "medium":
            return t("risk.caution")
        return t("risk.safe")

    def _update_risk_indicator(self, risk_level: str) -> None:
        normalized = self._normalize_risk(risk_level)
        self._risk_level = normalized
        label = self._risk_to_ui(risk_level)
        color = Colors.SUCCESS
        if normalized == "medium":
            color = Colors.WARNING
        elif normalized == "high":
            color = Colors.DANGER
        self._session_label.setText(f"{t('status.risk')}: {label}")
        self._session_label.setStyleSheet(f"color: {color};")

    def _request_root_confirmation(
        self,
        cmd: str,
        args: list,
        risk_level: str,
        correlation_id: str,
    ) -> None:
        self._pending_command = (cmd, args, risk_level)
        self._pending_correlation_id = correlation_id
        self._awaiting_root_confirmation = True
        self._update_risk_indicator(risk_level)
        self.chat_interface.add_ai_message(
            t("msg.root_confirm"),
            None,
            correlation_id=correlation_id,
        )
        self.chat_interface.show_yesno_prompt()

    def _handle_action_response(self, value: str):
        if self._awaiting_root_confirmation and self._pending_command:
            if value.lower() == "y":
                cmd, args, risk_level = self._pending_command
                self.terminal_view.start_command(
                    cmd,
                    args,
                    True,
                    correlation_id=self._pending_correlation_id,
                    risk_label=self._risk_to_ui(risk_level),
                )
                self.chat_interface.show_stop_button()
                self.chat_interface.add_ai_message(
                    t("msg.root_approved"),
                    correlation_id=self._pending_correlation_id,
                )
            else:
                self.chat_interface.add_ai_message(
                    t("msg.root_cancelled"),
                    correlation_id=self._pending_correlation_id,
                )

            self._awaiting_root_confirmation = False
            self._pending_command = None
            self._pending_correlation_id = ""
            self.chat_interface.hide_action_buttons()
            return

        if self._awaiting_terminal_yesno:
            self.terminal_view.send_input(value)
    
    def _needs_confirmation(self, requires_root: bool, risk_level: str) -> bool:
        """Check if current security settings require user confirmation."""
        if requires_root:
            return bool(self._security_settings.get("confirm_root", True))
        normalized = self._normalize_risk(risk_level)
        if normalized in ("high", "medium") and self._security_settings.get("warn_high_risk", True):
            return True
        return False

    def _execute_command(self, command: str):
        cmd, args, requires_root, risk_level = self.backend.parse_command_with_risk(command)
        if not cmd:
            return
        correlation_id = self._next_correlation_id()
        self._update_risk_indicator(risk_level)
        if self._needs_confirmation(requires_root, risk_level):
            self._request_root_confirmation(cmd, args, risk_level, correlation_id)
            return
        self.terminal_view.start_command(
            cmd,
            args,
            requires_root,
            correlation_id=correlation_id,
            risk_label=self._risk_to_ui(risk_level),
        )
        self.chat_interface.show_stop_button()
    
    def _execute_command_from_terminal(self, command: str):
        cmd, args, requires_root, risk_level = self.backend.parse_command_with_risk(command)
        if not cmd:
            self.terminal_view._log(
                t("msg.cmd_rejected").format(cmd=command.split()[0] if command.strip() else ""),
                Colors.WARNING,
            )
            return
        correlation_id = self._next_correlation_id()
        self._update_risk_indicator(risk_level)
        if self._needs_confirmation(requires_root, risk_level):
            self._request_root_confirmation(cmd, args, risk_level, correlation_id)
            return
        self.terminal_view.start_command(
            cmd,
            args,
            requires_root,
            correlation_id=correlation_id,
            risk_label=self._risk_to_ui(risk_level),
        )
    
    def _handle_user_message(self, text: str):
        """Process user message with real AI orchestrator."""
        correlation_id = self._next_correlation_id()
        self.chat_interface.add_user_message(text, correlation_id=correlation_id)

        if self._ai_worker and self._ai_worker.isRunning():
            self.chat_interface.add_ai_message(t("msg.ai_busy"))
            return

        self._ai_worker = AIWorker(self.backend, text, session_id=self._chat_session_id)
        self._ai_worker.result_ready.connect(self._on_ai_result)
        self._ai_worker.error_occurred.connect(self._on_ai_error)
        self._pending_correlation_id = correlation_id
        self._ai_worker.start()

    def _on_ai_result(self, response):
        command_text = None
        risk_level = "low"
        requires_root = False
        if getattr(response, "command", None):
            command = response.command
            command_text = f"{command.tool} {' '.join(command.arguments)}".strip()
            risk_level = self._normalize_risk(str(getattr(command, "risk_level", "low")))
            requires_root = bool(getattr(command, "requires_root", False))

        message = getattr(response, "message", None) or t("msg.ai_no_response")
        if requires_root:
            risk_level = "high"
        self._update_risk_indicator(risk_level)
        self.chat_interface.add_ai_message(
            message,
            command_text,
            correlation_id=self._pending_correlation_id or None,
        )

    def _on_ai_error(self, error: str):
        self.chat_interface.add_ai_message(
            t("msg.ai_error").format(error=error),
            correlation_id=self._pending_correlation_id or None,
        )
    
    # ── Event Handlers ──
    
    def _on_terminal_status(self, tab_name: str, is_running: bool, requires_root: bool):
        if is_running:
            self.chat_interface.show_stop_button()
            if requires_root:
                self._update_status_dot("root")
            else:
                self._update_status_dot("running")
        else:
            self.chat_interface.hide_action_buttons()
            self._update_status_dot("idle")
    
    def _update_status_dot(self, state: str) -> None:
        """Update the header status dot and badge based on execution state."""
        self._status_dot.setStyleSheet(_DOT_STYLES.get(state, _DOT_STYLES["idle"]))
        
        # Update header badge
        badge_text_map = {
            "idle": t("badge.ready"),
            "running": t("badge.running"),
            "root": t("badge.root"),
        }
        self._header_badge.setText(badge_text_map.get(state, t("badge.ready")))
        self._header_badge.setStyleSheet(_BADGE_STYLES.get(state, _BADGE_STYLES["idle"]))
    
    def _on_prompt_detected(self, prompt_type: str):
        if prompt_type == "password":
            self.chat_interface.show_password_prompt()
        elif prompt_type == "yesno":
            self._awaiting_terminal_yesno = True
            self.chat_interface.show_yesno_prompt()
    
    def _on_process_finished(self, exit_code: int):
        self._awaiting_terminal_yesno = False
        self.chat_interface.hide_action_buttons()
        self._update_risk_indicator("low")
    
    def _on_settings(self):
        # Fetch current statuses
        docker_running = self.backend.is_docker_running()
            
        ai_text = self._ai_label.text().replace("AI: ", "")
        mode = self.backend.process_manager._exec_mgr.mode.value.upper()
        
        dialog = SecuritySettingsDialog(
            self,
            cleanup_handler=self.backend.cleanup_old_sessions,
            clear_all_chats_handler=self.chat_interface.delete_all_history,
        )
        dialog.settings_changed.connect(self._apply_security_settings)
        dialog.set_settings(self._security_settings)
        dialog.update_connection_status(docker_running, ai_text, mode)
        dialog.exec()

    def _load_security_settings(self) -> dict:
        defaults = {
            "cleanup_days": 7,
            "secure_delete": True,
            "font_size": 13,
            "language": "en",
            "confirm_root": True,
            "warn_high_risk": True,
            "auto_cleanup": "off",
        }
        try:
            if os.path.exists(SECURITY_SETTINGS_FILE):
                with open(SECURITY_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "cleanup_days": int(data.get("cleanup_days", defaults["cleanup_days"])),
                        "secure_delete": bool(data.get("secure_delete", defaults["secure_delete"])),
                        "font_size": int(data.get("font_size", defaults["font_size"])),
                        "language": str(data.get("language", defaults["language"])),
                        "confirm_root": bool(data.get("confirm_root", defaults["confirm_root"])),
                        "warn_high_risk": bool(data.get("warn_high_risk", defaults["warn_high_risk"])),
                        "auto_cleanup": str(data.get("auto_cleanup", defaults["auto_cleanup"])),
                    }
        except Exception:
            pass
        return defaults

    def _save_security_settings(self) -> None:
        try:
            os.makedirs(os.path.dirname(SECURITY_SETTINGS_FILE), exist_ok=True)
            with open(SECURITY_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._security_settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _apply_security_settings(self, settings: dict) -> None:
        self._security_settings = {
            "cleanup_days": int(settings.get("cleanup_days", 7)),
            "secure_delete": bool(settings.get("secure_delete", True)),
            "font_size": int(settings.get("font_size", 13)),
            "language": str(settings.get("language", "en")),
            "confirm_root": bool(settings.get("confirm_root", True)),
            "warn_high_risk": bool(settings.get("warn_high_risk", True)),
            "auto_cleanup": str(settings.get("auto_cleanup", "off")),
        }
        self.backend.set_secure_delete(self._security_settings["secure_delete"])
        set_language(self._security_settings["language"])
        self._apply_text_settings(self._security_settings)
        self._refresh_ui_texts()
        self._save_security_settings()

    def _apply_text_settings(self, settings: dict) -> None:
        font_size = int(settings.get("font_size", 13))
        self.chat_interface.set_text_font_size(font_size)
        self.terminal_view.set_text_font_size(font_size)
    
    def closeEvent(self, event):
        self.chat_interface.save_on_close()
        self.backend.shutdown()
        event.accept()
    
    def _refresh_ui_texts(self) -> None:
        """Re-apply all translatable UI texts after language change."""
        self._history_btn.setText(t("btn.hist"))
        self._history_btn.setToolTip(t("tooltip.history"))
        self._new_chat_btn.setText(t("btn.new_chat"))
        self._new_chat_btn.setToolTip(t("tooltip.new_chat"))
        self._new_terminal_btn.setText(t("btn.new_terminal"))
        self._new_terminal_btn.setToolTip(t("tooltip.new_terminal"))
        self._swap_btn.setText(t("btn.swap"))
        self._swap_btn.setToolTip(t("tooltip.swap"))
        self._layout_btn.setText(t("btn.layout"))
        self._layout_btn.setToolTip(t("tooltip.layout"))
        self._settings_btn.setText(t("btn.settings"))
        self._settings_btn.setToolTip(t("tooltip.settings"))

        exec_mode = self.backend.process_manager._exec_mgr.mode.value.upper()
        self._mode_label.setText(f"{t('status.mode')}: {exec_mode}")
        self._update_ai_label()
        self._update_risk_indicator(self._risk_level)
        self._refresh_runtime_metrics()

        self.chat_interface.refresh_texts()
        self.terminal_view.refresh_texts()

    def _update_ai_label(self) -> None:
        """Refresh the AI status label with current state + language."""
        if self._ai_state == "online":
            self._ai_label.setText(f"AI: {self._ai_model_name}")
            self._ai_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif self._ai_state == "offline":
            self._ai_label.setText(f"AI: {t('msg.offline')}")
            self._ai_label.setStyleSheet(f"color: {Colors.DANGER};")
        else:
            self._ai_label.setText(f"AI: {t('status.checking')}")
            self._ai_label.setStyleSheet(f"color: {Colors.WARNING};")

    def _check_ai_status(self) -> None:
        """Check Ollama connectivity and update status bar."""
        self._ai_checker = _OllamaChecker()
        self._ai_checker.result_ready.connect(self._on_ai_check_result)
        self._ai_checker.start()
    
    def _on_ai_check_result(self, status: str) -> None:
        """Handle AI connectivity check result."""
        if status.startswith("online"):
            self._ai_state = "online"
            self._ai_model_name = status.split(":", 1)[1] if ":" in status else "Connected"
        else:
            self._ai_state = "offline"
            self._ai_model_name = ""
        self._update_ai_label()

    def _refresh_runtime_metrics(self) -> None:
        """Render minimal runtime telemetry in status bar."""
        try:
            metrics = self.backend.get_runtime_metrics()
            queued = int(metrics.get("queued_executions", 0) or 0)
            avg_queue_wait = float(metrics.get("avg_queue_wait_ms", 0.0) or 0.0)
            avg_tool_run = float(metrics.get("avg_tool_run_ms", 0.0) or 0.0)
            self._telemetry_label.setText(
                f"Q:{queued} | Wait:{avg_queue_wait:.0f}ms | Run:{avg_tool_run:.0f}ms"
            )
        except Exception:
            self._telemetry_label.setText("Q:0 | Wait:0ms | Run:0ms")


class _OllamaChecker(QThread):
    """Background thread to check Ollama API availability."""
    
    result_ready = pyqtSignal(str)
    
    def run(self) -> None:
        import urllib.request
        import json as _json
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read().decode())
                models = data.get("models", [])
                if models:
                    name = models[0].get("name", "Connected")
                    self.result_ready.emit(f"online:{name}")
                else:
                    self.result_ready.emit("online:No Model")
        except Exception:
            self.result_ready.emit("offline")
