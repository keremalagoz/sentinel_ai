"""
SENTINEL AI - Main Window (Unified Design)
Single header, cohesive layout
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from src.ui.styles import Colors, Fonts, GLOBAL_STYLE
from src.ui.terminal_view import TerminalView
from src.ui.chat_interface import ChatInterface
from src.ui.settings_dialog import SecuritySettingsDialog
from src.core.process_manager import AdvancedProcessManager


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
        
        self.process_manager = AdvancedProcessManager()
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
        parts = command.split()
        if not parts:
            return
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        requires_root = any(x in command for x in ['sudo', '-sS', '-sU', '--privileged'])
        self.terminal_view.start_command(cmd, args, requires_root)
        self.chat_interface.show_stop_button()
    
    def _execute_command_from_terminal(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        requires_root = any(x in command for x in ['sudo', '-sS', '-sU', '--privileged'])
        self.terminal_view.start_command(cmd, args, requires_root)
    
    def _handle_user_message(self, text: str):
        """Process user message - MOCK AI for now"""
        self.chat_interface.add_user_message(text)
        QTimer.singleShot(500, lambda: self._generate_mock_response(text))
    
    def _generate_mock_response(self, user_text: str):
        """Generate mock AI response"""
        text_lower = user_text.lower()
        response = "I can help you with security testing. Try asking me to scan a network or check a target."
        command = None
        
        if "scan" in text_lower and "network" in text_lower:
            response = "Here is a ping sweep command to discover hosts on your local network:"
            command = "nmap -sn 192.168.1.0/24"
        elif "port" in text_lower and "scan" in text_lower:
            response = "Running a port scan on the target. This may take a moment."
            command = "nmap -sT -T4 192.168.1.1"
        elif "nmap" in text_lower:
            response = "Running a port scan on the target. This may take a moment."
            command = "nmap -sT -T4 192.168.1.1"
        elif "ping" in text_lower:
            response = "Here's a ping command to test connectivity:"
            command = "ping -n 4 google.com" if sys.platform == "win32" else "ping -c 4 google.com"
        elif "ip" in text_lower or "network" in text_lower:
            response = "Checking network configuration:"
            command = "ipconfig" if sys.platform == "win32" else "ip addr"
        elif any(x in text_lower for x in ['merhaba', 'hello', 'hi', 'selam']):
            response = "Hello! I'm Sentinel AI, your security testing assistant. What would you like to analyze today?"
        else:
            response = "I can help you with: network scanning, port analysis, vulnerability detection, and more. Just describe what you want to do!"
        
        self.chat_interface.add_ai_message(response, command)
    
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
        dialog = SecuritySettingsDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        self.chat_interface.save_on_close()
        self.process_manager.stop_process()
        event.accept()
