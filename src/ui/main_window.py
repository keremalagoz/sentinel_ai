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
from src.application.backend_gateway import BackendGateway


SECURITY_SETTINGS_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'temp', 'security_settings.json'
)


class AIWorker(QThread):
    """AI sorgularını UI'yi bloklamadan arka planda çalıştırır."""

    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, gateway: BackendGateway, user_text: str):
        super().__init__()
        self._gateway = gateway
        self._user_text = user_text

    def run(self):
        try:
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
        self._awaiting_root_confirmation = False
        self._awaiting_terminal_yesno = False
        self._pending_command = None
        self._pending_correlation_id = ""
        self._security_settings = self._load_security_settings()
        self._risk_level = "low"
        
        self.setStyleSheet(GLOBAL_STYLE)
        self._setup_ui()
        self._connect_signals()
    
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
        self._status_dot.setToolTip("Disconnected")
        self._status_dot.setStyleSheet(f"""
            background-color: {Colors.STATUS_IDLE};
            border-radius: 4px;
            border: none;
        """)
        header_layout.addWidget(self._status_dot)
        
        # Execution status badge (READY/RUNNING/ROOT) -- in header
        self._header_badge = QLabel("READY")
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
        self._history_btn = self._make_header_btn("Hist", tooltip="Sohbet Gecmisi", width=46)
        self._history_btn.clicked.connect(self._show_history)
        header_layout.addWidget(self._history_btn)
        
        self._new_chat_btn = self._make_header_btn("+C", tooltip="Yeni Sohbet", width=36, bold=True)
        self._new_chat_btn.clicked.connect(self._new_chat)
        header_layout.addWidget(self._new_chat_btn)
        
        # -- Terminal controls --
        self._new_terminal_btn = self._make_header_btn("+T", tooltip="Yeni Terminal", width=36, bold=True)
        self._new_terminal_btn.clicked.connect(self._add_terminal)
        header_layout.addWidget(self._new_terminal_btn)

        self._layout_btn = self._make_header_btn("Layout", tooltip="Altli/Ustlu - Sagli/Sollu Degistir", width=62)
        self._layout_btn.clicked.connect(self._toggle_layout_orientation)
        header_layout.addWidget(self._layout_btn)
        
        # Settings
        self._settings_btn = self._make_header_btn("Settings", tooltip="Ayarlar", width=66)
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
        self._mode_label = QLabel(f"Mode: {exec_mode}")
        status_layout.addWidget(self._mode_label)
        
        self._ai_label = QLabel("AI: Checking...")
        self._ai_label.setStyleSheet(f"color: {Colors.WARNING};")
        status_layout.addWidget(self._ai_label)
        
        self._session_label = QLabel("Session: --")
        status_layout.addWidget(self._session_label)
        
        status_layout.addStretch()
        
        self._version_label = QLabel("v0.4.0-dev")
        status_layout.addWidget(self._version_label)
        
        main_layout.addWidget(self._status_bar)
        
        # Check AI connectivity after UI is ready
        QTimer.singleShot(500, self._check_ai_status)
    
    def _make_header_btn(self, text, tooltip="", size=None, width=None, bold=False):
        """Create a consistent header button"""
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if size:
            btn.setFixedSize(size, 28)
        elif width:
            btn.setFixedSize(width, 28)
        else:
            btn.setFixedHeight(28)
        
        font = QFont()
        font.setPixelSize(11 if not size else 13)
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
            return "ROOT-REQUIRED"
        if normalized == "medium":
            return "CAUTION"
        return "SAFE"

    def _update_risk_indicator(self, risk_level: str) -> None:
        normalized = self._normalize_risk(risk_level)
        self._risk_level = normalized
        label = self._risk_to_ui(risk_level)
        color = Colors.SUCCESS
        if normalized == "medium":
            color = Colors.WARNING
        elif normalized == "high":
            color = Colors.DANGER
        self._session_label.setText(f"Risk: {label}")
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
            "Bu komut ROOT yetkisi gerektiriyor. Çalıştırmak için onay ver (Yes/No).",
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
                    "Root komut onaylandı, çalıştırılıyor.",
                    correlation_id=self._pending_correlation_id,
                )
            else:
                self.chat_interface.add_ai_message(
                    "Root komut kullanıcı tarafından iptal edildi.",
                    correlation_id=self._pending_correlation_id,
                )

            self._awaiting_root_confirmation = False
            self._pending_command = None
            self._pending_correlation_id = ""
            self.chat_interface.hide_action_buttons()
            return

        if self._awaiting_terminal_yesno:
            self.terminal_view.send_input(value)
    
    def _execute_command(self, command: str):
        cmd, args, requires_root, risk_level = self.backend.parse_command_with_risk(command)
        if not cmd:
            return
        correlation_id = self._next_correlation_id()
        self._update_risk_indicator(risk_level)
        if requires_root:
            self._request_root_confirmation(cmd, args, risk_level, correlation_id)
            return
        self.terminal_view.start_command(
            cmd,
            args,
            False,
            correlation_id=correlation_id,
            risk_label=self._risk_to_ui(risk_level),
        )
        self.chat_interface.show_stop_button()
    
    def _execute_command_from_terminal(self, command: str):
        cmd, args, requires_root, risk_level = self.backend.parse_command_with_risk(command)
        if not cmd:
            self.terminal_view._log(
                f"[!] Komut reddedildi: '{command.split()[0] if command.strip() else ''}' "
                f"izin verilen komutlar degil veya guvenlik kontrolunden gecemedi.",
                Colors.WARNING,
            )
            return
        correlation_id = self._next_correlation_id()
        self._update_risk_indicator(risk_level)
        if requires_root:
            self._request_root_confirmation(cmd, args, risk_level, correlation_id)
            return
        self.terminal_view.start_command(
            cmd,
            args,
            False,
            correlation_id=correlation_id,
            risk_label=self._risk_to_ui(risk_level),
        )
    
    def _handle_user_message(self, text: str):
        """Process user message with real AI orchestrator."""
        correlation_id = self._next_correlation_id()
        self.chat_interface.add_user_message(text, correlation_id=correlation_id)

        if self._ai_worker and self._ai_worker.isRunning():
            self.chat_interface.add_ai_message("Önceki AI isteği hâlâ işleniyor, lütfen birkaç saniye bekleyin.")
            return

        self._ai_worker = AIWorker(self.backend, text)
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

        message = getattr(response, "message", None) or "AI yanıtı alınamadı."
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
            f"AI hatası: {error}",
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
        color_map = {
            "idle": Colors.STATUS_IDLE,
            "running": Colors.STATUS_RUNNING,
            "root": Colors.STATUS_ROOT,
        }
        color = color_map.get(state, Colors.STATUS_IDLE)
        self._status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 4px;
            border: none;
        """)
        
        # Update header badge
        badge_config = {
            "idle": ("READY", Colors.TEXT_DIM, Colors.BG_TERTIARY),
            "running": ("RUNNING", Colors.ACCENT_PRIMARY, Colors.ACCENT_SUBTLE),
            "root": ("ROOT", "#ffffff", Colors.DANGER),
        }
        text, fg, bg = badge_config.get(state, ("READY", Colors.TEXT_DIM, Colors.BG_TERTIARY))
        self._header_badge.setText(text)
        self._header_badge.setStyleSheet(f"""
            color: {fg};
            background-color: {bg};
            padding: 2px 8px;
            border-radius: 4px;
            border: none;
        """)
    
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
        )
        dialog.settings_changed.connect(self._apply_security_settings)
        dialog.set_settings(self._security_settings)
        dialog.update_connection_status(docker_running, ai_text, mode)
        dialog.exec()

    def _load_security_settings(self) -> dict:
        try:
            if os.path.exists(SECURITY_SETTINGS_FILE):
                with open(SECURITY_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "cleanup_days": int(data.get("cleanup_days", 7)),
                        "secure_delete": bool(data.get("secure_delete", True)),
                    }
        except Exception:
            pass
        return {"cleanup_days": 7, "secure_delete": True}

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
        }
        self._save_security_settings()
    
    def closeEvent(self, event):
        self.chat_interface.save_on_close()
        self.backend.shutdown()
        event.accept()
    
    def _check_ai_status(self) -> None:
        """Check Ollama connectivity and update status bar."""
        self._ai_checker = _OllamaChecker()
        self._ai_checker.result_ready.connect(self._on_ai_check_result)
        self._ai_checker.start()
    
    def _on_ai_check_result(self, status: str) -> None:
        """Handle AI connectivity check result."""
        if status.startswith("online"):
            model_name = status.split(":", 1)[1] if ":" in status else "Connected"
            self._ai_label.setText(f"AI: {model_name}")
            self._ai_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        else:
            self._ai_label.setText("AI: Offline")
            self._ai_label.setStyleSheet(f"color: {Colors.DANGER};")


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
