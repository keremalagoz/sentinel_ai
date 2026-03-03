"""
SENTINEL AI - Chat Interface (Unified Design)
No sub-header, message identity, clean layout
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QFrame, QLabel, QScrollArea,
    QListWidget, QListWidgetItem, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from typing import List, Dict, Optional
from datetime import datetime
import json
import os

from src.ui.styles import Colors, Fonts, SCROLLBAR_MODERN

CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'temp', 'chat_history.json')


# ── Command Card ─────────────────────────────────────────

class CommandCard(QFrame):
    """Inline command card with Run/Copy actions"""
    
    run_clicked = pyqtSignal(str)
    copy_clicked = pyqtSignal(str)
    
    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self.command = command
        self._setup_ui()
    
    def _setup_ui(self):
        self.setObjectName("CommandCard")
        self.setStyleSheet(f"""
            QFrame#CommandCard {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 8px;
            }}
            QFrame#CommandCard:hover {{
                border: 1px solid {Colors.ACCENT_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        # Command text
        cmd_label = QLabel(self.command)
        cmd_font = QFont("JetBrains Mono, Consolas", 10)
        cmd_font.setPixelSize(12)
        cmd_label.setFont(cmd_font)
        cmd_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;")
        cmd_label.setWordWrap(True)
        cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(cmd_label)
        
        # Buttons container
        self._btn_widget = QWidget()
        btn_layout = QHBoxLayout(self._btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        
        self._run_btn = QPushButton("Run")
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
        """)
        self._run_btn.clicked.connect(self._on_run)
        btn_layout.addWidget(self._run_btn)
        
        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_TERTIARY};
            }}
        """)
        self._copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(self._copy_btn)
        
        btn_layout.addStretch()
        layout.addWidget(self._btn_widget)
    
    def _on_run(self):
        self.run_clicked.emit(self.command)
        self._btn_widget.hide()
    
    def _on_copy(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.command)
        self._btn_widget.hide()
        self.copy_clicked.emit(self.command)


# ── Chat Bubble ──────────────────────────────────────────

class ChatBubble(QFrame):
    """Chat message with identity label"""
    
    command_run = pyqtSignal(str)
    
    def __init__(self, message: str, is_user: bool, command: Optional[str] = None, timestamp: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._setup_ui(message, command, timestamp)
    
    def _setup_ui(self, message: str, command: Optional[str], timestamp: Optional[str]):
        self.setStyleSheet("background: transparent; border: none;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Identity label
        identity = QLabel()
        id_font = QFont()
        id_font.setPixelSize(11)
        id_font.setBold(True)
        identity.setFont(id_font)
        
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")
        
        if self.is_user:
            identity.setText(f"You · {timestamp}")
            identity.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; background: transparent; border: none;")
            identity.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            identity.setText(f"Sentinel · {timestamp}")
            identity.setStyleSheet(f"color: {Colors.SUCCESS}; background: transparent; border: none;")
            identity.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(identity)
        
        # Message bubble
        bubble = QFrame()
        if self.is_user:
            bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.ACCENT_PRIMARY};
                    border-radius: 12px;
                    border-top-right-radius: 4px;
                }}
            """)
        else:
            bubble.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_TERTIARY};
                    border-radius: 12px;
                    border-top-left-radius: 4px;
                }}
            """)
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(8)
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_font = QFont()
        msg_font.setPixelSize(13)
        msg_label.setFont(msg_font)
        
        if self.is_user:
            msg_label.setStyleSheet("color: white; background: transparent; border: none;")
        else:
            msg_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;")
        
        bubble_layout.addWidget(msg_label)
        
        # Command card (AI only)
        if command and not self.is_user:
            cmd_card = CommandCard(command)
            cmd_card.run_clicked.connect(self.command_run.emit)
            bubble_layout.addWidget(cmd_card)
        
        layout.addWidget(bubble)


# ── Action Buttons ───────────────────────────────────────

class ActionButtons(QFrame):
    """Dynamic action buttons (yes/no, password)"""
    
    yes_clicked = pyqtSignal()
    no_clicked = pyqtSignal()
    password_submitted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; border: none;")
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 4, 12, 4)
        self._layout.setSpacing(8)
        self.setFixedHeight(36)
        self.setStyleSheet(f"background-color: {Colors.BG_PRIMARY}; border: none;")
        
        self._yes_btn = QPushButton("Yes")
        self._yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._yes_btn.setFixedHeight(28)
        self._yes_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white; border: none;
                border-radius: 14px; padding: 4px 16px; font-weight: bold; font-size: 11px;
            }}
        """)
        self._yes_btn.clicked.connect(self.yes_clicked.emit)
        self._layout.addWidget(self._yes_btn)
        self._yes_btn.hide()
        
        self._no_btn = QPushButton("No")
        self._no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._no_btn.setFixedHeight(28)
        self._no_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY}; border: none;
                border-radius: 14px; padding: 4px 16px; font-size: 11px;
            }}
        """)
        self._no_btn.clicked.connect(self.no_clicked.emit)
        self._layout.addWidget(self._no_btn)
        self._no_btn.hide()
        
        from PyQt6.QtWidgets import QLineEdit
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Enter password...")
        self._password_input.setFixedHeight(28)
        self._password_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 14px; padding: 4px 12px;
            }}
        """)
        self._password_input.returnPressed.connect(self._submit_password)
        self._layout.addWidget(self._password_input)
        self._password_input.hide()
        
        self._layout.addStretch()
    
    def show_yesno(self):
        self._hide_all(); self._yes_btn.show(); self._no_btn.show(); self.show()
    
    def show_password(self):
        self._hide_all(); self._password_input.show(); self._password_input.setFocus(); self.show()
    
    def hide_all(self):
        self._hide_all(); self.hide()
    
    def _hide_all(self):
        self._yes_btn.hide(); self._no_btn.hide()
        self._password_input.hide(); self._password_input.clear()
    
    def _submit_password(self):
        password = self._password_input.text()
        if password:
            self.password_submitted.emit(password)
            self._password_input.clear()
            self.hide_all()


# ── History Dialog ───────────────────────────────────────

class HistoryDialog(QDialog):
    """Professional chat history dialog with better visual hierarchy"""
    
    chat_selected = pyqtSignal(str)
    
    def __init__(self, history: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sohbet Gecmisi")
        self.setFixedSize(420, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        self._setup_ui(history)
    
    def _setup_ui(self, history: List[Dict]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Sohbet Gecmisi")
        t_font = QFont()
        t_font.setPixelSize(16)
        t_font.setBold(True)
        title.setFont(t_font)
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()
        
        count_label = QLabel(f"{len(history)} sohbet")
        count_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 11px;")
        header.addWidget(count_label)
        layout.addLayout(header)
        
        # List
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px 14px;
                color: {Colors.TEXT_PRIMARY};
                border-bottom: 1px solid {Colors.BG_ELEVATED};
                border-radius: 0;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.BG_TERTIARY};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.ACCENT_SUBTLE};
                color: {Colors.ACCENT_PRIMARY};
                border-left: 3px solid {Colors.ACCENT_PRIMARY};
            }}
        """)
        
        for chat in history:
            chat_title = chat.get('title', 'Untitled')
            chat_date = chat.get('date', '')
            # Truncate long titles
            if len(chat_title) > 35:
                chat_title = chat_title[:32] + '...'
            item = QListWidgetItem(f"{chat_title}\n{chat_date}")
            item.setData(Qt.ItemDataRole.UserRole, chat.get('id'))
            item_font = QFont()
            item_font.setPixelSize(12)
            item.setFont(item_font)
            self._list.addItem(item)
        
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list, stretch=1)
        
        # Footer buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("Kapat")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 6px;
                padding: 6px 24px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def _on_select(self, item):
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        self.chat_selected.emit(chat_id)
        self.close()


# ── Auto-Expand Input ────────────────────────────────────

class AutoExpandTextEdit(QTextEdit):
    """Text edit that auto-expands vertically with message history"""
    
    returnPressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._adjust_height)
        self._min_height = 36
        self._max_height = 120
        self.setFixedHeight(self._min_height)
        self._msg_history: List[str] = []
        self._history_index = 0
    
    def add_to_history(self, text: str):
        if text and (not self._msg_history or self._msg_history[-1] != text):
            self._msg_history.append(text)
        self._history_index = 0
    
    def _adjust_height(self):
        doc_height = self.document().size().height()
        new_height = max(self._min_height, min(int(doc_height) + 8, self._max_height))
        self.setFixedHeight(new_height)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers():
            self.returnPressed.emit()
        elif event.key() == Qt.Key.Key_Up and not self.toPlainText().strip():
            self._history_up()
        elif event.key() == Qt.Key.Key_Up and self._history_index > 0:
            self._history_up()
        elif event.key() == Qt.Key.Key_Down and self._history_index > 0:
            self._history_down()
        else:
            super().keyPressEvent(event)
    
    def _history_up(self):
        if not self._msg_history:
            return
        if self._history_index < len(self._msg_history):
            self._history_index += 1
            self.setPlainText(self._msg_history[-self._history_index])
    
    def _history_down(self):
        if self._history_index > 1:
            self._history_index -= 1
            self.setPlainText(self._msg_history[-self._history_index])
        elif self._history_index == 1:
            self._history_index = 0
            self.clear()


# ── Main Chat Interface ─────────────────────────────────

class ChatInterface(QWidget):
    """
    SENTINEL Chat Interface - Headerless Design
    
    Header controls moved to main_window unified header.
    This widget only contains: messages area + action buttons + input.
    """
    
    message_sent = pyqtSignal(str)
    command_requested = pyqtSignal(str)
    stop_requested = pyqtSignal()
    input_sent = pyqtSignal(str)
    action_response = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_chat_id = None
        self._messages: List[Dict] = []
        self._command_running = False
        self.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        self._setup_ui()
        self._load_or_create_chat()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ── Section label (subtle) ──
        section_bar = QFrame()
        section_bar.setFixedHeight(28)
        section_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BG_ELEVATED};
            }}
        """)
        section_layout = QHBoxLayout(section_bar)
        section_layout.setContentsMargins(12, 0, 12, 0)
        
        section_label = QLabel("Chat")
        sl_font = QFont()
        sl_font.setPixelSize(11)
        section_label.setFont(sl_font)
        section_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; background: transparent; border: none;")
        section_layout.addWidget(section_label)
        section_layout.addStretch()
        
        layout.addWidget(section_bar)
        
        # ── Scroll area for messages ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
        """ + SCROLLBAR_MODERN)
        
        self._messages_container = QWidget()
        self._messages_container.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._messages_layout.setSpacing(16)
        self._messages_layout.addStretch()
        
        scroll.setWidget(self._messages_container)
        layout.addWidget(scroll, stretch=1)
        
        self._scroll = scroll
        
        # ── Action buttons ──
        self._action_buttons = ActionButtons()
        self._action_buttons.yes_clicked.connect(lambda: self.action_response.emit("y"))
        self._action_buttons.no_clicked.connect(lambda: self.action_response.emit("n"))
        self._action_buttons.password_submitted.connect(self.input_sent.emit)
        layout.addWidget(self._action_buttons)
        
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
        input_layout.setSpacing(8)
        
        self._input = AutoExpandTextEdit()
        self._input.setPlaceholderText("Ask Sentinel...")
        input_font = QFont()
        input_font.setPixelSize(13)
        self._input.setFont(input_font)
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 18px;
                padding: 8px 16px;
            }}
            QTextEdit:focus {{
                border: 1px solid {Colors.ACCENT_PRIMARY};
            }}
        """)
        self._input.returnPressed.connect(self._on_send)
        input_layout.addWidget(self._input, stretch=1)
        
        # Send Button
        self._send_btn = QPushButton("->")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setFixedSize(34, 34)
        send_font = QFont()
        send_font.setPixelSize(13)
        send_font.setBold(True)
        self._send_btn.setFont(send_font)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 17px;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: #1d4ed8; }}
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self._send_btn)
        
        layout.addWidget(input_frame)
    
    # ── Send ──
    
    def _on_send(self):
        text = self._input.toPlainText().strip()
        if text:
            self._input.add_to_history(text)
            self._input.clear()
            self.message_sent.emit(text)
    
    # ── Chat Management ──
    
    def _load_or_create_chat(self):
        """Always start fresh on launch"""
        self._new_chat()
    
    def _new_chat(self):
        if self._current_chat_id and self._messages:
            self._save_current_chat()
        self._current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._messages = []
        self.clear_chat()
    
    def _save_current_chat(self):
        if not self._current_chat_id:
            return
        if not self._messages:
            return
        history = self._load_history()
        found = False
        for i, chat in enumerate(history):
            if chat.get('id') == self._current_chat_id:
                history[i]['messages'] = self._messages
                history[i]['title'] = self._get_chat_title()
                found = True
                break
        if not found:
            history.append({
                'id': self._current_chat_id,
                'title': self._get_chat_title(),
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'messages': self._messages
            })
        self._save_history(history)
    
    def _get_chat_title(self) -> str:
        for msg in self._messages:
            if msg.get('is_user'):
                return msg.get('text', 'Untitled')[:30]
        return "Untitled"
    
    def _load_history(self) -> List[Dict]:
        try:
            os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
            if os.path.exists(CHAT_HISTORY_FILE):
                with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load chat history: {e}")
        return []
    
    def _save_history(self, history: List[Dict]):
        try:
            os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
            with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save chat history: {e}")
    
    def _show_history(self):
        history = self._load_history()
        dialog = HistoryDialog(history, self)
        dialog.chat_selected.connect(self._load_chat)
        dialog.exec()
    
    def _load_chat(self, chat_id: str):
        if self._current_chat_id and self._messages:
            self._save_current_chat()
        history = self._load_history()
        for chat in history:
            if chat.get('id') == chat_id:
                self._current_chat_id = chat_id
                self._messages = chat.get('messages', [])
                self._render_messages()
                break
    
    def _render_messages(self):
        self.clear_chat()
        for msg in self._messages:
            if msg.get('is_user'):
                self._add_bubble(msg['text'], is_user=True, timestamp=msg.get('timestamp'))
            else:
                self._add_bubble(msg['text'], is_user=False, command=msg.get('command'), timestamp=msg.get('timestamp'))
    
    # ── Bubble Management ──
    
    def _add_bubble(self, message: str, is_user: bool, command: Optional[str] = None, timestamp: Optional[str] = None):
        bubble_container = QWidget()
        container_layout = QHBoxLayout(bubble_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        if is_user:
            container_layout.addStretch()
        
        bubble = ChatBubble(message, is_user=is_user, command=command, timestamp=timestamp)
        bubble.setMaximumWidth(380)
        if not is_user:
            bubble.command_run.connect(self.command_requested.emit)
        
        container_layout.addWidget(bubble)
        
        if not is_user:
            container_layout.addStretch()
        
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, bubble_container)
        self._scroll_to_bottom()
    
    def add_user_message(self, message: str, correlation_id: Optional[str] = None):
        timestamp = datetime.now().strftime("%H:%M")
        item = {'text': message, 'is_user': True, 'timestamp': timestamp}
        if correlation_id:
            item['correlation_id'] = correlation_id
        self._messages.append(item)
        self._add_bubble(message, is_user=True, timestamp=timestamp)
        self._save_current_chat()
    
    def add_ai_message(
        self,
        message: str,
        command: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        timestamp = datetime.now().strftime("%H:%M")
        item = {'text': message, 'is_user': False, 'command': command, 'timestamp': timestamp}
        if correlation_id:
            item['correlation_id'] = correlation_id
        self._messages.append(item)
        self._add_bubble(message, is_user=False, command=command, timestamp=timestamp)
        self._save_current_chat()
    
    def show_stop_button(self):
        self._command_running = True
        self._action_buttons.hide_all()
    
    def show_yesno_prompt(self):
        self._action_buttons.show_yesno()
    
    def show_password_prompt(self):
        self._action_buttons.show_password()
    
    def hide_action_buttons(self):
        self._command_running = False
        self._action_buttons.hide_all()
    
    def clear_chat(self):
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def keep_scroll_position(self):
        bar = self._scroll.verticalScrollBar()
        current_value = bar.value()
        QTimer.singleShot(0, lambda v=current_value: bar.setValue(min(v, bar.maximum())))
    
    def save_on_close(self):
        self._save_current_chat()
