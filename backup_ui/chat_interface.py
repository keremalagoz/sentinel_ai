"""
SENTINEL AI - Chat Interface (VS Code Style)
History support, auto-expand input, JSON persistence
"""

import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QTextEdit, QPushButton, QFrame, QLabel,
    QSizePolicy, QMenu, QListWidget, QListWidgetItem, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont
from typing import Optional, List, Dict

from src.ui.styles import Colors, Fonts


# Chat history file path
CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "temp", "chat_history.json")


class CommandCard(QFrame):
    """Command display with Run/Copy buttons"""
    
    run_clicked = pyqtSignal(str)
    copy_clicked = pyqtSignal(str)
    
    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self.command = command
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        # Command text
        cmd_label = QLabel(self.command)
        cmd_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.MONO};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
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


class ChatBubble(QFrame):
    """Chat message bubble"""
    
    command_run = pyqtSignal(str)
    
    def __init__(self, message: str, is_user: bool, command: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._setup_ui(message, command)
    
    def _setup_ui(self, message: str, command: Optional[str]):
        if self.is_user:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.ACCENT_PRIMARY};
                    border-radius: 12px;
                    border-top-right-radius: 4px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BG_TERTIARY};
                    border-radius: 12px;
                    border-top-left-radius: 4px;
                }}
            """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Message text
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if self.is_user:
            msg_label.setStyleSheet(f"color: white; background: transparent; border: none;")
        else:
            msg_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;")
        layout.addWidget(msg_label)
        
        # Command card (AI only)
        if command and not self.is_user:
            cmd_card = CommandCard(command)
            cmd_card.run_clicked.connect(self.command_run.emit)
            layout.addWidget(cmd_card)


class ActionButtons(QFrame):
    """Dynamic action buttons area"""
    
    stop_clicked = pyqtSignal()
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
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(8)
        
        # Stop button
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #dc2626; }}
        """)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self._layout.addWidget(self._stop_btn)
        self._stop_btn.hide()
        
        # Yes/No buttons
        self._yes_btn = QPushButton("Yes")
        self._yes_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }}
        """)
        self._yes_btn.clicked.connect(self.yes_clicked.emit)
        self._layout.addWidget(self._yes_btn)
        self._yes_btn.hide()
        
        self._no_btn = QPushButton("No")
        self._no_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }}
        """)
        self._no_btn.clicked.connect(self.no_clicked.emit)
        self._layout.addWidget(self._no_btn)
        self._no_btn.hide()
        
        # Password input
        from PyQt6.QtWidgets import QLineEdit
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Enter password...")
        self._password_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        self._password_input.returnPressed.connect(self._submit_password)
        self._layout.addWidget(self._password_input)
        self._password_input.hide()
        
        self._layout.addStretch()
    
    def show_stop(self):
        self._hide_all()
        self._stop_btn.show()
        self.show()
    
    def show_yesno(self):
        self._hide_all()
        self._yes_btn.show()
        self._no_btn.show()
        self.show()
    
    def show_password(self):
        self._hide_all()
        self._password_input.show()
        self._password_input.setFocus()
        self.show()
    
    def hide_all(self):
        self._hide_all()
        self.hide()
    
    def _hide_all(self):
        self._stop_btn.hide()
        self._yes_btn.hide()
        self._no_btn.hide()
        self._password_input.hide()
        self._password_input.clear()
    
    def _submit_password(self):
        password = self._password_input.text()
        if password:
            self.password_submitted.emit(password)
            self._password_input.clear()
            self.hide_all()


class HistoryDialog(QDialog):
    """Chat history selection dialog"""
    
    chat_selected = pyqtSignal(str)  # chat_id
    
    def __init__(self, history: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sohbet Gecmisi")
        self.setMinimumSize(300, 400)
        self.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        self._setup_ui(history)
    
    def _setup_ui(self, history: List[Dict]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("Gecmis Sohbetler")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # List
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 10px;
                color: {Colors.TEXT_PRIMARY};
                border-bottom: 1px solid {Colors.BG_ELEVATED};
            }}
            QListWidget::item:hover {{
                background-color: {Colors.BG_TERTIARY};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.ACCENT_SUBTLE};
            }}
        """)
        
        for chat in history:
            item = QListWidgetItem(f"{chat.get('title', 'Untitled')} - {chat.get('date', '')}")
            item.setData(Qt.ItemDataRole.UserRole, chat.get('id'))
            self._list.addItem(item)
        
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list)
        
        # Close button
        close_btn = QPushButton("Kapat")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def _on_select(self, item):
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        self.chat_selected.emit(chat_id)
        self.close()


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
        """Add sent message to history"""
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


class ChatInterface(QWidget):
    """
    SENTINEL Chat Interface - VS Code Style
    
    Features:
    - History button + New chat button
    - Auto-expand input
    - JSON persistence
    """
    
    message_sent = pyqtSignal(str)
    command_requested = pyqtSignal(str)
    stop_requested = pyqtSignal()
    input_sent = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_chat_id = None
        self._messages: List[Dict] = []
        self.setStyleSheet(f"background-color: {Colors.BG_SECONDARY};")
        self._setup_ui()
        self._load_or_create_chat()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with History and New Chat buttons
        header = QFrame()
        header.setStyleSheet(f"""
            background-color: {Colors.BG_SECONDARY};
            border-bottom: 1px solid {Colors.BG_ELEVATED};
        """)
        header.setFixedHeight(36)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(4)
        
        # History button
        self._history_btn = QPushButton("History")
        self._history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._history_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_TERTIARY};
                border-radius: 4px;
            }}
        """)
        self._history_btn.clicked.connect(self._show_history)
        header_layout.addWidget(self._history_btn)
        
        header_layout.addStretch()
        
        # New chat button
        self._new_chat_btn = QPushButton("+")
        self._new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_chat_btn.setFixedSize(28, 28)
        self._new_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_ELEVATED};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT_PRIMARY};
                border-color: {Colors.ACCENT_PRIMARY};
                background-color: {Colors.ACCENT_SUBTLE};
            }}
        """)
        self._new_chat_btn.clicked.connect(self._new_chat)
        header_layout.addWidget(self._new_chat_btn)
        
        layout.addWidget(header)
        
        # Scroll area for messages
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BG_SECONDARY};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
        """)
        
        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._messages_layout.setSpacing(12)
        self._messages_layout.addStretch()
        
        scroll.setWidget(self._messages_container)
        layout.addWidget(scroll, stretch=1)
        
        self._scroll = scroll
        
        # Action buttons (dynamic)
        self._action_buttons = ActionButtons()
        self._action_buttons.stop_clicked.connect(self.stop_requested.emit)
        self._action_buttons.yes_clicked.connect(lambda: self.input_sent.emit("y"))
        self._action_buttons.no_clicked.connect(lambda: self.input_sent.emit("n"))
        self._action_buttons.password_submitted.connect(self.input_sent.emit)
        layout.addWidget(self._action_buttons)
        
        # Input area (auto-expand)
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            background-color: {Colors.BG_PRIMARY};
            border-top: 1px solid {Colors.BG_ELEVATED};
        """)
        input_frame.setMinimumHeight(44)
        input_frame.setMaximumHeight(128)
        
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 4, 12, 4)
        input_layout.setSpacing(8)
        
        self._input = AutoExpandTextEdit()
        self._input.setPlaceholderText("Ask Sentinel...")
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_TERTIARY};
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
        """)
        self._input.returnPressed.connect(self._on_send)
        input_layout.addWidget(self._input, stretch=1)
        
        self._send_btn = QPushButton("Send")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setFixedHeight(36)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self._send_btn)
        
        layout.addWidget(input_frame)
    
    def _on_send(self):
        text = self._input.toPlainText().strip()
        if text:
            self._input.add_to_history(text)
            self._input.clear()
            self.message_sent.emit(text)
    
    def _load_or_create_chat(self):
        """Always start with a fresh chat on app launch"""
        self._new_chat()
    
    def _new_chat(self):
        """Create new chat, save current if exists"""
        if self._current_chat_id and self._messages:
            self._save_current_chat()
        
        self._current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._messages = []
        self.clear_chat()
    
    def _save_current_chat(self):
        """Save current chat to history"""
        if not self._current_chat_id:
            return
            
        history = self._load_history()
        
        # Find and update or add
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
        """Get title from first user message"""
        for msg in self._messages:
            if msg.get('is_user'):
                return msg.get('text', 'Untitled')[:30]
        return "Untitled"
    
    def _load_history(self) -> List[Dict]:
        """Load chat history from JSON file"""
        try:
            os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
            if os.path.exists(CHAT_HISTORY_FILE):
                with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load chat history: {e}")
        return []
    
    def _save_history(self, history: List[Dict]):
        """Save chat history to JSON file"""
        try:
            os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
            with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save chat history: {e}")
    
    def _show_history(self):
        """Show history dialog"""
        history = self._load_history()
        dialog = HistoryDialog(history, self)
        dialog.chat_selected.connect(self._load_chat)
        dialog.exec()
    
    def _load_chat(self, chat_id: str):
        """Load specific chat from history"""
        # Save current first
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
        """Render all messages from current chat"""
        self.clear_chat()
        for msg in self._messages:
            if msg.get('is_user'):
                self._add_bubble(msg['text'], is_user=True)
            else:
                self._add_bubble(msg['text'], is_user=False, command=msg.get('command'))
    
    def _add_bubble(self, message: str, is_user: bool, command: Optional[str] = None):
        """Internal: add bubble to UI"""
        bubble_container = QWidget()
        container_layout = QHBoxLayout(bubble_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        if is_user:
            container_layout.addStretch()
        
        bubble = ChatBubble(message, is_user=is_user, command=command)
        if not is_user:
            bubble.command_run.connect(self.command_requested.emit)
        
        container_layout.addWidget(bubble)
        
        if not is_user:
            container_layout.addStretch()
        
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, bubble_container)
        self._scroll_to_bottom()
    
    def add_user_message(self, message: str):
        """Add user message bubble"""
        self._messages.append({'text': message, 'is_user': True})
        self._add_bubble(message, is_user=True)
        self._save_current_chat()
    
    def add_ai_message(self, message: str, command: Optional[str] = None):
        """Add AI message bubble with optional command"""
        self._messages.append({'text': message, 'is_user': False, 'command': command})
        self._add_bubble(message, is_user=False, command=command)
        self._save_current_chat()
    
    def show_stop_button(self):
        self._action_buttons.show_stop()
    
    def show_yesno_prompt(self):
        self._action_buttons.show_yesno()
    
    def show_password_prompt(self):
        self._action_buttons.show_password()
    
    def hide_action_buttons(self):
        self._action_buttons.hide_all()
    
    def clear_chat(self):
        """Clear all messages from UI"""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _scroll_to_bottom(self):
        """Scroll to bottom after adding message"""
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))
    
    def save_on_close(self):
        """Call this when app closes to save chat"""
        self._save_current_chat()
