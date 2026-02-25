"""
SENTINEL AI - Main Window (VS Code Style)
Agent Manager header with layout controls
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from src.ui.styles import Colors, Fonts, GLOBAL_STYLE
from src.ui.terminal_view import TerminalView
from src.ui.chat_interface import ChatInterface
from src.ui.settings_dialog import SecuritySettingsDialog
from src.core.process_manager import AdvancedProcessManager


class MainWindow(QMainWindow):
    """
    SENTINEL AI Main Window - VS Code Style
    
    Features:
    - Agent Manager header
    - Layout controls (swap, presets)
    - Terminal + Chat splitter
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTINEL AI")
        self.setMinimumSize(1200, 700)
        
        # Initialize process manager
        self.process_manager = AdvancedProcessManager()
        
        # Track layout state
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
        
        # Header - Agent Manager
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-bottom: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        header.setFixedHeight(40)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)
        
        # Agent Manager title
        title = QLabel("Agent Manager")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 13px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Layout controls
        # Swap button (Terminal <-> Chat)
        self._swap_btn = QPushButton("⇄")
        self._swap_btn.setToolTip("Swap Terminal/Chat")
        self._swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._swap_btn.setFixedSize(28, 28)
        self._swap_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT_PRIMARY};
                border-color: {Colors.ACCENT_PRIMARY};
                background-color: {Colors.ACCENT_SUBTLE};
            }}
        """)
        self._swap_btn.clicked.connect(self._swap_layout)
        header_layout.addWidget(self._swap_btn)
        
        # Layout preset: Full Terminal
        self._full_terminal_btn = QPushButton("▣")
        self._full_terminal_btn.setToolTip("Full Terminal")
        self._full_terminal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._full_terminal_btn.setFixedSize(28, 28)
        self._full_terminal_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT_PRIMARY};
                border-color: {Colors.ACCENT_PRIMARY};
                background-color: {Colors.ACCENT_SUBTLE};
            }}
        """)
        self._full_terminal_btn.clicked.connect(lambda: self._set_layout_preset("terminal"))
        header_layout.addWidget(self._full_terminal_btn)
        
        # Layout preset: Full Chat
        self._full_chat_btn = QPushButton("▢")
        self._full_chat_btn.setToolTip("Full Chat")
        self._full_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._full_chat_btn.setFixedSize(28, 28)
        self._full_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT_PRIMARY};
                border-color: {Colors.ACCENT_PRIMARY};
                background-color: {Colors.ACCENT_SUBTLE};
            }}
        """)
        self._full_chat_btn.clicked.connect(lambda: self._set_layout_preset("chat"))
        header_layout.addWidget(self._full_chat_btn)
        
        # Layout preset: Split 50/50
        self._split_btn = QPushButton("⊞")
        self._split_btn.setToolTip("Split 50/50")
        self._split_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._split_btn.setFixedSize(28, 28)
        self._split_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT_PRIMARY};
                border-color: {Colors.ACCENT_PRIMARY};
                background-color: {Colors.ACCENT_SUBTLE};
            }}
        """)
        self._split_btn.clicked.connect(lambda: self._set_layout_preset("split"))
        header_layout.addWidget(self._split_btn)
        
        # Separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet(f"background-color: {Colors.BG_ELEVATED};")
        header_layout.addWidget(sep)
        
        # Settings button
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setFixedSize(28, 28)
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_TERTIARY};
            }}
        """)
        self._settings_btn.clicked.connect(self._on_settings)
        header_layout.addWidget(self._settings_btn)
        
        main_layout.addWidget(header)
        
        # Content Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)
        
        # Terminal (Left - 65%)
        self.terminal_view = TerminalView(self.process_manager)
        self.terminal_view.setMinimumWidth(300)
        self.splitter.addWidget(self.terminal_view)
        
        # Chat (Right - 35%)
        self.chat_interface = ChatInterface()
        self.chat_interface.setMinimumWidth(280)
        self.splitter.addWidget(self.chat_interface)
        
        # Set initial sizes (65% / 35%)
        self.splitter.setSizes([780, 420])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        
        main_layout.addWidget(self.splitter, stretch=1)
    
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
    
    def _swap_layout(self):
        """Swap terminal and chat positions"""
        sizes = self.splitter.sizes()
        
        # Remove widgets
        self.splitter.widget(0).setParent(None)
        self.splitter.widget(0).setParent(None)
        
        if self._is_swapped:
            # Back to normal: Terminal | Chat
            self.splitter.addWidget(self.terminal_view)
            self.splitter.addWidget(self.chat_interface)
        else:
            # Swapped: Chat | Terminal
            self.splitter.addWidget(self.chat_interface)
            self.splitter.addWidget(self.terminal_view)
        
        # Reverse sizes
        self.splitter.setSizes([sizes[1], sizes[0]])
        self._is_swapped = not self._is_swapped
    
    def _set_layout_preset(self, preset: str):
        """Set layout preset"""
        total = sum(self.splitter.sizes())
        if preset == "terminal":
            self.splitter.setSizes([int(total * 0.85), int(total * 0.15)])
        elif preset == "chat":
            self.splitter.setSizes([int(total * 0.15), int(total * 0.85)])
        elif preset == "split":
            self.splitter.setSizes([int(total * 0.5), int(total * 0.5)])
    
    def _execute_command(self, command: str):
        """Execute command from chat"""
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        requires_root = any(x in command for x in ['sudo', '-sS', '-sU', '--privileged'])
        
        self.terminal_view.start_command(cmd, args, requires_root)
        self.chat_interface.show_stop_button()
    
    def _execute_command_from_terminal(self, command: str):
        """Execute command typed directly in terminal"""
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        requires_root = any(x in command for x in ['sudo', '-sS', '-sU', '--privileged'])
        
        self.terminal_view.start_command(cmd, args, requires_root)
        self.chat_interface.show_stop_button()
    
    def _handle_user_message(self, text: str):
        """Process user message - MOCK AI for now"""
        self.chat_interface.add_user_message(text)
        
        # Simulate AI thinking
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
    
    def _on_terminal_status(self, tab_name: str, is_running: bool, requires_root: bool):
        """Handle terminal status changes"""
        if is_running:
            self.chat_interface.show_stop_button()
        else:
            self.chat_interface.hide_action_buttons()
    
    def _on_prompt_detected(self, prompt_type: str):
        """Handle interactive prompts"""
        if prompt_type == "password":
            self.chat_interface.show_password_prompt()
        elif prompt_type == "yesno":
            self.chat_interface.show_yesno_prompt()
    
    def _on_process_finished(self, exit_code: int):
        """Handle process completion"""
        self.chat_interface.hide_action_buttons()
    
    def _on_settings(self):
        """Open settings dialog"""
        dialog = SecuritySettingsDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        """Save state before closing"""
        self.chat_interface.save_on_close()
        
        # Stop any running processes
        self.process_manager.stop_process()
        
        event.accept()
