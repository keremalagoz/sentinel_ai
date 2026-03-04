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
from src.ui.i18n import t

CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'temp', 'chat_history.json')

# ── Pre-built QSS constants (M3: avoid per-widget f-string formatting) ────
_COMMAND_CARD_STYLE = f"""
    QFrame#CommandCard {{
        background-color: {Colors.BG_PRIMARY};
        border: 1px solid {Colors.BG_ELEVATED};
        border-radius: 8px;
    }}
    QFrame#CommandCard:hover {{
        border: 1px solid {Colors.ACCENT_PRIMARY};
    }}
"""
_RUN_BTN_STYLE = f"""
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
"""
_COPY_BTN_STYLE = f"""
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
"""
_BUBBLE_USER_STYLE = f"""
    QFrame {{
        background-color: {Colors.ACCENT_PRIMARY};
        border-radius: 12px;
        border-top-right-radius: 4px;
    }}
"""
_BUBBLE_AI_STYLE = f"""
    QFrame {{
        background-color: {Colors.BG_TERTIARY};
        border-radius: 12px;
        border-top-left-radius: 4px;
    }}
"""
_IDENTITY_USER_STYLE = f"color: {Colors.ACCENT_PRIMARY}; background: transparent; border: none;"
_IDENTITY_AI_STYLE = f"color: {Colors.SUCCESS}; background: transparent; border: none;"
_MSG_USER_STYLE = "color: white; background: transparent; border: none;"
_MSG_AI_STYLE = f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;"
_CMD_LABEL_STYLE = f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none; font-family: {Fonts.MONO};"

# ── QFont cache (M2: avoid creating identical QFont objects repeatedly) ────
_font_cache: dict = {}

def _get_cached_font(family: str, size: int, bold: bool = False) -> QFont:
    """Return a cached QFont instance for the given parameters."""
    key = (family, size, bold)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    font = QFont(family)
    if family == "mono":
        font = QFont("JetBrains Mono")
        font.setFamilies(["JetBrains Mono", "Fira Code", "Consolas"])
    font.setPixelSize(size)
    if bold:
        font.setBold(True)
    _font_cache[key] = font
    return font


# ── Command Card ─────────────────────────────────────────

class CommandCard(QFrame):
    """Inline command card with Run/Copy actions"""
    
    run_clicked = pyqtSignal(str)
    copy_clicked = pyqtSignal(str)
    
    def __init__(self, command: str, text_size: int = 13, parent=None):
        super().__init__(parent)
        self.command = command
        self._text_size = text_size
        self._setup_ui()
    
    def _setup_ui(self):
        self.setObjectName("CommandCard")
        self.setStyleSheet(_COMMAND_CARD_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        
        # Command text
        cmd_label = QLabel(self.command)
        cmd_label.setFont(_get_cached_font("mono", self._text_size))
        cmd_label.setStyleSheet(_CMD_LABEL_STYLE)
        cmd_label.setWordWrap(True)
        cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(cmd_label)
        
        # Buttons container
        self._btn_widget = QWidget()
        btn_layout = QHBoxLayout(self._btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        
        self._run_btn = QPushButton(t("btn.run"))
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setStyleSheet(_RUN_BTN_STYLE)
        self._run_btn.clicked.connect(self._on_run)
        btn_layout.addWidget(self._run_btn)
        
        self._copy_btn = QPushButton(t("btn.copy"))
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setStyleSheet(_COPY_BTN_STYLE)
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
    
    def __init__(
        self,
        message: str,
        is_user: bool,
        command: Optional[str] = None,
        timestamp: Optional[str] = None,
        text_size: int = 13,
        parent=None,
    ):
        super().__init__(parent)
        self.is_user = is_user
        self._text_size = text_size
        self._setup_ui(message, command, timestamp)
    
    def _setup_ui(self, message: str, command: Optional[str], timestamp: Optional[str]):
        self.setStyleSheet("background: transparent; border: none;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Identity label
        identity = QLabel()
        identity.setFont(_get_cached_font("ui", max(11, self._text_size - 2), bold=True))
        
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")
        
        if self.is_user:
            identity.setText(f"{t('chat.you')} \u00b7 {timestamp}")
            identity.setStyleSheet(_IDENTITY_USER_STYLE)
            identity.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            identity.setText(f"{t('chat.sentinel')} \u00b7 {timestamp}")
            identity.setStyleSheet(_IDENTITY_AI_STYLE)
            identity.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(identity)
        
        # Message bubble
        bubble = QFrame()
        bubble.setStyleSheet(_BUBBLE_USER_STYLE if self.is_user else _BUBBLE_AI_STYLE)
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(8)
        
        self._msg_label = QLabel(message)
        self._msg_label.setWordWrap(True)
        self._msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._msg_label.setFont(_get_cached_font("ui", self._text_size))
        self._msg_label.setStyleSheet(_MSG_USER_STYLE if self.is_user else _MSG_AI_STYLE)
        msg_label = self._msg_label  # local alias for downstream code
        
        bubble_layout.addWidget(msg_label)
        
        # Command card (AI only)
        if command and not self.is_user:
            cmd_card = CommandCard(command, text_size=self._text_size)
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
        
        self._yes_btn = QPushButton(t("btn.yes"))
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
        
        self._no_btn = QPushButton(t("btn.no"))
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
        self._password_input.setPlaceholderText(t("chat.enter_password"))
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

    def refresh_texts(self) -> None:
        """Update translatable texts after language change."""
        self._yes_btn.setText(t("btn.yes"))
        self._no_btn.setText(t("btn.no"))
        self._password_input.setPlaceholderText(t("chat.enter_password"))


# ── History Dialog ───────────────────────────────────────

class HistoryDialog(QDialog):
    """Professional chat history dialog with better visual hierarchy"""
    
    chat_selected = pyqtSignal(str)
    
    def __init__(self, history: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("chat.history_title"))
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
        title = QLabel(t("chat.history_title"))
        t_font = QFont()
        t_font.setPixelSize(16)
        t_font.setBold(True)
        title.setFont(t_font)
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()
        
        count_label = QLabel(t("chat.history_count").format(n=len(history)))
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
            chat_title = chat.get('title', t('chat.untitled'))
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
        
        close_btn = QPushButton(t("btn.close"))
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
        self._text_font_size = 13
        self._history_cache: Optional[List[Dict]] = None
        self._dirty = False
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(500)
        self._debounce_timer.timeout.connect(self._flush_history)
        self._bubble_refs: List[ChatBubble] = []
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
        
        self._section_label = QLabel(t("chat.section"))
        sl_font = QFont()
        sl_font.setPixelSize(11)
        self._section_label.setFont(sl_font)
        self._section_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; background: transparent; border: none;")
        section_layout.addWidget(self._section_label)
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
        self._input.setPlaceholderText(t("chat.placeholder"))
        input_font = QFont()
        input_font.setPixelSize(self._text_font_size)
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
        self._history_cache = history
        self._dirty = True
        self._debounce_timer.start()
    
    def _flush_history(self):
        """Write cached history to disk (called by debounce timer)."""
        if not self._dirty:
            return
        if self._history_cache is not None:
            self._save_history(self._history_cache)
        self._dirty = False
    
    def _get_chat_title(self) -> str:
        for msg in self._messages:
            if msg.get('is_user'):
                return msg.get('text', t('chat.untitled'))[:30]
        return t('chat.untitled')
    
    def _load_history(self) -> List[Dict]:
        if self._history_cache is not None:
            return self._history_cache
        try:
            os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
            if os.path.exists(CHAT_HISTORY_FILE):
                with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self._history_cache = json.load(f)
                    return self._history_cache
        except Exception as e:
            print(f"[WARN] Could not load chat history: {e}")
        self._history_cache = []
        return self._history_cache
    
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

    def delete_all_history(self) -> int:
        deleted = 0
        try:
            history = self._load_history()
            deleted = len(history)
            self._history_cache = []
            self._save_history([])
        except Exception as e:
            print(f"[WARN] Could not clear chat history: {e}")
        self._new_chat()
        return deleted
    
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
        
        bubble = ChatBubble(
            message,
            is_user=is_user,
            command=command,
            timestamp=timestamp,
            text_size=self._text_font_size,
        )
        bubble.setFixedWidth(self._get_target_bubble_width())
        if not is_user:
            bubble.command_run.connect(self.command_requested.emit)
        
        container_layout.addWidget(bubble)
        self._bubble_refs.append(bubble)
        
        if not is_user:
            container_layout.addStretch()
        
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, bubble_container)
        self._scroll_to_bottom()

    def _get_target_bubble_width(self) -> int:
        viewport_width = self._scroll.viewport().width()
        target_width = int(viewport_width * 0.62)
        target_width = max(420, min(760, target_width))
        return min(target_width, max(320, viewport_width - 48))

    def _update_bubble_widths(self):
        target_width = self._get_target_bubble_width()
        for bubble in self._bubble_refs:
            bubble.setFixedWidth(target_width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_bubble_widths()

    def set_text_font_size(self, size: int):
        self._text_font_size = max(11, min(24, int(size)))
        input_font = self._input.font()
        input_font.setPixelSize(self._text_font_size)
        self._input.setFont(input_font)
        # H4: Update existing bubble fonts instead of full re-render
        new_font = _get_cached_font("ui", self._text_font_size)
        for bubble in self._bubble_refs:
            if hasattr(bubble, '_msg_label'):
                bubble._msg_label.setFont(new_font)

    def refresh_texts(self) -> None:
        """Update translatable texts after language change."""
        self._section_label.setText(t("chat.section"))
        self._input.setPlaceholderText(t("chat.placeholder"))
        self._action_buttons.refresh_texts()
        self._render_messages()
    
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
        self._bubble_refs.clear()
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
        self._flush_history()
        self._save_current_chat()
        self._flush_history()
