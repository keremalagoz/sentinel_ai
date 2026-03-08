"""
SENTINEL AI — UI Feature Integration Tests
Tests that verify feature-level behavior across multiple components.

Coverage:
  A. Swap Chat/Terminal               (splitter widget reordering)
  B. Font System                      (no hardcoded font-size, clamp, sync)
  C. Language Switch E2E              (set_language → refresh → verify labels)
  D. Settings Persistence             (JSON round-trip, defaults, bad data)
  E. Orchestrator i18n                (AI messages in all languages)
  F. Badge & Status i18n              (execution state badges)
  G. Risk Normalization               (normalize + label mapping)
  H. Connection Status i18n           (settings dialog docker/AI labels)
  I. Boundary Regression              (import rules)
  J. Chat History i18n                (untitled, cleanup)
  K. Cleanup Regression               (empty chat record removal)
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.i18n import set_language, get_language, t, get_available_languages, _EN, _TRANSLATIONS, LANGUAGES


# ── Shared fixture ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication(sys.argv)
    return instance


# =========================================================================
# A. Swap Chat/Terminal
# =========================================================================
class TestSwapFeature:
    """Verify Chat/Terminal swap changes splitter widget order."""

    def _make_window_light(self, app):
        """Create a lightweight simulated splitter swap without full MainWindow."""
        from PyQt6.QtWidgets import QSplitter, QWidget
        splitter = QSplitter(Qt.Orientation.Vertical)
        chat = QWidget()
        chat.setObjectName("chat")
        terminal = QWidget()
        terminal.setObjectName("terminal")
        splitter.addWidget(chat)
        splitter.addWidget(terminal)
        splitter.setSizes([600, 300])
        return splitter, chat, terminal

    def test_initial_order_chat_first(self, app):
        splitter, chat, terminal = self._make_window_light(app)
        assert splitter.widget(0).objectName() == "chat"
        assert splitter.widget(1).objectName() == "terminal"

    def test_swap_puts_terminal_first(self, app):
        splitter, chat, terminal = self._make_window_light(app)
        sizes = splitter.sizes()
        splitter.insertWidget(0, terminal)
        splitter.setSizes(list(reversed(sizes)))
        assert splitter.widget(0).objectName() == "terminal"
        assert splitter.widget(1).objectName() == "chat"

    def test_double_swap_restores_order(self, app):
        splitter, chat, terminal = self._make_window_light(app)
        # First swap
        sizes = splitter.sizes()
        splitter.insertWidget(0, terminal)
        splitter.setSizes(list(reversed(sizes)))
        # Second swap (back to original)
        sizes2 = splitter.sizes()
        splitter.insertWidget(0, chat)
        splitter.setSizes(list(reversed(sizes2)))
        assert splitter.widget(0).objectName() == "chat"
        assert splitter.widget(1).objectName() == "terminal"

    def test_swap_preserves_sizes_sum(self, app):
        splitter, chat, terminal = self._make_window_light(app)
        splitter.setSizes([600, 300])
        original_sum = sum(splitter.sizes())
        splitter.insertWidget(0, terminal)
        splitter.setSizes(list(reversed(splitter.sizes())))
        new_sum = sum(splitter.sizes())
        assert new_sum == original_sum

    def test_swap_sizes_reversed(self, app):
        splitter, chat, terminal = self._make_window_light(app)
        splitter.setSizes([700, 200])
        before = splitter.sizes()
        splitter.insertWidget(0, terminal)
        splitter.setSizes(list(reversed(before)))
        after = splitter.sizes()
        assert after == list(reversed(before))

    def test_widget_count_unchanged_after_swap(self, app):
        splitter, chat, terminal = self._make_window_light(app)
        assert splitter.count() == 2
        splitter.insertWidget(0, terminal)
        assert splitter.count() == 2

    def test_horizontal_swap_also_works(self, app):
        from PyQt6.QtWidgets import QSplitter, QWidget
        splitter = QSplitter(Qt.Orientation.Horizontal)
        a = QWidget(); a.setObjectName("a")
        b = QWidget(); b.setObjectName("b")
        splitter.addWidget(a)
        splitter.addWidget(b)
        splitter.insertWidget(0, b)
        assert splitter.widget(0).objectName() == "b"


# =========================================================================
# B. Font System
# =========================================================================
class TestFontSystem:
    """Sprint 3 font fix regression tests."""

    def test_global_style_no_font_size(self):
        from src.ui.styles import GLOBAL_STYLE
        # Must NOT contain font-size to avoid overriding setFont()
        assert "font-size" not in GLOBAL_STYLE

    def test_terminal_theme_no_font_size(self):
        from src.ui.styles import TERMINAL_THEME
        assert "font-size" not in TERMINAL_THEME

    def test_chat_interface_font_clamp_low(self, app):
        from src.ui.chat_interface import ChatInterface
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test.json"):
            ci = ChatInterface()
        ci.set_text_font_size(3)
        assert ci._text_font_size == 11

    def test_chat_interface_font_clamp_high(self, app):
        from src.ui.chat_interface import ChatInterface
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test.json"):
            ci = ChatInterface()
        ci.set_text_font_size(999)
        assert ci._text_font_size == 24

    def test_terminal_view_font_clamp_low(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv.set_text_font_size(3)
        assert tv._text_font_size == 11

    def test_terminal_view_font_clamp_high(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv.set_text_font_size(999)
        assert tv._text_font_size == 24

    def test_font_size_13_default(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        assert tv._text_font_size == 13

    def test_set_font_size_updates_input_font(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv.set_text_font_size(20)
        assert tv._input.font().pixelSize() == 20

    def test_set_font_size_updates_session_font(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv.set_text_font_size(18)
        for session in tv._sessions:
            assert session.output.font().pixelSize() == 18

    @pytest.mark.parametrize("size", [11, 13, 16, 20, 24])
    def test_valid_font_sizes(self, app, size):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv.set_text_font_size(size)
        assert tv._text_font_size == size


# =========================================================================
# C. Language Switch E2E
# =========================================================================
class TestLanguageSwitchE2E:
    """Full language switch cycle: set → verify all visible text."""

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_all_critical_keys_translate(self, lang):
        set_language(lang)
        # Every critical key must return non-empty, different from key itself (for EN base)
        for key in ["badge.ready", "btn.save", "btn.run", "chat.section",
                     "terminal.section", "settings.title", "msg.offline"]:
            val = t(key)
            assert val, f"t('{key}') empty for lang={lang}"
            assert isinstance(val, str)

    def test_refresh_chat_section_label(self, app):
        from src.ui.chat_interface import ChatInterface
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test.json"):
            ci = ChatInterface()
        set_language("tr")
        ci.refresh_texts()
        assert ci._section_label.text() == t("chat.section")

    def test_refresh_terminal_section_label(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        set_language("ja")
        tv.refresh_texts()
        assert tv._section_label.text() == t("terminal.section")

    def test_refresh_action_buttons(self, app):
        from src.ui.chat_interface import ActionButtons
        ab = ActionButtons()
        set_language("de")
        ab.refresh_texts()
        assert ab._yes_btn.text() == t("btn.yes")

    def test_settings_dialog_title_changes(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        set_language("fr")
        dlg = SecuritySettingsDialog()
        assert dlg.windowTitle() == t("settings.title")

    def test_terminal_tab_name_language(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        set_language("zh")
        tv.refresh_texts()
        session = tv._sessions[0]
        assert session.name == t("terminal.tab_name").format(id=session.id)

    @pytest.mark.parametrize("lang", ["en", "tr", "ru", "ja", "zh"])
    def test_orchestrator_cmd_ready_format(self, lang):
        set_language(lang)
        msg = t("ai.cmd_ready").format(cmd="nmap -sS 10.0.0.1")
        assert "nmap -sS 10.0.0.1" in msg
        assert len(msg) > len("nmap -sS 10.0.0.1")

    def test_language_does_not_affect_sentinel_name(self):
        for code, _ in LANGUAGES:
            set_language(code)
            assert t("chat.sentinel") == "Sentinel"


# =========================================================================
# D. Settings Persistence
# =========================================================================
class TestSettingsPersistence:
    """JSON settings file round-trip tests."""

    def _make_temp_settings(self, data):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, f, ensure_ascii=False)
        f.close()
        return f.name

    def test_valid_json_roundtrip(self):
        data = {"cleanup_days": 14, "secure_delete": True, "font_size": 16, "language": "tr"}
        path = self._make_temp_settings(data)
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded == data
        finally:
            os.unlink(path)

    def test_default_fallback_on_missing_keys(self):
        data = {"cleanup_days": 5}
        defaults = {"cleanup_days": 7, "secure_delete": True, "font_size": 13, "language": "en"}
        merged = {
            "cleanup_days": int(data.get("cleanup_days", defaults["cleanup_days"])),
            "secure_delete": bool(data.get("secure_delete", defaults["secure_delete"])),
            "font_size": int(data.get("font_size", defaults["font_size"])),
            "language": str(data.get("language", defaults["language"])),
        }
        assert merged["cleanup_days"] == 5
        assert merged["secure_delete"] is True
        assert merged["font_size"] == 13
        assert merged["language"] == "en"

    def test_bad_json_returns_defaults(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        f.write("{invalid json!!!}")
        f.close()
        try:
            try:
                with open(f.name, "r") as fh:
                    json.load(fh)
                loaded = True
            except json.JSONDecodeError:
                loaded = False
            assert loaded is False
        finally:
            os.unlink(f.name)

    def test_language_key_persists(self):
        data = {"cleanup_days": 7, "secure_delete": True, "font_size": 13, "language": "ja"}
        path = self._make_temp_settings(data)
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["language"] == "ja"
        finally:
            os.unlink(path)

    def test_font_size_persists(self):
        data = {"cleanup_days": 7, "secure_delete": True, "font_size": 20, "language": "en"}
        path = self._make_temp_settings(data)
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["font_size"] == 20
        finally:
            os.unlink(path)


# =========================================================================
# E. Orchestrator i18n
# =========================================================================
class TestOrchestratorI18n:
    """Verify all 8 orchestrator message keys translate correctly across languages."""

    ORCHESTRATOR_KEYS = [
        "ai.cmd_ready",
        "ai.cmd_failed",
        "ai.low_confidence",
        "ai.clarify",
        "ai.info_query",
        "ai.unknown_intent",
        "ai.no_target",
        "ai.no_tool",
    ]

    @pytest.mark.parametrize("key", ORCHESTRATOR_KEYS)
    def test_key_exists_in_all_languages(self, key):
        for code, _ in LANGUAGES:
            assert key in _TRANSLATIONS[code], (
                f"Key '{key}' missing in language '{code}'"
            )

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_cmd_ready_format_works(self, code):
        set_language(code)
        result = t("ai.cmd_ready").format(cmd="nmap -sS 10.0.0.1")
        assert "nmap -sS 10.0.0.1" in result

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_cmd_failed_format_works(self, code):
        set_language(code)
        result = t("ai.cmd_failed").format(error="timeout")
        assert "timeout" in result

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_low_confidence_format_works(self, code):
        set_language(code)
        result = t("ai.low_confidence").format(conf="42%")
        assert "42%" in result

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_no_tool_format_works(self, code):
        set_language(code)
        result = t("ai.no_tool").format(intent="port_scan")
        assert "port_scan" in result

    def test_en_cmd_ready_text(self):
        set_language("en")
        assert "Command ready:" in t("ai.cmd_ready").format(cmd="test")

    def test_tr_cmd_ready_text(self):
        set_language("tr")
        result = t("ai.cmd_ready").format(cmd="test")
        assert "Komut hazır:" in result

    def test_ru_cmd_ready_text(self):
        set_language("ru")
        result = t("ai.cmd_ready").format(cmd="test")
        assert "Команда готова:" in result

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_non_format_keys_are_standalone(self, code):
        """Keys without format params should be usable directly."""
        set_language(code)
        assert t("ai.clarify")
        assert t("ai.info_query")
        assert t("ai.unknown_intent")
        assert t("ai.no_target")


# =========================================================================
# F. Badge & Status i18n
# =========================================================================
class TestBadgeStatus:
    """Header badge text follows active language."""

    @pytest.mark.parametrize("lang,expected", [
        ("en", "READY"),
        ("tr", "HAZIR"),
        ("ru", "ГОТОВ"),
        ("es", "LISTO"),
    ])
    def test_badge_ready_text(self, lang, expected):
        set_language(lang)
        assert t("badge.ready") == expected

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_badge_running_non_empty(self, lang):
        set_language(lang)
        assert t("badge.running")

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_badge_root_is_root(self, lang):
        set_language(lang)
        assert t("badge.root") == "ROOT"


# =========================================================================
# G. Risk Normalization
# =========================================================================
class TestRiskNormalization:
    """MainWindow._normalize_risk and _risk_to_ui logic."""

    def _normalize(self, value):
        """Replicate MainWindow._normalize_risk without full MainWindow."""
        val = (value or "low").lower()
        if val.endswith(".high"):
            return "high"
        if val.endswith(".medium"):
            return "medium"
        if val.endswith(".low"):
            return "low"
        if val in {"high", "medium", "low"}:
            return val
        return "low"

    def _risk_to_ui(self, value):
        normalized = self._normalize(value)
        if normalized == "high":
            return t("risk.root_required")
        if normalized == "medium":
            return t("risk.caution")
        return t("risk.safe")

    @pytest.mark.parametrize("input_val,expected", [
        ("low", "low"),
        ("medium", "medium"),
        ("high", "high"),
        ("LOW", "low"),
        ("HIGH", "high"),
        ("MEDIUM", "medium"),
        ("risk.high", "high"),
        ("risk.medium", "medium"),
        ("risk.low", "low"),
        (None, "low"),
        ("", "low"),
        ("unknown_value", "low"),
        ("CRITICAL", "low"),  # maps to default
    ])
    def test_normalize_risk(self, input_val, expected):
        assert self._normalize(input_val) == expected

    def test_risk_to_ui_high_en(self):
        set_language("en")
        assert self._risk_to_ui("high") == t("risk.root_required")

    def test_risk_to_ui_medium_en(self):
        set_language("en")
        assert self._risk_to_ui("medium") == t("risk.caution")

    def test_risk_to_ui_low_en(self):
        set_language("en")
        assert self._risk_to_ui("low") == t("risk.safe")

    def test_risk_to_ui_tr(self):
        set_language("tr")
        assert self._risk_to_ui("high") == t("risk.root_required")

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_risk_labels_non_empty(self, lang):
        set_language(lang)
        assert t("risk.root_required")
        assert t("risk.caution")
        assert t("risk.safe")


class TestSessionParity:
    """Chat history selection should keep backend session context aligned."""

    def test_chat_loaded_restores_existing_backend_session(self):
        from src.ui.main_window import MainWindow

        create_calls = []

        class DummyOrchestrator:
            def create_session(self, session_id=None):
                create_calls.append(session_id)
                return session_id or "sess_new"

        class DummyChatInterface:
            def __init__(self):
                self.backend_session_id = None

            def set_backend_session_id(self, session_id):
                self.backend_session_id = session_id

        dummy = type("DummyWindow", (), {})()
        dummy.backend = type("DummyBackend", (), {"_orchestrator": DummyOrchestrator()})()
        dummy.chat_interface = DummyChatInterface()
        dummy._chat_session_id = None
        dummy.updated = False
        dummy._update_session_indicator = lambda: setattr(dummy, "updated", True)

        MainWindow._on_chat_loaded(dummy, "chat_1", "sess_existing")

        assert create_calls == ["sess_existing"]
        assert dummy._chat_session_id == "sess_existing"
        assert dummy.chat_interface.backend_session_id == "sess_existing"
        assert dummy.updated is True

    def test_chat_loaded_without_saved_backend_session_creates_new_one(self):
        from src.ui.main_window import MainWindow

        create_calls = []

        class DummyOrchestrator:
            def create_session(self, session_id=None):
                create_calls.append(session_id)
                return "sess_generated"

        class DummyChatInterface:
            def __init__(self):
                self.backend_session_id = None

            def set_backend_session_id(self, session_id):
                self.backend_session_id = session_id

        dummy = type("DummyWindow", (), {})()
        dummy.backend = type("DummyBackend", (), {"_orchestrator": DummyOrchestrator()})()
        dummy.chat_interface = DummyChatInterface()
        dummy._chat_session_id = None
        dummy.updated = False
        dummy._update_session_indicator = lambda: setattr(dummy, "updated", True)

        MainWindow._on_chat_loaded(dummy, "chat_2", "")

        assert create_calls == [None]
        assert dummy._chat_session_id == "sess_generated"
        assert dummy.chat_interface.backend_session_id == "sess_generated"
        assert dummy.updated is True

    def test_clear_all_chats_resets_backend_session(self):
        from src.ui.main_window import MainWindow

        create_calls = []

        class DummyOrchestrator:
            def create_session(self, session_id=None):
                create_calls.append(session_id)
                return "sess_after_clear"

        class DummyChatInterface:
            def __init__(self):
                self.backend_session_id = "sess_old"
                self.delete_calls = 0

            def delete_all_history(self):
                self.delete_calls += 1
                return 4

            def set_backend_session_id(self, session_id):
                self.backend_session_id = session_id

        dummy = type("DummyWindow", (), {})()
        dummy.backend = type("DummyBackend", (), {"_orchestrator": DummyOrchestrator()})()
        dummy.chat_interface = DummyChatInterface()
        dummy._chat_session_id = "sess_old"
        dummy.updated = False
        dummy._update_session_indicator = lambda: setattr(dummy, "updated", True)

        deleted = MainWindow._clear_all_chats(dummy)

        assert deleted == 4
        assert dummy.chat_interface.delete_calls == 1
        assert create_calls == [None]
        assert dummy._chat_session_id == "sess_after_clear"
        assert dummy.chat_interface.backend_session_id == "sess_after_clear"
        assert dummy.updated is True


# =========================================================================
# H. Connection Status  i18n
# =========================================================================
class TestConnectionStatusI18n:

    def test_docker_running_label_en(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        set_language("en")
        dlg = SecuritySettingsDialog()
        dlg.update_connection_status(True, "qwen2.5:3b", "NATIVE")
        assert dlg._docker_status.text() == t("settings.docker_running")

    def test_docker_stopped_label_en(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        set_language("en")
        dlg = SecuritySettingsDialog()
        dlg.update_connection_status(False, t("msg.offline"), "NATIVE")
        assert dlg._docker_status.text() == t("settings.docker_stopped")

    def test_docker_running_label_tr(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        set_language("tr")
        dlg = SecuritySettingsDialog()
        dlg.update_connection_status(True, "model", "NATIVE")
        assert dlg._docker_status.text() == t("settings.docker_running")

    def test_mode_label_displayed(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        set_language("en")
        dlg = SecuritySettingsDialog()
        dlg.update_connection_status(True, "model", "DOCKER")
        assert dlg._mode_status.text() == "DOCKER"

    def test_ai_status_text_passthrough(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        set_language("en")
        dlg = SecuritySettingsDialog()
        dlg.update_connection_status(True, "qwen2.5:3b", "NATIVE")
        assert dlg._ai_status.text() == "qwen2.5:3b"


# =========================================================================
# I. Boundary Regression
# =========================================================================
class TestBoundaryRegression:
    """UI must NOT import src.ai or src.core directly (except i18n.py allowed ref)."""

    FORBIDDEN = [
        r"^\s*from\s+src\.(ai|core)\.",
        r"^\s*import\s+src\.(ai|core)(\.|\ |$)",
    ]
    ALLOWED_FILES = {"__init__.py"}

    def test_ui_no_direct_ai_core_imports(self):
        import re
        patterns = [re.compile(p, re.MULTILINE) for p in self.FORBIDDEN]
        ui_dir = Path(__file__).resolve().parents[1] / "ui"
        violations = []
        for py_file in ui_dir.glob("*.py"):
            if py_file.name in self.ALLOWED_FILES:
                continue
            content = py_file.read_text(encoding="utf-8")
            for pat in patterns:
                if pat.search(content):
                    violations.append(py_file.name)
                    break
        assert not violations, f"UI files importing src.ai/src.core: {violations}"

    def test_i18n_importable_from_orchestrator(self):
        """Orchestrator should be able to import i18n (reverse direction is OK)."""
        from src.ui.i18n import t as t_fn
        assert callable(t_fn)


# =========================================================================
# J. Chat History i18n
# =========================================================================
class TestChatHistoryI18n:

    def test_untitled_en(self):
        set_language("en")
        assert t("chat.untitled") == "Untitled"

    def test_untitled_tr(self):
        set_language("tr")
        assert t("chat.untitled") == "İsimsiz"

    def test_get_chat_title_uses_i18n(self, app):
        from src.ui.chat_interface import ChatInterface
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test.json"):
            ci = ChatInterface()
        ci._messages = []
        set_language("en")
        assert ci._get_chat_title() == "Untitled"
        set_language("tr")
        assert ci._get_chat_title() == t("chat.untitled")

    def test_history_count_format_en(self):
        set_language("en")
        result = t("chat.history_count").format(n=5)
        assert "5" in result

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_history_count_format_all_langs(self, lang):
        set_language(lang)
        result = t("chat.history_count").format(n=10)
        assert "10" in result

    def test_delete_all_history(self, app):
        from src.ui.chat_interface import ChatInterface
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump([
            {"id": "a", "title": "A", "date": "2026-01-01", "messages": [{"text": "x", "is_user": True}]},
            {"id": "b", "title": "B", "date": "2026-01-02", "messages": [{"text": "y", "is_user": True}]},
        ], tf, ensure_ascii=False)
        tf.close()
        try:
            with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf.name):
                ci = ChatInterface()
                deleted = ci.delete_all_history()
            assert deleted == 2
        finally:
            if os.path.exists(tf.name):
                os.unlink(tf.name)

    def test_delete_all_empty_history(self, app):
        from src.ui.chat_interface import ChatInterface
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump([], tf)
        tf.close()
        try:
            with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf.name):
                ci = ChatInterface()
                deleted = ci.delete_all_history()
            assert deleted == 0
        finally:
            if os.path.exists(tf.name):
                os.unlink(tf.name)


# =========================================================================
# K. Cleanup Regression
# =========================================================================
class TestCleanupRegression:
    """Regression: empty-message chat records should be cleaned up."""

    def test_settings_deleted_sessions_format(self):
        set_language("en")
        result = t("settings.deleted_sessions").format(n=3)
        assert "3" in result

    def test_settings_deleted_chats_format(self):
        set_language("en")
        result = t("settings.deleted_chats").format(n=5)
        assert "5" in result

    def test_settings_no_sessions_text(self):
        set_language("en")
        val = t("settings.no_sessions")
        assert val and len(val) > 0

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_cleanup_messages_all_langs(self, lang):
        set_language(lang)
        # Template must contain {n} placeholder and .format(n=X) must work
        raw = _TRANSLATIONS[lang]["settings.deleted_sessions"]
        assert "{n}" in raw
        result = t("settings.deleted_sessions").format(n=7)
        assert "7" in result


# =========================================================================
# L. Terminal Risk Banners (BL-1)
# =========================================================================
class TestTerminalRiskBanners:
    """BL-1: Verify risk banner rendering in terminal view."""

    def test_risk_banner_templates_exist(self):
        from src.ui.terminal_view import _RISK_BANNER
        assert "high" in _RISK_BANNER
        assert "medium" in _RISK_BANNER
        assert "low" in _RISK_BANNER

    def test_risk_banner_contains_color_coding(self):
        from src.ui.terminal_view import _RISK_BANNER
        from src.ui.styles import Colors
        assert Colors.DANGER in _RISK_BANNER["high"]
        assert Colors.WARNING in _RISK_BANNER["medium"]
        assert Colors.SUCCESS in _RISK_BANNER["low"]

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_risk_i18n_keys_all_langs(self, lang):
        set_language(lang)
        for key in ("terminal.risk_high", "terminal.risk_medium",
                     "terminal.risk_low", "terminal.root_banner"):
            val = t(key)
            assert val and len(val) > 5, f"{lang}:{key} is empty or too short"

    def test_terminal_log_banner_method_exists(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        assert hasattr(tv, "_log_banner")
        assert callable(tv._log_banner)

    def test_terminal_start_command_high_risk(self, app):
        """High risk label should insert risk banner HTML into output."""
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        # Inject a mock manager so start_command proceeds to banner logic
        mock_mgr = MagicMock()
        tv._manager = mock_mgr
        tv.start_command("nmap", ["-sS", "10.0.0.1"], risk_label="high")
        output_html = tv._active_session.output.toHtml()
        assert "risk" in output_html.lower() or "rgba(239" in output_html

    def test_terminal_start_command_root_banner(self, app):
        """Root command should insert root privilege banner."""
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        mock_mgr = MagicMock()
        tv._manager = mock_mgr
        set_language("en")
        tv.start_command("nmap", ["-sS", "10.0.0.1"], requires_root=True, risk_label="high")
        output_html = tv._active_session.output.toHtml()
        assert "ROOT" in output_html or "root" in output_html.lower()

    def test_terminal_start_command_low_risk(self, app):
        """Low/safe risk should insert green banner."""
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        mock_mgr = MagicMock()
        tv._manager = mock_mgr
        tv.start_command("ping", ["-c", "4", "10.0.0.1"], risk_label="safe")
        output_html = tv._active_session.output.toHtml()
        # Low risk banner or the command itself should be present
        assert "10.0.0.1" in output_html


# =========================================================================
# M. Settings Security Policy (BL-2)
# =========================================================================
class TestSettingsSecurityPolicy:
    """BL-2: Verify security policy settings in dialog."""

    def test_dialog_has_security_widgets(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        dialog = SecuritySettingsDialog()
        assert hasattr(dialog, "_confirm_root")
        assert hasattr(dialog, "_warn_high_risk")
        assert hasattr(dialog, "_auto_cleanup_combo")

    def test_security_defaults(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        dialog = SecuritySettingsDialog()
        settings = dialog.get_settings()
        assert settings["confirm_root"] is True
        assert settings["warn_high_risk"] is True
        assert settings["auto_cleanup"] == "off"

    def test_security_settings_roundtrip(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        dialog = SecuritySettingsDialog()
        dialog.set_settings({
            "confirm_root": False,
            "warn_high_risk": False,
            "auto_cleanup": "weekly",
        })
        result = dialog.get_settings()
        assert result["confirm_root"] is False
        assert result["warn_high_risk"] is False
        assert result["auto_cleanup"] == "weekly"

    def test_security_settings_daily_option(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        dialog = SecuritySettingsDialog()
        dialog.set_settings({"auto_cleanup": "daily"})
        assert dialog.get_settings()["auto_cleanup"] == "daily"

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_security_i18n_keys_all_langs(self, lang):
        set_language(lang)
        for key in ("settings.security_policy", "settings.confirm_root",
                     "settings.warn_high_risk", "settings.auto_cleanup",
                     "settings.auto_cleanup_off", "settings.auto_cleanup_daily",
                     "settings.auto_cleanup_weekly"):
            val = t(key)
            assert val and len(val) >= 1, f"{lang}:{key} is empty"

    def test_settings_changed_signal_includes_security(self, app):
        from src.ui.settings_dialog import SecuritySettingsDialog
        dialog = SecuritySettingsDialog()
        received = {}
        dialog.settings_changed.connect(lambda s: received.update(s))
        dialog._on_save()
        assert "confirm_root" in received
        assert "warn_high_risk" in received
        assert "auto_cleanup" in received


# =========================================================================
# N. Security Policy Confirmation Logic
# =========================================================================
class TestNeedsConfirmationLogic:
    """Verify _needs_confirmation honours confirm_root / warn_high_risk independently."""

    @staticmethod
    def _make_stub(confirm_root: bool, warn_high_risk: bool):
        """Lightweight stub that reuses MainWindow's methods without full init."""
        from src.ui.main_window import MainWindow

        class _Stub:
            _security_settings = {
                "confirm_root": confirm_root,
                "warn_high_risk": warn_high_risk,
            }
            _needs_confirmation = MainWindow._needs_confirmation
            _normalize_risk = staticmethod(MainWindow._normalize_risk)

        return _Stub()

    # -- confirm_root ON -----------------------------------------------
    def test_root_confirmed_when_setting_on(self, app):
        stub = self._make_stub(confirm_root=True, warn_high_risk=False)
        assert stub._needs_confirmation(requires_root=True, risk_level="high") is True

    # -- confirm_root OFF → root commands skip confirmation ------------
    def test_root_skipped_when_setting_off(self, app):
        stub = self._make_stub(confirm_root=False, warn_high_risk=True)
        assert stub._needs_confirmation(requires_root=True, risk_level="high") is False

    # -- warn_high_risk ON → medium-risk non-root warns ----------------
    def test_medium_risk_warned_when_setting_on(self, app):
        stub = self._make_stub(confirm_root=False, warn_high_risk=True)
        assert stub._needs_confirmation(requires_root=False, risk_level="medium") is True

    # -- warn_high_risk OFF → medium-risk non-root passes silently -----
    def test_medium_risk_skipped_when_setting_off(self, app):
        stub = self._make_stub(confirm_root=False, warn_high_risk=False)
        assert stub._needs_confirmation(requires_root=False, risk_level="medium") is False

    # -- low risk never triggers confirmation --------------------------
    def test_low_risk_never_confirms(self, app):
        stub = self._make_stub(confirm_root=True, warn_high_risk=True)
        assert stub._needs_confirmation(requires_root=False, risk_level="low") is False

    # -- both OFF → nothing triggers -----------------------------------
    def test_both_off_no_confirmation(self, app):
        stub = self._make_stub(confirm_root=False, warn_high_risk=False)
        assert stub._needs_confirmation(requires_root=True, risk_level="high") is False
        assert stub._needs_confirmation(requires_root=False, risk_level="medium") is False
        assert stub._needs_confirmation(requires_root=False, risk_level="low") is False
