"""
SENTINEL AI — UI Widget Unit Tests (PyQt6)
Headless widget instantiation & behavior verification.

Coverage:
  A. SecuritySettingsDialog  (get/set settings, combo, signal, connection status)
  B. ActionButtons           (show/hide, password submit, refresh_texts)
  C. ChatBubble              (user vs AI, command card, timestamp)
  D. CommandCard             (run/copy signals)
  E. AutoExpandTextEdit      (enter, shift+enter, history)
  F. HistoryDialog           (list display, truncation, signal)
  G. TerminalSession         (id, name, defaults)
  H. ChatInterface           (messages, title, font, clear, refresh)
  I. TerminalView            (tabs, escape, font, refresh, buffer, history)
  J. InteractivePatterns     (password & yesno detection)
  K. Styles constants        (colors, fonts, no hardcoded font-size)
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent

from src.ui.i18n import set_language, t


# ── Shared fixture ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """Module-scoped QApplication — reuse across all widget tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication(sys.argv)
    return instance


# =========================================================================
# A. SecuritySettingsDialog
# =========================================================================
class TestSecuritySettingsDialog:
    """SecuritySettingsDialog widget tests."""

    def _make(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        return SecuritySettingsDialog()

    def test_instantiation(self, app):
        dlg = self._make(app)
        assert dlg is not None

    def test_default_settings(self, app):
        dlg = self._make(app)
        s = dlg.get_settings()
        assert "cleanup_days" in s
        assert "secure_delete" in s
        assert "font_size" in s
        assert "language" in s

    def test_set_get_roundtrip(self, app):
        dlg = self._make(app)
        settings = {
            "cleanup_days": 14,
            "secure_delete": False,
            "font_size": 18,
            "language": "tr",
        }
        dlg.set_settings(settings)
        got = dlg.get_settings()
        assert got["cleanup_days"] == 14
        assert got["secure_delete"] is False
        assert got["font_size"] == 18
        assert got["language"] == "tr"

    def test_font_spin_min_boundary(self, app):
        dlg = self._make(app)
        dlg.set_settings({"font_size": 5})   # below minimum
        assert dlg.get_settings()["font_size"] >= 11

    def test_font_spin_max_boundary(self, app):
        dlg = self._make(app)
        dlg.set_settings({"font_size": 99})  # above maximum
        assert dlg.get_settings()["font_size"] <= 24

    def test_days_spin_min_boundary(self, app):
        dlg = self._make(app)
        dlg.set_settings({"cleanup_days": 0})
        assert dlg.get_settings()["cleanup_days"] >= 1

    def test_days_spin_max_boundary(self, app):
        dlg = self._make(app)
        dlg.set_settings({"cleanup_days": 999})
        assert dlg.get_settings()["cleanup_days"] <= 90

    def test_language_combo_has_11_items(self, app):
        dlg = self._make(app)
        assert dlg._lang_combo.count() == 11

    def test_language_combo_default_en(self, app):
        dlg = self._make(app)
        dlg.set_settings({"language": "en"})
        assert dlg._lang_combo.currentData() == "en"

    def test_language_combo_set_tr(self, app):
        dlg = self._make(app)
        dlg.set_settings({"language": "tr"})
        assert dlg._lang_combo.currentData() == "tr"

    def test_language_combo_invalid_falls_to_first(self, app):
        dlg = self._make(app)
        dlg.set_settings({"language": "xx_invalid"})
        # findData returns -1 → combo stays as is (default first item = "en")
        assert dlg._lang_combo.currentData() is not None

    def test_save_signal_emitted(self, app):
        dlg = self._make(app)
        received = []
        dlg.settings_changed.connect(lambda s: received.append(s))
        dlg._on_save()
        assert len(received) == 1
        assert "language" in received[0]
        assert "font_size" in received[0]

    def test_cleanup_handler_called(self, app):
        handler = MagicMock(return_value=3)
        from src.ui.settings_dialog import SecuritySettingsDialog
        dlg = SecuritySettingsDialog(cleanup_handler=handler)
        dlg._on_clean_now()
        handler.assert_called_once()

    def test_clear_all_chats_handler_called(self, app):
        handler = MagicMock(return_value=5)
        from src.ui.settings_dialog import SecuritySettingsDialog
        dlg = SecuritySettingsDialog(clear_all_chats_handler=handler)
        dlg._on_clear_all_chats()
        handler.assert_called_once()

    def test_update_connection_docker_running(self, app):
        dlg = self._make(app)
        set_language("en")
        dlg.update_connection_status(True, "qwen2.5:3b", "NATIVE")
        assert t("settings.docker_running") in dlg._docker_status.text()

    def test_update_connection_docker_stopped(self, app):
        dlg = self._make(app)
        set_language("en")
        dlg.update_connection_status(False, t("msg.offline"), "NATIVE")
        assert t("settings.docker_stopped") in dlg._docker_status.text()

    def test_update_connection_ai_offline_style(self, app):
        dlg = self._make(app)
        set_language("en")
        dlg.update_connection_status(True, t("msg.offline"), "NATIVE")
        # Should have danger color in stylesheet
        assert "color" in dlg._ai_status.styleSheet()


# =========================================================================
# B. ActionButtons
# =========================================================================
class TestActionButtons:

    def _make(self, app):
        from src.ui.chat_interface import ActionButtons
        return ActionButtons()

    def test_starts_hidden(self, app):
        ab = self._make(app)
        assert not ab.isVisible()

    def test_show_yesno_makes_visible(self, app):
        ab = self._make(app)
        ab.show_yesno()
        assert ab.isVisible()
        assert ab._yes_btn.isVisible()
        assert ab._no_btn.isVisible()
        assert not ab._password_input.isVisible()

    def test_show_password_makes_visible(self, app):
        ab = self._make(app)
        ab.show_password()
        assert ab.isVisible()
        assert ab._password_input.isVisible()
        assert not ab._yes_btn.isVisible()
        assert not ab._no_btn.isVisible()

    def test_hide_all_hides(self, app):
        ab = self._make(app)
        ab.show_yesno()
        ab.hide_all()
        assert not ab.isVisible()

    def test_yes_signal(self, app):
        ab = self._make(app)
        signals = []
        ab.yes_clicked.connect(lambda: signals.append("yes"))
        ab.yes_clicked.emit()
        assert signals == ["yes"]

    def test_no_signal(self, app):
        ab = self._make(app)
        signals = []
        ab.no_clicked.connect(lambda: signals.append("no"))
        ab.no_clicked.emit()
        assert signals == ["no"]

    def test_password_submit_signal(self, app):
        ab = self._make(app)
        signals = []
        ab.password_submitted.connect(lambda p: signals.append(p))
        ab._password_input.setText("secret123")
        ab._submit_password()
        assert signals == ["secret123"]

    def test_empty_password_not_submitted(self, app):
        ab = self._make(app)
        signals = []
        ab.password_submitted.connect(lambda p: signals.append(p))
        ab._password_input.setText("")
        ab._submit_password()
        assert signals == []

    def test_password_cleared_after_submit(self, app):
        ab = self._make(app)
        ab._password_input.setText("secret")
        ab._submit_password()
        assert ab._password_input.text() == ""

    def test_refresh_texts(self, app):
        ab = self._make(app)
        set_language("tr")
        ab.refresh_texts()
        assert ab._yes_btn.text() == t("btn.yes")
        assert ab._no_btn.text() == t("btn.no")

    def test_refresh_texts_changes_with_lang(self, app):
        ab = self._make(app)
        set_language("en")
        ab.refresh_texts()
        en_yes = ab._yes_btn.text()
        set_language("tr")
        ab.refresh_texts()
        tr_yes = ab._yes_btn.text()
        assert en_yes != tr_yes


# =========================================================================
# C. ChatBubble
# =========================================================================
class TestChatBubble:

    def _make(self, app, **kwargs):
        from src.ui.chat_interface import ChatBubble
        defaults = {"message": "Hello", "is_user": True}
        defaults.update(kwargs)
        return ChatBubble(**defaults)

    def test_user_bubble(self, app):
        b = self._make(app, is_user=True)
        assert b.is_user is True

    def test_ai_bubble(self, app):
        b = self._make(app, is_user=False)
        assert b.is_user is False

    def test_bubble_with_command_has_card(self, app):
        from src.ui.chat_interface import CommandCard
        b = self._make(app, is_user=False, command="nmap -sS 10.0.0.1")
        cards = b.findChildren(CommandCard)
        assert len(cards) == 1

    def test_user_bubble_no_command_card(self, app):
        from src.ui.chat_interface import CommandCard
        b = self._make(app, is_user=True, command="nmap -sS 10.0.0.1")
        cards = b.findChildren(CommandCard)
        assert len(cards) == 0

    def test_bubble_without_command_no_card(self, app):
        from src.ui.chat_interface import CommandCard
        b = self._make(app, is_user=False, command=None)
        cards = b.findChildren(CommandCard)
        assert len(cards) == 0

    def test_text_size_applied(self, app):
        b = self._make(app, text_size=18)
        assert b._text_size == 18

    def test_timestamp_preserved(self, app):
        b = self._make(app, timestamp="14:30")
        # Timestamp appears in a QLabel inside the bubble
        from PyQt6.QtWidgets import QLabel
        labels = b.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any("14:30" in txt for txt in texts)


# =========================================================================
# D. CommandCard
# =========================================================================
class TestCommandCard:

    def _make(self, app, cmd="ping 1.1.1.1"):
        from src.ui.chat_interface import CommandCard
        return CommandCard(cmd)

    def test_command_stored(self, app):
        c = self._make(app, "nmap -sV 10.0.0.1")
        assert c.command == "nmap -sV 10.0.0.1"

    def test_run_signal(self, app):
        c = self._make(app, "ping 1.1.1.1")
        signals = []
        c.run_clicked.connect(lambda cmd: signals.append(cmd))
        c._on_run()
        assert signals == ["ping 1.1.1.1"]

    def test_copy_signal(self, app):
        c = self._make(app, "ping 2.2.2.2")
        signals = []
        c.copy_clicked.connect(lambda cmd: signals.append(cmd))
        c._on_copy()
        assert signals == ["ping 2.2.2.2"]

    def test_run_hides_buttons(self, app):
        c = self._make(app)
        c._on_run()
        assert not c._btn_widget.isVisible()

    def test_copy_hides_buttons(self, app):
        c = self._make(app)
        c._on_copy()
        assert not c._btn_widget.isVisible()

    def test_run_button_text_i18n(self, app):
        set_language("en")
        c = self._make(app)
        assert c._run_btn.text() == "Run"

    def test_copy_button_text_i18n(self, app):
        set_language("en")
        c = self._make(app)
        assert c._copy_btn.text() == "Copy"

    def test_clipboard_set_on_copy(self, app):
        c = self._make(app, "echo hello")
        c._on_copy()
        clipboard = QApplication.clipboard()
        assert clipboard.text() == "echo hello"


# =========================================================================
# E. AutoExpandTextEdit
# =========================================================================
class TestAutoExpandTextEdit:

    def _make(self, app):
        from src.ui.chat_interface import AutoExpandTextEdit
        return AutoExpandTextEdit()

    def test_starts_empty(self, app):
        w = self._make(app)
        assert w.toPlainText() == ""

    def test_min_height(self, app):
        w = self._make(app)
        assert w.height() == w._min_height

    def test_add_to_history(self, app):
        w = self._make(app)
        w.add_to_history("hello")
        assert w._msg_history == ["hello"]

    def test_add_to_history_no_duplicates(self, app):
        w = self._make(app)
        w.add_to_history("hello")
        w.add_to_history("hello")  # duplicate
        assert w._msg_history == ["hello"]

    def test_add_to_history_different(self, app):
        w = self._make(app)
        w.add_to_history("a")
        w.add_to_history("b")
        assert len(w._msg_history) == 2

    def test_history_up(self, app):
        w = self._make(app)
        w.add_to_history("first")
        w.add_to_history("second")
        w._history_up()
        assert w.toPlainText() == "second"
        w._history_up()
        assert w.toPlainText() == "first"

    def test_history_down(self, app):
        w = self._make(app)
        w.add_to_history("first")
        w.add_to_history("second")
        w._history_up()
        w._history_up()
        w._history_down()
        assert w.toPlainText() == "second"

    def test_history_down_clears(self, app):
        w = self._make(app)
        w.add_to_history("first")
        w._history_up()
        w._history_down()
        assert w.toPlainText() == ""

    def test_return_pressed_signal(self, app):
        w = self._make(app)
        signals = []
        w.returnPressed.connect(lambda: signals.append("enter"))
        w.returnPressed.emit()
        assert signals == ["enter"]

    def test_empty_text_history_up_does_nothing(self, app):
        w = self._make(app)
        w._history_up()
        assert w.toPlainText() == ""


# =========================================================================
# F. HistoryDialog
# =========================================================================
class TestHistoryDialog:

    def _make(self, app, history=None):
        from src.ui.chat_interface import HistoryDialog
        if history is None:
            history = [
                {"id": "1", "title": "Test Chat", "date": "2026-03-03 12:00"},
                {"id": "2", "title": "Another Chat", "date": "2026-03-03 13:00"},
            ]
        return HistoryDialog(history)

    def test_instantiation(self, app):
        dlg = self._make(app)
        assert dlg is not None

    def test_list_has_correct_count(self, app):
        dlg = self._make(app)
        assert dlg._list.count() == 2

    def test_empty_history(self, app):
        dlg = self._make(app, history=[])
        assert dlg._list.count() == 0

    def test_long_title_truncated(self, app):
        long_title = "A" * 50
        dlg = self._make(app, history=[
            {"id": "x", "title": long_title, "date": "2026-01-01"}
        ])
        item_text = dlg._list.item(0).text()
        assert len(item_text.split("\n")[0]) <= 38  # 32 + "..."

    def test_chat_selected_signal(self, app):
        dlg = self._make(app)
        signals = []
        dlg.chat_selected.connect(lambda cid: signals.append(cid))
        dlg.chat_selected.emit("test_id")
        assert signals == ["test_id"]


# =========================================================================
# G. TerminalSession
# =========================================================================
class TestTerminalSession:

    def test_id_stored(self, app):
        from src.ui.terminal_view import TerminalSession
        s = TerminalSession(42)
        assert s.id == 42

    def test_name_format(self, app):
        from src.ui.terminal_view import TerminalSession
        set_language("en")
        s = TerminalSession(1)
        assert s.name == "Terminal 1"

    def test_name_i18n(self, app):
        from src.ui.terminal_view import TerminalSession
        set_language("tr")
        s = TerminalSession(3)
        expected = t("terminal.tab_name").format(id=3)
        assert s.name == expected

    def test_defaults(self, app):
        from src.ui.terminal_view import TerminalSession
        s = TerminalSession(1)
        assert s.is_running is False
        assert s.requires_root is False

    def test_custom_font_size(self, app):
        from src.ui.terminal_view import TerminalSession
        s = TerminalSession(1, text_font_size=20)
        assert s.output.font().pixelSize() == 20


# =========================================================================
# H. ChatInterface
# =========================================================================
class TestChatInterface:

    def _make(self, app):
        from src.ui.chat_interface import ChatInterface
        # Patch the history file to avoid polluting real data
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test_chat.json"):
            ci = ChatInterface()
        return ci

    def test_instantiation(self, app):
        ci = self._make(app)
        assert ci is not None

    def test_starts_with_empty_messages(self, app):
        ci = self._make(app)
        assert ci._messages == []

    def test_add_user_message(self, app):
        ci = self._make(app)
        ci.add_user_message("hello")
        assert len(ci._messages) == 1
        assert ci._messages[0]["is_user"] is True
        assert ci._messages[0]["text"] == "hello"

    def test_add_ai_message(self, app):
        ci = self._make(app)
        ci.add_ai_message("response")
        assert len(ci._messages) == 1
        assert ci._messages[0]["is_user"] is False

    def test_add_ai_message_with_command(self, app):
        ci = self._make(app)
        ci.add_ai_message("Ready", command="nmap -sS 10.0.0.1")
        assert ci._messages[0]["command"] == "nmap -sS 10.0.0.1"

    def test_add_ai_message_without_command(self, app):
        ci = self._make(app)
        ci.add_ai_message("Just text")
        assert ci._messages[0]["command"] is None

    def test_correlation_id_stored(self, app):
        ci = self._make(app)
        ci.add_user_message("test", correlation_id="cid_abc")
        assert ci._messages[0]["correlation_id"] == "cid_abc"

    def test_set_backend_session_id(self, app):
        ci = self._make(app)
        ci.set_backend_session_id("sess_123")
        assert ci.get_backend_session_id() == "sess_123"

    def test_new_chat_resets_backend_session_id(self, app):
        ci = self._make(app)
        ci.set_backend_session_id("sess_123")
        ci._new_chat()
        assert ci.get_backend_session_id() is None

    def test_get_chat_title_first_user_msg(self, app):
        ci = self._make(app)
        ci._messages = [{"text": "Scan 192.168.1.0/24", "is_user": True}]
        assert ci._get_chat_title() == "Scan 192.168.1.0/24"

    def test_get_chat_title_truncation(self, app):
        ci = self._make(app)
        long_text = "A" * 100
        ci._messages = [{"text": long_text, "is_user": True}]
        title = ci._get_chat_title()
        assert len(title) == 30

    def test_get_chat_title_no_user_msg(self, app):
        ci = self._make(app)
        ci._messages = [{"text": "AI response", "is_user": False}]
        set_language("en")
        assert ci._get_chat_title() == t("chat.untitled")

    def test_get_chat_title_empty(self, app):
        ci = self._make(app)
        ci._messages = []
        set_language("en")
        assert ci._get_chat_title() == t("chat.untitled")

    def test_clear_chat(self, app):
        ci = self._make(app)
        ci.add_user_message("test1")
        ci.add_user_message("test2")
        ci.clear_chat()
        # Messages layout should only have the stretch
        assert ci._messages_layout.count() == 1

    def test_message_sent_signal(self, app):
        ci = self._make(app)
        signals = []
        ci.message_sent.connect(lambda msg: signals.append(msg))
        ci.message_sent.emit("hello")
        assert signals == ["hello"]

    def test_command_requested_signal(self, app):
        ci = self._make(app)
        signals = []
        ci.command_requested.connect(lambda cmd: signals.append(cmd))
        ci.command_requested.emit("ping 1.1.1.1")
        assert signals == ["ping 1.1.1.1"]

    def test_set_text_font_size_normal(self, app):
        ci = self._make(app)
        ci.set_text_font_size(16)
        assert ci._text_font_size == 16

    def test_set_text_font_size_min_clamp(self, app):
        ci = self._make(app)
        ci.set_text_font_size(5)
        assert ci._text_font_size == 11

    def test_set_text_font_size_max_clamp(self, app):
        ci = self._make(app)
        ci.set_text_font_size(50)
        assert ci._text_font_size == 24

    def test_show_yesno_prompt(self, app):
        ci = self._make(app)
        ci.show_yesno_prompt()
        # isHidden() checks the widget's own state (not parent chain)
        assert not ci._action_buttons._yes_btn.isHidden()
        assert not ci._action_buttons._no_btn.isHidden()

    def test_show_password_prompt(self, app):
        ci = self._make(app)
        ci.show_password_prompt()
        assert not ci._action_buttons._password_input.isHidden()

    def test_hide_action_buttons(self, app):
        ci = self._make(app)
        ci.show_yesno_prompt()
        ci.hide_action_buttons()
        assert ci._action_buttons._yes_btn.isHidden()

    def test_refresh_texts_en(self, app):
        ci = self._make(app)
        set_language("en")
        ci.refresh_texts()
        assert ci._section_label.text() == "Chat"

    def test_refresh_texts_tr(self, app):
        ci = self._make(app)
        set_language("tr")
        ci.refresh_texts()
        assert ci._section_label.text() == t("chat.section")

    def test_multiple_messages(self, app):
        ci = self._make(app)
        for i in range(5):
            ci.add_user_message(f"msg_{i}")
        assert len(ci._messages) == 5

    def test_new_chat_clears_messages(self, app):
        ci = self._make(app)
        ci.add_user_message("test")
        ci._new_chat()
        assert ci._messages == []

    def test_save_current_chat_persists_backend_session_id(self, app):
        ci = self._make(app)
        ci.set_backend_session_id("sess_history")
        ci.add_user_message("scan target")
        ci._flush_history()
        history = ci._load_history()
        assert history[-1]["backend_session_id"] == "sess_history"

    def test_load_chat_emits_backend_session_id(self, app):
        ci = self._make(app)
        ci._history_cache = [
            {
                "id": "chat_1",
                "title": "Chat 1",
                "date": "2026-03-08 10:00",
                "backend_session_id": "sess_saved",
                "messages": [{"text": "hello", "is_user": True, "timestamp": "10:00"}],
            }
        ]
        events = []
        ci.chat_loaded.connect(lambda chat_id, session_id: events.append((chat_id, session_id)))
        ci._load_chat("chat_1")
        assert ci.get_backend_session_id() == "sess_saved"
        assert events == [("chat_1", "sess_saved")]

    def test_load_chat_without_backend_session_emits_empty_string(self, app):
        ci = self._make(app)
        ci._history_cache = [
            {
                "id": "chat_2",
                "title": "Chat 2",
                "date": "2026-03-08 10:05",
                "messages": [{"text": "hello", "is_user": True, "timestamp": "10:05"}],
            }
        ]
        events = []
        ci.chat_loaded.connect(lambda chat_id, session_id: events.append((chat_id, session_id)))
        ci._load_chat("chat_2")
        assert ci.get_backend_session_id() is None
        assert events == [("chat_2", "")]


# =========================================================================
# I. TerminalView
# =========================================================================
class TestTerminalView:

    def _make(self, app):
        from src.ui.terminal_view import TerminalView
        return TerminalView(process_manager=None)

    def test_instantiation(self, app):
        tv = self._make(app)
        assert tv is not None

    def test_starts_with_one_session(self, app):
        tv = self._make(app)
        assert len(tv._sessions) == 1

    def test_add_terminal(self, app):
        tv = self._make(app)
        initial = len(tv._sessions)
        tv._add_terminal()
        assert len(tv._sessions) == initial + 1

    def test_close_terminal_min_one(self, app):
        tv = self._make(app)
        # Should not close the last terminal
        session = tv._sessions[0]
        tv._close_terminal(session)
        assert len(tv._sessions) == 1

    def test_close_terminal_when_multiple(self, app):
        tv = self._make(app)
        tv._add_terminal()
        assert len(tv._sessions) == 2
        session = tv._sessions[-1]
        tv._close_terminal(session)
        assert len(tv._sessions) == 1

    def test_tab_count_matches_sessions(self, app):
        tv = self._make(app)
        tv._add_terminal()
        tv._add_terminal()
        assert tv._tab_bar.count() == len(tv._sessions)

    def test_active_session_after_creation(self, app):
        tv = self._make(app)
        assert tv._active_session is not None
        assert tv._active_session == tv._sessions[0]

    def test_switch_terminal(self, app):
        tv = self._make(app)
        s2 = tv._add_terminal()
        tv._switch_terminal(tv._sessions[0])
        assert tv._active_session == tv._sessions[0]
        tv._switch_terminal(s2)
        assert tv._active_session == s2

    def test_session_ids_unique(self, app):
        tv = self._make(app)
        tv._add_terminal()
        tv._add_terminal()
        ids = [s.id for s in tv._sessions]
        assert len(ids) == len(set(ids))

    def test_escape_html(self, app):
        from src.ui.terminal_view import TerminalView
        assert TerminalView._escape("<script>") == "&lt;script&gt;"
        assert TerminalView._escape("a & b") == "a&nbsp;&amp;&nbsp;b"
        assert TerminalView._escape("x > y") == "x&nbsp;&gt;&nbsp;y"
        assert TerminalView._escape("line\nbreak") == "line<br>break"
        assert TerminalView._escape("two  spaces") == "two&nbsp;&nbsp;spaces"

    def test_set_text_font_size_normal(self, app):
        tv = self._make(app)
        tv.set_text_font_size(18)
        assert tv._text_font_size == 18

    def test_set_text_font_size_min_clamp(self, app):
        tv = self._make(app)
        tv.set_text_font_size(5)
        assert tv._text_font_size == 11

    def test_set_text_font_size_max_clamp(self, app):
        tv = self._make(app)
        tv.set_text_font_size(50)
        assert tv._text_font_size == 24

    def test_refresh_texts_en(self, app):
        tv = self._make(app)
        set_language("en")
        tv.refresh_texts()
        assert tv._section_label.text() == "Terminal"
        assert tv._stop_btn.text() == "Stop"

    def test_refresh_texts_tr(self, app):
        tv = self._make(app)
        set_language("tr")
        tv.refresh_texts()
        assert tv._section_label.text() == t("terminal.section")
        assert tv._stop_btn.text() == t("btn.stop")

    def test_refresh_texts_updates_tab_names(self, app):
        tv = self._make(app)
        set_language("tr")
        tv.refresh_texts()
        for session in tv._sessions:
            expected = t("terminal.tab_name").format(id=session.id)
            assert session.name == expected

    def test_get_active_session_name(self, app):
        tv = self._make(app)
        name = tv.get_active_session_name()
        assert name and len(name) > 0

    def test_command_history_empty_at_start(self, app):
        tv = self._make(app)
        assert tv._command_history == []

    def test_history_up_empty(self, app):
        tv = self._make(app)
        tv._history_up()  # should not crash
        assert tv._input.text() == ""

    def test_history_navigation(self, app):
        tv = self._make(app)
        tv._command_history = ["cmd1", "cmd2", "cmd3"]
        tv._history_index = 0
        tv._history_up()
        assert tv._input.text() == "cmd3"
        tv._history_up()
        assert tv._input.text() == "cmd2"
        tv._history_down()
        assert tv._input.text() == "cmd3"

    def test_history_down_clears(self, app):
        tv = self._make(app)
        tv._command_history = ["cmd1"]
        tv._history_index = 0
        tv._history_up()
        assert tv._input.text() == "cmd1"
        tv._history_down()
        assert tv._input.text() == ""

    def test_stop_btn_hidden_by_default(self, app):
        tv = self._make(app)
        assert not tv._stop_btn.isVisible()

    def test_status_signals_exist(self, app):
        tv = self._make(app)
        # Verify all expected signals exist
        assert hasattr(tv, "sig_status_changed")
        assert hasattr(tv, "sig_prompt_detected")
        assert hasattr(tv, "sig_process_finished")
        assert hasattr(tv, "sig_command_submitted")


# =========================================================================
# J. InteractivePatterns
# =========================================================================
class TestInteractivePatterns:

    @pytest.mark.parametrize("text,expected", [
        ("Enter password: ", True),
        ("Password:", True),
        ("password:", True),
        ("[sudo] password for user:", True),
        ("parola:", True),
        ("şifre:", True),
        ("sifre:", True),
        ("Enter your passwd:", True),
        ("Hello world", False),
        ("password", False),  # no colon → no prompt
        ("The password is stored in file", False),
        ("", False),
    ])
    def test_is_password_prompt(self, text, expected):
        from src.ui.styles import InteractivePatterns
        assert InteractivePatterns.is_password_prompt(text) is expected

    @pytest.mark.parametrize("text,expected", [
        ("Continue? [y/n]: ", True),
        ("Proceed? ", True),
        ("Do you want to continue?", True),
        ("confirm?", True),
        ("[y/n]:", True),
        ("Hello world", False),
        ("yes", False),
        ("no", False),
        ("", False),
    ])
    def test_is_yesno_prompt(self, text, expected):
        from src.ui.styles import InteractivePatterns
        assert InteractivePatterns.is_yesno_prompt(text) is expected

    def test_multiline_password_last_line(self):
        from src.ui.styles import InteractivePatterns
        text = "Connecting to server...\nEnter password: "
        assert InteractivePatterns.is_password_prompt(text) is True

    def test_multiline_no_password(self):
        from src.ui.styles import InteractivePatterns
        text = "password was remembered\nAll done"
        assert InteractivePatterns.is_password_prompt(text) is False

    def test_empty_string_safe(self):
        from src.ui.styles import InteractivePatterns
        assert InteractivePatterns.is_password_prompt("") is False
        assert InteractivePatterns.is_yesno_prompt("") is False


# =========================================================================
# K. Styles / Constants
# =========================================================================
class TestStylesConstants:

    def test_colors_are_valid_hex_or_rgba(self):
        from src.ui.styles import Colors
        import re
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        rgba_pattern = re.compile(r"^rgba\(\d+,\s*\d+,\s*\d+,\s*[0-9.]+\)$")

        for attr in dir(Colors):
            if attr.startswith("_"):
                continue
            val = getattr(Colors, attr)
            if isinstance(val, str):
                assert hex_pattern.match(val) or rgba_pattern.match(val), (
                    f"Colors.{attr} = '{val}' is not valid hex or rgba"
                )

    def test_fonts_not_empty(self):
        from src.ui.styles import Fonts
        assert Fonts.UI and len(Fonts.UI) > 0
        assert Fonts.MONO and len(Fonts.MONO) > 0

    def test_global_style_no_font_size(self):
        """Sprint 3 font fix regression: GLOBAL_STYLE must NOT contain font-size."""
        from src.ui.styles import GLOBAL_STYLE
        assert "font-size" not in GLOBAL_STYLE, (
            "GLOBAL_STYLE should not have hardcoded font-size (Sprint 3 fix)"
        )

    def test_terminal_theme_no_font_size(self):
        """Sprint 3 font fix regression: TERMINAL_THEME must NOT contain font-size."""
        from src.ui.styles import TERMINAL_THEME
        assert "font-size" not in TERMINAL_THEME, (
            "TERMINAL_THEME should not have hardcoded font-size (Sprint 3 fix)"
        )
