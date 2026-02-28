"""
SENTINEL AI - Main Window (Unified Design)
Single header, cohesive layout
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.ui.styles import Colors, Fonts, GLOBAL_STYLE
from src.ui.terminal_view import TerminalView
from src.ui.chat_interface import ChatInterface
from src.ui.settings_dialog import SecuritySettingsDialog
from src.application.backend_gateway import BackendGateway


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
        self._is_swapped = False
        
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
                background-color: {Colors.BG_PRIMARY};
                border-bottom: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        header.setFixedHeight(42)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 12, 0)
        header_layout.setSpacing(6)
        
        # Logo/Title
        logo = QLabel("⬡")
        logo_font = QFont()
        logo_font.setPixelSize(18)
        logo.setFont(logo_font)
        logo.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; background: transparent; border: none;")
        header_layout.addWidget(logo)
        
        title = QLabel("SENTINEL")
        title_font = QFont()
        title_font.setPixelSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none; letter-spacing: 2px;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("AI")
        sub_font = QFont()
        sub_font.setPixelSize(13)
        subtitle.setFont(sub_font)
        subtitle.setStyleSheet(f"color: {Colors.TEXT_DIM}; background: transparent; border: none;")
        header_layout.addWidget(subtitle)
        
        header_layout.addStretch()
        
        # ── Chat controls (left-group) ──
        self._history_btn = self._make_header_btn("History", tooltip="Sohbet Geçmişi")
        self._history_btn.clicked.connect(self._show_history)
        header_layout.addWidget(self._history_btn)
        
        self._new_chat_btn = self._make_header_btn("+", tooltip="Yeni Sohbet", size=28, bold=True)
        self._new_chat_btn.clicked.connect(self._new_chat)
        header_layout.addWidget(self._new_chat_btn)
        
        # Separator
        header_layout.addWidget(self._make_separator())
        
        # ── Terminal controls ──
        self._new_terminal_btn = self._make_header_btn("+ Terminal", tooltip="Yeni Terminal")
        self._new_terminal_btn.clicked.connect(self._add_terminal)
        header_layout.addWidget(self._new_terminal_btn)
        
        # Separator
        header_layout.addWidget(self._make_separator())
        
        # ── Layout controls ──
        for icon, tip, preset in [("⇄", "Swap", "swap"), ("◧", "Terminal", "terminal"), ("◨", "Chat", "chat"), ("⊞", "50/50", "split")]:
            btn = self._make_header_btn(icon, tooltip=tip, size=28)
            if preset == "swap":
                btn.clicked.connect(self._swap_layout)
            else:
                btn.clicked.connect(lambda checked, p=preset: self._set_layout_preset(p))
            header_layout.addWidget(btn)
        
        # Separator
        header_layout.addWidget(self._make_separator())
        
        # Settings
        self._settings_btn = self._make_header_btn("⚙", tooltip="Ayarlar", size=28)
        self._settings_btn.clicked.connect(self._on_settings)
        header_layout.addWidget(self._settings_btn)
        
        main_layout.addWidget(header)
        
        # ── Content Splitter ────────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)
        
        # Chat (Left - 35%) - headerless
        self.chat_interface = ChatInterface()
        self.chat_interface.setMinimumWidth(300)
        self.splitter.addWidget(self.chat_interface)
        
        # Terminal (Right - 65%) - headerless
        self.terminal_view = TerminalView(self.process_manager)
        self.terminal_view.setMinimumWidth(350)
        self.splitter.addWidget(self.terminal_view)
        
        # 35% chat / 65% terminal
        self.splitter.setSizes([420, 780])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        
        main_layout.addWidget(self.splitter, stretch=1)
    
    def _make_header_btn(self, text, tooltip="", size=None, bold=False):
        """Create a consistent header button"""
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if size:
            btn.setFixedSize(size, 28)
        
        font = QFont()
        font.setPixelSize(12 if not size else 14)
        if bold:
            font.setBold(True)
        btn.setFont(font)
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_TERTIARY};
            }}
        """)
        return btn
    
    def _make_separator(self):
        """Create a vertical separator for the header"""
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        sep.setStyleSheet(f"background-color: {Colors.BG_ELEVATED}; border: none;")
        return sep
    
    def _connect_signals(self):
        # Chat -> Terminal
        self.chat_interface.command_requested.connect(self._execute_command)
        self.chat_interface.stop_requested.connect(self.terminal_view.stop_command)
        self.chat_interface.input_sent.connect(self.terminal_view.send_input)
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
    
    def _swap_layout(self):
        sizes = self.splitter.sizes()
        w0 = self.splitter.widget(0)
        w1 = self.splitter.widget(1)
        self.splitter.insertWidget(0, w1)
        self.splitter.insertWidget(1, w0)
        self.splitter.setSizes([sizes[1], sizes[0]])
        self._is_swapped = not self._is_swapped
    
    def _set_layout_preset(self, preset: str):
        total = sum(self.splitter.sizes())
        if preset == "terminal":
            self.splitter.setSizes([int(total * 0.15), int(total * 0.85)])
        elif preset == "chat":
            self.splitter.setSizes([int(total * 0.85), int(total * 0.15)])
        elif preset == "split":
            self.splitter.setSizes([int(total * 0.5), int(total * 0.5)])
    
    # ── Command Execution ──
    
    def _execute_command(self, command: str):
        cmd, args, requires_root = self.backend.parse_command(command)
        if not cmd:
            return
        self.terminal_view.start_command(cmd, args, requires_root)
        self.chat_interface.show_stop_button()
    
    def _execute_command_from_terminal(self, command: str):
        cmd, args, requires_root = self.backend.parse_command(command)
        if not cmd:
            return
        self.terminal_view.start_command(cmd, args, requires_root)
    
    def _handle_user_message(self, text: str):
        """Process user message with real AI orchestrator."""
        self.chat_interface.add_user_message(text)

        if self._ai_worker and self._ai_worker.isRunning():
            self.chat_interface.add_ai_message("Önceki AI isteği hâlâ işleniyor, lütfen birkaç saniye bekleyin.")
            return

        self._ai_worker = AIWorker(self.backend, text)
        self._ai_worker.result_ready.connect(self._on_ai_result)
        self._ai_worker.error_occurred.connect(self._on_ai_error)
        self._ai_worker.start()

    def _on_ai_result(self, response):
        command_text = None
        if getattr(response, "command", None):
            command = response.command
            command_text = f"{command.tool} {' '.join(command.arguments)}".strip()

        message = getattr(response, "message", None) or "AI yanıtı alınamadı."
        self.chat_interface.add_ai_message(message, command_text)

    def _on_ai_error(self, error: str):
        self.chat_interface.add_ai_message(f"AI hatası: {error}")
    
    # ── Event Handlers ──
    
    def _on_terminal_status(self, tab_name: str, is_running: bool, requires_root: bool):
        if is_running:
            self.chat_interface.show_stop_button()
        else:
            self.chat_interface.hide_action_buttons()
    
    def _on_prompt_detected(self, prompt_type: str):
        if prompt_type == "password":
            self.chat_interface.show_password_prompt()
        elif prompt_type == "yesno":
            self.chat_interface.show_yesno_prompt()
    
    def _on_process_finished(self, exit_code: int):
        self.chat_interface.hide_action_buttons()
    
    def _on_settings(self):
        dialog = SecuritySettingsDialog(
            self,
            cleanup_handler=self.backend.cleanup_old_sessions,
        )
        dialog.exec()
    
    def closeEvent(self, event):
        self.chat_interface.save_on_close()
        self.backend.shutdown()
        event.accept()
