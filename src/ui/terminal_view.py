"""
SENTINEL AI - Terminal View (Unified Design)
No sub-header, section label only, clean layout
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QFrame, QLabel, QStackedWidget, QLineEdit,
    QTabBar, QMenu
)
from PyQt6.QtCore import pyqtSlot, pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QTextCursor, QFont, QAction
from typing import List, Optional, Set

from src.ui.styles import Colors, Fonts, TERMINAL_THEME, SCROLLBAR_MODERN


class TerminalSession:
    """Single terminal session data"""
    def __init__(self, session_id: int):
        self.id = session_id
        self.name = f"Terminal {session_id}"
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(TERMINAL_THEME + SCROLLBAR_MODERN)
        font = QFont("JetBrains Mono, Fira Code, Consolas", 10)
        font.setPixelSize(13)
        self.output.setFont(font)
        self.is_running = False
        self.requires_root = False


class TerminalView(QWidget):
    """
    SENTINEL Terminal - Headerless Design
    
    Header controls moved to main_window unified header.
    This widget only contains: section label + output + sidebar + input.
    """
    
    sig_status_changed = pyqtSignal(str, bool, bool)
    sig_prompt_detected = pyqtSignal(str)
    sig_process_finished = pyqtSignal(int)
    sig_command_submitted = pyqtSignal(str)
    
    def __init__(self, process_manager=None, parent=None):
        super().__init__(parent)
        self._manager = process_manager
        self._sessions: List[TerminalSession] = []
        self._active_session: Optional[TerminalSession] = None
        self._max_buffer_lines = 10000
        self._used_ids: Set[int] = set()
        self._command_history: List[str] = []
        self._history_index = 0
        
        self.setStyleSheet(f"background-color: {Colors.BG_PRIMARY};")
        self._setup_ui()
        self._connect_manager_signals()
        
        # Create initial terminal
        self._add_terminal()
    
    def _get_next_id(self) -> int:
        i = 1
        while i in self._used_ids:
            i += 1
        self._used_ids.add(i)
        return i
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ── Section label bar (subtle, matching chat) ──
        section_bar = QFrame()
        section_bar.setFixedHeight(28)
        section_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-bottom: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        section_layout = QHBoxLayout(section_bar)
        section_layout.setContentsMargins(12, 0, 12, 0)
        
        section_label = QLabel("Terminal")
        sl_font = QFont()
        sl_font.setPixelSize(11)
        section_label.setFont(sl_font)
        section_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; background: transparent; border: none;")
        section_layout.addWidget(section_label)
        
        section_layout.addStretch()
        
        layout.addWidget(section_bar)
        
        # ── Tabs Area ──
        tab_container = QFrame()
        tab_container.setFixedHeight(30)
        tab_container.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border-bottom: 1px solid {Colors.BG_ELEVATED};")
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        
        self._tab_bar = QTabBar()
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setSelectionBehaviorOnRemove(QTabBar.SelectionBehavior.SelectPreviousTab)
        self._tab_bar.setStyleSheet(f"""
            QTabBar::tab {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_SECONDARY};
                border: none;
                border-right: 1px solid {Colors.BG_ELEVATED};
                padding: 6px 16px;
                min-width: 80px;
                font-family: {Fonts.UI};
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border-top: 2px solid {Colors.ACCENT_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background: {Colors.BG_ELEVATED};
            }}
        """)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        self._tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        tab_layout.addWidget(self._tab_bar)

        tab_layout.addStretch()
        
        layout.addWidget(tab_container)
        
        # ── Content area ──
        self._output_stack = QStackedWidget()
        layout.addWidget(self._output_stack, stretch=1)
        
        # ── Input area ──
        # ── Input area (redesigned) ──
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border-top: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        input_frame.setFixedHeight(52)
        
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(12)
        
        # Prompt icon
        self._prompt_icon = QLabel("❯")
        prompt_font = QFont("JetBrains Mono, Consolas", 10)
        prompt_font.setPixelSize(16)
        prompt_font.setBold(True)
        self._prompt_icon.setFont(prompt_font)
        self._prompt_icon.setStyleSheet(f"color: {Colors.SUCCESS}; background: transparent; border: none; padding-left: 4px;")
        input_layout.addWidget(self._prompt_icon)
        
        # Input field
        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter command...")
        input_font = QFont("JetBrains Mono, Consolas", 10)
        input_font.setPixelSize(13)
        self._input.setFont(input_font)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 18px;
                padding: 8px 16px;
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.ACCENT_PRIMARY};
            }}
        """)
        self._input.returnPressed.connect(self._on_input_submit)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input, stretch=1)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setFixedHeight(32)
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #dc2626;
            }}
        """)
        self._stop_btn.clicked.connect(self.stop_command)
        self._stop_btn.hide()
        input_layout.addWidget(self._stop_btn)
        
        layout.addWidget(input_frame)
    
    def eventFilter(self, obj, event):
        if obj == self._input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._history_up()
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._history_down()
                return True
        return super().eventFilter(obj, event)
    
    def _history_up(self):
        if not self._command_history:
            return
        if self._history_index < len(self._command_history):
            self._history_index += 1
            self._input.setText(self._command_history[-self._history_index])
    
    def _history_down(self):
        if self._history_index > 1:
            self._history_index -= 1
            self._input.setText(self._command_history[-self._history_index])
        elif self._history_index == 1:
            self._history_index = 0
            self._input.clear()
    
    def _on_input_submit(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._history_index = 0
        if self._active_session and self._active_session.is_running:
            self.send_input(text)
        else:
            self._command_history.append(text)
            self.sig_command_submitted.emit(text)
    
    def _add_terminal(self) -> TerminalSession:
        session_id = self._get_next_id()
        session = TerminalSession(session_id)
        self._sessions.append(session)
        self._output_stack.addWidget(session.output)
        
        tab_index = self._tab_bar.addTab(session.name)
        self._tab_bar.setTabData(tab_index, session.id)
        
        self._switch_terminal(session)
        return session
    
    def _close_terminal(self, session: TerminalSession):
        if len(self._sessions) <= 1:
            return
        if session.is_running and session == self._active_session and self._manager:
            self._manager.stop_process()
        
        for i in range(self._tab_bar.count()):
            if self._tab_bar.tabData(i) == session.id:
                self._tab_bar.removeTab(i)
                break
        
        self._output_stack.removeWidget(session.output)
        session.output.deleteLater()
        self._sessions.remove(session)
        self._used_ids.discard(session.id)
        
        if self._active_session == session and self._sessions:
            self._switch_terminal(self._sessions[-1])
    
    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        session_id = self._tab_bar.tabData(index)
        session = next((s for s in self._sessions if s.id == session_id), None)
        if session:
            self._switch_terminal(session)
            
    def _on_tab_close_requested(self, index: int):
        if index < 0:
            return
        session_id = self._tab_bar.tabData(index)
        session = next((s for s in self._sessions if s.id == session_id), None)
        if session:
            self._close_terminal(session)
    
    def _switch_terminal(self, session: TerminalSession):
        self._active_session = session
        self._output_stack.setCurrentWidget(session.output)
        
        for i in range(self._tab_bar.count()):
            if self._tab_bar.tabData(i) == session.id:
                if self._tab_bar.currentIndex() != i:
                    self._tab_bar.setCurrentIndex(i)
                break
        
        self._update_tab_indicators()
        self._update_status_badge()
    
    def _update_status_badge(self):
        if not self._active_session:
            self._stop_btn.hide()
            return
        if self._active_session.is_running:
            self._stop_btn.show()
            if self._active_session.requires_root:
                self._prompt_icon.setStyleSheet(f"color: {Colors.DANGER}; background: transparent; border: none;")
            else:
                self._prompt_icon.setStyleSheet(f"color: {Colors.WARNING}; background: transparent; border: none;")
        else:
            self._stop_btn.hide()
            self._prompt_icon.setStyleSheet(f"color: {Colors.SUCCESS}; background: transparent; border: none;")
    
    def _update_status(self):
        self._update_tab_indicators()
        self._update_status_badge()
        if self._active_session:
            self.sig_status_changed.emit(
                self._active_session.name,
                self._active_session.is_running,
                self._active_session.requires_root
            )
    
    def _update_tab_indicators(self):
        for i in range(self._tab_bar.count()):
            session_id = self._tab_bar.tabData(i)
            session = next((s for s in self._sessions if s.id == session_id), None)
            if session:
                prefix = "● " if session.is_running else ""
                self._tab_bar.setTabText(i, f"{prefix}{session.name}")
    
    def _connect_manager_signals(self):
        if self._manager:
            self._manager.sig_output_stream.connect(self._on_output)
            self._manager.sig_process_finished.connect(self._on_finished)
            self._manager.sig_auth_failed.connect(self._on_auth_failed)
    
    # ── Public API ──
    
    def start_command(
        self,
        command: str,
        args: list,
        requires_root: bool = False,
        correlation_id: str = "",
        risk_label: str = "",
    ):
        if not self._manager or not self._active_session:
            return
        self._active_session.is_running = True
        self._active_session.requires_root = requires_root
        self._update_status()
        if correlation_id:
            self._log(f"[CID:{correlation_id}]", Colors.TEXT_DIM)
        if risk_label:
            self._log(f"[RISK] {risk_label.upper()}", Colors.WARNING if risk_label.lower() != "safe" else Colors.SUCCESS)
        self._log(f"$ {command} {' '.join(args)}", Colors.TEXT_SECONDARY)
        if requires_root:
            self._log("[!] ROOT: Yuksek yetki ile calistiriliyor", Colors.WARNING)
        self._manager.start_process(command, args, requires_root, correlation_id=correlation_id)
    
    def stop_command(self):
        if self._manager:
            self._manager.stop_process()
            self._log("[X] Process terminated by user", Colors.DANGER)
            if self._active_session:
                self._active_session.is_running = False
                self._active_session.requires_root = False
                self._update_status()
    
    def send_input(self, text: str):
        if self._manager:
            self._manager.write_input(text)
            if "password" not in text.lower():
                self._log(f"> {text}", Colors.ACCENT_PRIMARY)
    
    def get_active_session_name(self) -> str:
        return self._active_session.name if self._active_session else "Terminal"
    
    # ── Internal ──
    
    def _log(self, text: str, color: str):
        if not self._active_session:
            return
        output = self._active_session.output
        cursor = output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if output.toPlainText():
            cursor.insertHtml("<br>")
        escaped = self._escape(text)
        cursor.insertHtml(f"<span style='color: {color};'>{escaped}</span>")
        output.setTextCursor(cursor)
        output.ensureCursorVisible()
    
    @pyqtSlot(str, str)
    def _on_output(self, text: str, channel: str):
        if not self._active_session:
            return
        color = Colors.DANGER if channel == "stderr" else Colors.TEXT_PRIMARY
        output = self._active_session.output
        cursor = output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f"<span style='color: {color};'>{self._escape(text)}</span>")
        output.setTextCursor(cursor)
        output.ensureCursorVisible()
        self._detect_prompt(text)
        self._check_buffer_limit(output)
    
    def _detect_prompt(self, text: str):
        from src.ui.styles import InteractivePatterns
        if InteractivePatterns.is_password_prompt(text):
            self.sig_prompt_detected.emit("password")
        elif InteractivePatterns.is_yesno_prompt(text):
            self.sig_prompt_detected.emit("yesno")
    
    def _check_buffer_limit(self, output: QTextEdit):
        doc = output.document()
        if doc.lineCount() > self._max_buffer_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(1000):
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
                if cursor.atEnd():
                    break
                cursor.deleteChar()
    
    @pyqtSlot(int, str)
    def _on_finished(self, exit_code: int, log_path: str):
        if self._active_session:
            self._active_session.is_running = False
            self._active_session.requires_root = False
            self._update_status()
            if exit_code == 0:
                self._log("[OK] Completed", Colors.SUCCESS)
            else:
                self._log(f"[X] Exit code {exit_code}", Colors.DANGER)
        self.sig_process_finished.emit(exit_code)
    
    @pyqtSlot()
    def _on_auth_failed(self):
        if self._active_session:
            self._active_session.is_running = False
            self._active_session.requires_root = False
            self._update_status()
            self._log("[!] Authentication failed or cancelled", Colors.WARNING)
    
    @staticmethod
    def _escape(text: str) -> str:
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
            .replace(" ", "&nbsp;"))
