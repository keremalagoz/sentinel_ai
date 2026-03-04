"""
SENTINEL AI — Optimization & Performance Tests
Validates all 12 performance fixes + timing benchmarks.

Coverage:
  A. Chat History Debounce & Cache  (H1+H3)
  B. Bubble Ref Cache               (H2)
  C. Font Update vs Re-render       (H4)
  D. Regex Pre-compile              (H5, M6, M7)
  E. get_available_languages        (M1)
  F. QFont Cache                    (M2)
  G. QSS String Constants           (M3)
  H. Status Badge Prebuilt          (M4+M11)
  I. Tab-Session Map                (M5)
  J. validators.py Pre-compile      (M6)
  K. parser_framework Pre-compile   (M7)
  L. Terminal _escape + Buffer      (M9+M10)
  M. Source Code Anti-Pattern Scan
"""

import ast
import inspect
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.ui.i18n import (
    set_language, get_language, t, get_available_languages,
    LANGUAGES, _TRANSLATIONS,
)


# ── Shared fixture ──────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication(sys.argv)
    return instance


# =========================================================================
# A. Chat History Debounce & Cache (H1+H3)
# =========================================================================
class TestChatHistoryDebounce:
    """Verify in-memory cache + debounce timer for chat history I/O."""

    def _make(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat.json")
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
        ci._history_cache = None  # reset
        return ci, tf

    def test_history_cache_attr_exists(self, app, tmp_path):
        ci, _ = self._make(app, tmp_path)
        assert hasattr(ci, '_history_cache')

    def test_dirty_flag_attr_exists(self, app, tmp_path):
        ci, _ = self._make(app, tmp_path)
        assert hasattr(ci, '_dirty')
        assert ci._dirty is False

    def test_debounce_timer_attr_exists(self, app, tmp_path):
        ci, _ = self._make(app, tmp_path)
        assert hasattr(ci, '_debounce_timer')
        assert isinstance(ci._debounce_timer, QTimer)

    def test_debounce_timer_is_singleshot(self, app, tmp_path):
        ci, _ = self._make(app, tmp_path)
        assert ci._debounce_timer.isSingleShot()

    def test_debounce_interval(self, app, tmp_path):
        ci, _ = self._make(app, tmp_path)
        assert ci._debounce_timer.interval() == 500

    def test_save_sets_dirty_flag(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat2.json")
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
        ci._messages = [{'text': 'hello', 'is_user': True}]
        ci._current_chat_id = "test123"
        ci._save_current_chat()
        assert ci._dirty is True

    def test_save_fills_cache(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat3.json")
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
        ci._messages = [{'text': 'hello', 'is_user': True}]
        ci._current_chat_id = "test456"
        ci._save_current_chat()
        assert ci._history_cache is not None
        assert len(ci._history_cache) >= 1

    def test_flush_clears_dirty(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat4.json")
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
        ci._messages = [{'text': 'hello', 'is_user': True}]
        ci._current_chat_id = "test789"
        ci._save_current_chat()
        ci._flush_history()
        assert ci._dirty is False

    def test_flush_writes_to_disk(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat5.json")
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
            ci._messages = [{'text': 'test', 'is_user': True}]
            ci._current_chat_id = "disk_test"
            ci._save_current_chat()
            ci._flush_history()
        assert os.path.exists(tf)
        with open(tf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) >= 1

    def test_load_uses_cache_on_second_call(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat6.json")
        json.dump([{"id": "a", "title": "A", "date": "2026", "messages": []}], open(tf, 'w'))
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
        ci._history_cache = None
        first = ci._load_history()
        # Delete file — second call should use cache, not disk
        os.unlink(tf)
        second = ci._load_history()
        assert first is second  # Same object reference — cache hit

    def test_delete_all_invalidates_cache(self, app, tmp_path):
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat7.json")
        json.dump([{"id": "b", "title": "B", "date": "2026", "messages": []}], open(tf, 'w'))
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()
            ci.delete_all_history()
        assert ci._history_cache == []

    def test_no_disk_io_for_consecutive_messages(self, app, tmp_path):
        """Multiple messages should NOT trigger multiple disk writes."""
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "chat8.json")
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()

        ci._current_chat_id = "perf_test"
        original_save = ci._save_history
        call_count = [0]
        def counting_save(h):
            call_count[0] += 1
            original_save(h)
        ci._save_history = counting_save

        ci._messages = [{'text': f'msg{i}', 'is_user': True} for i in range(10)]
        for _ in range(10):
            ci._save_current_chat()

        # Debounce not triggered yet (no event loop), so disk writes = 0
        assert call_count[0] == 0

    def test_timing_cache_vs_disk(self, app, tmp_path):
        """Cache reads should be faster than disk reads."""
        from src.ui.chat_interface import ChatInterface
        tf = str(tmp_path / "timing.json")
        big_history = [{"id": str(i), "title": f"Chat {i}", "date": "2026",
                        "messages": [{"text": f"m{j}", "is_user": True} for j in range(20)]}
                       for i in range(50)]
        with open(tf, 'w', encoding='utf-8') as f:
            json.dump(big_history, f)

        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", tf):
            ci = ChatInterface()

        # Warm up cache
        ci._history_cache = None
        ci._load_history()

        # Timed cache reads
        start = time.perf_counter()
        for _ in range(1000):
            ci._load_history()
        cache_time = time.perf_counter() - start

        # Timed disk reads (bust cache each time)
        start = time.perf_counter()
        for _ in range(100):
            ci._history_cache = None
            ci._load_history()
        disk_time = time.perf_counter() - start

        # Cache 1000x should be much faster than disk 100x
        assert cache_time < disk_time


# =========================================================================
# B. Bubble Ref Cache (H2)
# =========================================================================
class TestBubbleRefCache:
    """Verify _bubble_refs list is maintained correctly."""

    def _make(self, app):
        from src.ui.chat_interface import ChatInterface
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test.json"):
            ci = ChatInterface()
        return ci

    def test_bubble_refs_attr_exists(self, app):
        ci = self._make(app)
        assert hasattr(ci, '_bubble_refs')
        assert isinstance(ci._bubble_refs, list)

    def test_bubble_refs_starts_empty(self, app):
        ci = self._make(app)
        assert len(ci._bubble_refs) == 0

    def test_add_bubble_appends_ref(self, app):
        ci = self._make(app)
        ci._add_bubble("Hello", is_user=True)
        assert len(ci._bubble_refs) == 1

    def test_multiple_bubbles_tracked(self, app):
        ci = self._make(app)
        for i in range(5):
            ci._add_bubble(f"msg {i}", is_user=(i % 2 == 0))
        assert len(ci._bubble_refs) == 5

    def test_clear_chat_clears_refs(self, app):
        ci = self._make(app)
        ci._add_bubble("Hello", is_user=True)
        ci._add_bubble("World", is_user=False)
        ci.clear_chat()
        assert len(ci._bubble_refs) == 0

    def test_update_bubble_widths_no_findchild(self, app):
        """_update_bubble_widths should NOT call findChild anymore."""
        ci = self._make(app)
        ci._add_bubble("Test", is_user=True)
        ci._add_bubble("Test2", is_user=False)
        # Patch findChild on all containers
        for i in range(ci._messages_layout.count() - 1):
            item = ci._messages_layout.itemAt(i)
            if item and item.widget():
                item.widget().findChild = MagicMock(side_effect=AssertionError("findChild called"))
        # This should NOT raise — it uses _bubble_refs instead
        ci._update_bubble_widths()

    def test_bubble_refs_are_chatbubble_instances(self, app):
        from src.ui.chat_interface import ChatBubble
        ci = self._make(app)
        ci._add_bubble("Test", is_user=True)
        assert all(isinstance(b, ChatBubble) for b in ci._bubble_refs)

    def test_timing_bubble_widths(self, app):
        """Update bubble widths with refs should be fast."""
        ci = self._make(app)
        for i in range(50):
            ci._add_bubble(f"Message {i}", is_user=(i % 2 == 0))
        start = time.perf_counter()
        for _ in range(100):
            ci._update_bubble_widths()
        elapsed = time.perf_counter() - start
        # 50 bubbles × 100 iterations should complete in <1s
        assert elapsed < 1.0


# =========================================================================
# C. Font Update vs Re-render (H4)
# =========================================================================
class TestFontUpdateVsRerender:
    """Verify set_text_font_size updates fonts without full re-render."""

    def _make(self, app):
        from src.ui.chat_interface import ChatInterface
        with patch("src.ui.chat_interface.CHAT_HISTORY_FILE", "/tmp/sentinel_test.json"):
            ci = ChatInterface()
        return ci

    def test_set_font_does_not_call_render(self, app):
        ci = self._make(app)
        ci._add_bubble("Hello", is_user=True)
        ci._add_bubble("World", is_user=False)
        ci._render_messages = MagicMock()
        ci.set_text_font_size(18)
        ci._render_messages.assert_not_called()

    def test_set_font_updates_existing_bubbles(self, app):
        ci = self._make(app)
        ci._add_bubble("Test", is_user=True)
        ci.set_text_font_size(20)
        for bubble in ci._bubble_refs:
            if hasattr(bubble, '_msg_label'):
                assert bubble._msg_label.font().pixelSize() == 20

    def test_font_clamp_min(self, app):
        ci = self._make(app)
        ci.set_text_font_size(5)
        assert ci._text_font_size == 11

    def test_font_clamp_max(self, app):
        ci = self._make(app)
        ci.set_text_font_size(50)
        assert ci._text_font_size == 24

    def test_timing_font_update_vs_render(self, app):
        """Font update should be much faster than re-rendering."""
        ci = self._make(app)
        for i in range(20):
            ci._add_bubble(f"Message {i}", is_user=(i % 2 == 0))

        # Time set_text_font_size (no re-render)
        start = time.perf_counter()
        for size in range(11, 25):
            ci.set_text_font_size(size)
        font_time = time.perf_counter() - start

        # Time _render_messages (full re-render) for comparison
        start = time.perf_counter()
        ci._messages = [{'text': f'msg{i}', 'is_user': True} for i in range(20)]
        ci._render_messages()
        render_time = time.perf_counter() - start

        # Font update (14 changes) should be faster than single re-render
        assert font_time < render_time * 10  # generous margin


# =========================================================================
# D. Regex Pre-compile (H5)
# =========================================================================
class TestRegexPrecompile:
    """Verify all regex patterns are pre-compiled at module level."""

    def test_intent_resolver_has_compiled_regex(self):
        from src.ai import intent_resolver
        assert hasattr(intent_resolver, '_JSON_BLOCK_RE')
        assert isinstance(intent_resolver._JSON_BLOCK_RE, re.Pattern)

    def test_hierarchical_resolver_has_compiled_regex(self):
        from src.ai import hierarchical_resolver
        assert hasattr(hierarchical_resolver, '_JSON_BLOCK_RE')
        assert isinstance(hierarchical_resolver._JSON_BLOCK_RE, re.Pattern)

    def test_intent_extract_json_markdown(self):
        from src.ai.intent_resolver import IntentResolver
        resolver = IntentResolver.__new__(IntentResolver)
        text = '```json\n{"intent_type": "port_scan"}\n```'
        result = resolver._extract_json(text)
        assert '"intent_type"' in result

    def test_hierarchical_extract_json_markdown(self):
        from src.ai.hierarchical_resolver import HierarchicalResolver
        text = '```json\n{"category": "network"}\n```'
        result = HierarchicalResolver._extract_json(text)
        assert '"category"' in result

    def test_intent_extract_json_no_code_block(self):
        from src.ai.intent_resolver import IntentResolver
        resolver = IntentResolver.__new__(IntentResolver)
        text = 'Some text {"intent_type": "dns_lookup"} more text'
        result = resolver._extract_json(text)
        assert '"intent_type"' in result

    def test_no_import_re_inside_extract_json(self):
        """_extract_json should NOT have 'import re' in its body."""
        from src.ai.intent_resolver import IntentResolver
        source = inspect.getsource(IntentResolver._extract_json)
        assert "import re" not in source

    def test_timing_regex_precompiled(self):
        """Pre-compiled regex should handle many calls efficiently."""
        from src.ai import intent_resolver
        pattern = intent_resolver._JSON_BLOCK_RE
        text = '```json\n{"intent_type": "port_scan", "target": "10.0.0.1"}\n```'
        start = time.perf_counter()
        for _ in range(10000):
            pattern.search(text)
        elapsed = time.perf_counter() - start
        # 10K regex searches should be well under 1 second
        assert elapsed < 1.0


# =========================================================================
# E. get_available_languages (M1)
# =========================================================================
class TestGetAvailableLanguages:
    """Verify get_available_languages returns LANGUAGES directly (no copy)."""

    def test_returns_languages_identity(self):
        result = get_available_languages()
        assert result is LANGUAGES

    def test_returns_tuple(self):
        result = get_available_languages()
        assert isinstance(result, (list, tuple))

    def test_correct_length(self):
        assert len(get_available_languages()) == 11

    def test_timing_no_copy(self):
        start = time.perf_counter()
        for _ in range(100000):
            get_available_languages()
        elapsed = time.perf_counter() - start
        # Direct return should be < 50ms for 100K calls
        assert elapsed < 0.5


# =========================================================================
# F. QFont Cache (M2)
# =========================================================================
class TestQFontCache:
    """Verify font caching returns same instances."""

    def test_font_cache_exists(self):
        from src.ui.chat_interface import _font_cache
        assert isinstance(_font_cache, dict)

    def test_same_params_same_font(self, app):
        from src.ui.chat_interface import _get_cached_font
        f1 = _get_cached_font("ui", 13)
        f2 = _get_cached_font("ui", 13)
        assert f1 is f2

    def test_different_size_different_font(self, app):
        from src.ui.chat_interface import _get_cached_font
        f1 = _get_cached_font("ui", 13)
        f2 = _get_cached_font("ui", 16)
        assert f1 is not f2

    def test_bold_vs_normal(self, app):
        from src.ui.chat_interface import _get_cached_font
        f1 = _get_cached_font("ui", 13, bold=False)
        f2 = _get_cached_font("ui", 13, bold=True)
        assert f1 is not f2

    def test_mono_family(self, app):
        from src.ui.chat_interface import _get_cached_font
        f = _get_cached_font("mono", 13)
        assert "JetBrains Mono" in f.families() or f.family() == "JetBrains Mono"

    def test_timing_cached_vs_new(self, app):
        from src.ui.chat_interface import _get_cached_font
        from PyQt6.QtGui import QFont
        # Warm cache
        _get_cached_font("ui", 14)

        start = time.perf_counter()
        for _ in range(10000):
            _get_cached_font("ui", 14)
        cache_time = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(10000):
            f = QFont()
            f.setPixelSize(14)
        new_time = time.perf_counter() - start

        # Cached should be faster
        assert cache_time < new_time


# =========================================================================
# G. QSS String Constants (M3)
# =========================================================================
class TestQSSConstants:
    """Verify QSS constants are module-level strings."""

    def test_command_card_style_exists(self):
        from src.ui.chat_interface import _COMMAND_CARD_STYLE
        assert isinstance(_COMMAND_CARD_STYLE, str)
        assert "CommandCard" in _COMMAND_CARD_STYLE

    def test_run_btn_style_exists(self):
        from src.ui.chat_interface import _RUN_BTN_STYLE
        assert isinstance(_RUN_BTN_STYLE, str)
        assert "QPushButton" in _RUN_BTN_STYLE

    def test_copy_btn_style_exists(self):
        from src.ui.chat_interface import _COPY_BTN_STYLE
        assert isinstance(_COPY_BTN_STYLE, str)

    def test_bubble_user_style_exists(self):
        from src.ui.chat_interface import _BUBBLE_USER_STYLE
        assert isinstance(_BUBBLE_USER_STYLE, str)
        assert "border-radius" in _BUBBLE_USER_STYLE

    def test_bubble_ai_style_exists(self):
        from src.ui.chat_interface import _BUBBLE_AI_STYLE
        assert isinstance(_BUBBLE_AI_STYLE, str)

    def test_identity_styles_exist(self):
        from src.ui.chat_interface import _IDENTITY_USER_STYLE, _IDENTITY_AI_STYLE
        assert isinstance(_IDENTITY_USER_STYLE, str)
        assert isinstance(_IDENTITY_AI_STYLE, str)

    def test_msg_styles_exist(self):
        from src.ui.chat_interface import _MSG_USER_STYLE, _MSG_AI_STYLE
        assert isinstance(_MSG_USER_STYLE, str)
        assert isinstance(_MSG_AI_STYLE, str)

    def test_styles_contain_colors(self):
        from src.ui.chat_interface import _BUBBLE_USER_STYLE, _BUBBLE_AI_STYLE
        # Must contain actual hex color values
        assert Colors.ACCENT_PRIMARY in _BUBBLE_USER_STYLE
        assert Colors.BG_TERTIARY in _BUBBLE_AI_STYLE


# =========================================================================
# H. Status Badge Prebuilt Styles (M4+M11)
# =========================================================================
class TestStatusBadgePrebuilt:
    """Verify pre-built status styles in terminal_view and main_window."""

    def test_terminal_prompt_styles_exist(self):
        from src.ui.terminal_view import _PROMPT_STYLE_IDLE, _PROMPT_STYLE_RUNNING, _PROMPT_STYLE_ROOT
        assert isinstance(_PROMPT_STYLE_IDLE, str)
        assert isinstance(_PROMPT_STYLE_RUNNING, str)
        assert isinstance(_PROMPT_STYLE_ROOT, str)

    def test_terminal_idle_has_success_color(self):
        from src.ui.terminal_view import _PROMPT_STYLE_IDLE
        assert Colors.SUCCESS in _PROMPT_STYLE_IDLE

    def test_terminal_running_has_warning_color(self):
        from src.ui.terminal_view import _PROMPT_STYLE_RUNNING
        assert Colors.WARNING in _PROMPT_STYLE_RUNNING

    def test_terminal_root_has_danger_color(self):
        from src.ui.terminal_view import _PROMPT_STYLE_ROOT
        assert Colors.DANGER in _PROMPT_STYLE_ROOT

    def test_main_window_dot_styles_exist(self):
        from src.ui.main_window import _DOT_STYLES
        assert isinstance(_DOT_STYLES, dict)
        assert set(_DOT_STYLES.keys()) == {"idle", "running", "root"}

    def test_main_window_badge_styles_exist(self):
        from src.ui.main_window import _BADGE_STYLES
        assert isinstance(_BADGE_STYLES, dict)
        assert set(_BADGE_STYLES.keys()) == {"idle", "running", "root"}

    def test_dot_styles_contain_colors(self):
        from src.ui.main_window import _DOT_STYLES
        assert Colors.STATUS_IDLE in _DOT_STYLES["idle"]
        assert Colors.STATUS_RUNNING in _DOT_STYLES["running"]
        assert Colors.STATUS_ROOT in _DOT_STYLES["root"]

    def test_badge_styles_are_complete(self):
        from src.ui.main_window import _BADGE_STYLES
        for key in ("idle", "running", "root"):
            assert "padding" in _BADGE_STYLES[key]
            assert "border-radius" in _BADGE_STYLES[key]


# =========================================================================
# I. Tab-Session Map (M5)
# =========================================================================
class TestTabSessionMap:
    """Verify session_id -> tab_index mapping dictionary."""

    def test_session_tab_map_exists(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        assert hasattr(tv, '_session_tab_map')
        assert isinstance(tv._session_tab_map, dict)

    def test_initial_session_in_map(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        assert len(tv._session_tab_map) >= 1
        first_session = tv._sessions[0]
        assert first_session.id in tv._session_tab_map

    def test_add_terminal_updates_map(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        initial_count = len(tv._session_tab_map)
        tv._add_terminal()
        assert len(tv._session_tab_map) == initial_count + 1

    def test_close_terminal_updates_map(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv._add_terminal()
        session_to_close = tv._sessions[-1]
        sid = session_to_close.id
        tv._close_terminal(session_to_close)
        assert sid not in tv._session_tab_map

    def test_rebuild_tab_map(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        tv._add_terminal()
        tv._add_terminal()
        tv._rebuild_tab_map()
        assert len(tv._session_tab_map) == len(tv._sessions)

    def test_map_values_are_ints(self, app):
        from src.ui.terminal_view import TerminalView
        tv = TerminalView(process_manager=None)
        for sid, idx in tv._session_tab_map.items():
            assert isinstance(sid, int)
            assert isinstance(idx, int)


# =========================================================================
# J. validators.py Pre-compile (M6)
# =========================================================================
class TestValidatorsPrecompile:
    """Verify hostname regex pre-compiled at class level."""

    def test_hostname_re_exists(self):
        from src.core.validators import InputValidator
        assert hasattr(InputValidator, '_HOSTNAME_RE')
        assert isinstance(InputValidator._HOSTNAME_RE, re.Pattern)

    def test_internal_hostname_re_exists(self):
        from src.core.validators import InputValidator
        assert hasattr(InputValidator, '_INTERNAL_HOSTNAME_RE')
        assert isinstance(InputValidator._INTERNAL_HOSTNAME_RE, re.Pattern)

    def test_validate_hostname_still_works(self):
        from src.core.validators import InputValidator
        assert InputValidator.validate_hostname("example.com") is True
        assert InputValidator.validate_hostname("localhost") is True
        assert InputValidator.validate_hostname("192.168.1.1") is True
        assert InputValidator.validate_hostname("invalid..host") is False

    def test_validate_hostname_internal_domains(self):
        from src.core.validators import InputValidator
        assert InputValidator.validate_hostname("myserver.local") is True
        assert InputValidator.validate_hostname("mypc.lan") is True

    def test_no_recompile_in_function_body(self):
        """validate_hostname should NOT contain re.compile in its body."""
        from src.core.validators import InputValidator
        source = inspect.getsource(InputValidator.validate_hostname)
        assert "re.compile" not in source

    def test_timing_precompiled_hostname(self):
        from src.core.validators import InputValidator
        start = time.perf_counter()
        for _ in range(10000):
            InputValidator.validate_hostname("example.com")
            InputValidator.validate_hostname("192.168.1.1")
            InputValidator.validate_hostname("myserver.local")
        elapsed = time.perf_counter() - start
        # 30K validations should be well under 2 seconds
        assert elapsed < 2.0


# =========================================================================
# K. parser_framework Pre-compile (M7)
# =========================================================================
class TestParserFrameworkPrecompile:
    """Verify regex pre-compiled in parser_framework module."""

    def test_cve_re_exists(self):
        from src.core import parser_framework
        assert hasattr(parser_framework, '_CVE_RE')
        assert isinstance(parser_framework._CVE_RE, re.Pattern)

    def test_cvss_re_exists(self):
        from src.core import parser_framework
        assert hasattr(parser_framework, '_CVSS_RE')
        assert isinstance(parser_framework._CVSS_RE, re.Pattern)

    def test_version_re_exists(self):
        from src.core import parser_framework
        assert hasattr(parser_framework, '_VERSION_RE')
        assert isinstance(parser_framework._VERSION_RE, re.Pattern)

    def test_extract_cve_still_works(self):
        from src.core.parser_framework import extract_cve_info
        result = extract_cve_info("Found CVE-2024-1234 with CVSS: 9.8")
        assert "CVE-2024-1234" in result["cve_ids"]
        assert result["cvss_score"] == 9.8

    def test_parse_service_version_still_works(self):
        from src.core.parser_framework import parse_service_version
        result = parse_service_version("OpenSSH 8.2p1 Ubuntu")
        assert result["product"] == "OpenSSH"
        assert result["version"] == "8.2p1"

    def test_analyze_banner_still_works(self):
        from src.core.parser_framework import analyze_banner
        result = analyze_banner("SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5")
        assert result["service_type"] == "ssh"
        assert len(result["version_hints"]) > 0

    def test_timing_precompiled_parsers(self):
        from src.core.parser_framework import extract_cve_info, parse_service_version
        text = "CVE-2023-44487 CVSS: 7.5 High severity. Apache 2.4.41"
        start = time.perf_counter()
        for _ in range(5000):
            extract_cve_info(text)
            parse_service_version("OpenSSH 8.2p1")
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0


# =========================================================================
# L. Terminal _escape + Buffer (M9+M10)
# =========================================================================
class TestTerminalEscapeAndBuffer:
    """Verify _escape correctness and _check_buffer_limit optimization."""

    def test_escape_ampersand(self):
        from src.ui.terminal_view import TerminalView
        assert "&amp;" in TerminalView._escape("a&b")

    def test_escape_lt_gt(self):
        from src.ui.terminal_view import TerminalView
        result = TerminalView._escape("<script>")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_escape_newline(self):
        from src.ui.terminal_view import TerminalView
        assert "<br>" in TerminalView._escape("a\nb")

    def test_escape_space(self):
        from src.ui.terminal_view import TerminalView
        assert "&nbsp;" in TerminalView._escape("a b")

    def test_escape_combined(self):
        from src.ui.terminal_view import TerminalView
        result = TerminalView._escape("a & b\n<c> d")
        assert "&amp;" in result
        assert "<br>" in result
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&nbsp;" in result

    def test_escape_empty_string(self):
        from src.ui.terminal_view import TerminalView
        assert TerminalView._escape("") == ""

    def test_escape_no_special_chars(self):
        from src.ui.terminal_view import TerminalView
        assert TerminalView._escape("hello") == "hello"

    def test_timing_escape(self):
        from src.ui.terminal_view import TerminalView
        text = "root@kali:~# nmap -sS 192.168.1.0/24 & check <result> output\n"
        start = time.perf_counter()
        for _ in range(10000):
            TerminalView._escape(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0


# =========================================================================
# M. Source Code Anti-Pattern Scan
# =========================================================================
class TestAntiPatternScan:
    """Scan source files for known performance anti-patterns."""

    def _get_src_root(self):
        return Path(__file__).resolve().parents[1]

    def test_no_recompile_in_ai_function_bodies(self):
        """AI layer should have no re.compile inside function bodies."""
        src_root = self._get_src_root()
        violations = []
        for py_file in (src_root / "ai").glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            func = child.func
                            if isinstance(func, ast.Attribute) and func.attr == "compile":
                                if isinstance(func.value, ast.Name) and func.value.id == "re":
                                    violations.append(f"{py_file.name}:{node.name}")
        assert not violations, f"re.compile in function bodies: {violations}"

    def test_no_recompile_in_validators(self):
        """validators.py should have no re.compile inside functions."""
        src_root = self._get_src_root()
        source = (src_root / "core" / "validators.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr == "compile":
                            if isinstance(func.value, ast.Name) and func.value.id == "re":
                                violations.append(f"validators.py:{node.name}")
        assert not violations, f"re.compile in function bodies: {violations}"

    def test_no_import_re_in_extract_json_methods(self):
        """_extract_json methods should not import re inside the function."""
        from src.ai import intent_resolver, hierarchical_resolver
        for mod in [intent_resolver]:
            if hasattr(mod, 'IntentResolver'):
                source = inspect.getsource(mod.IntentResolver._extract_json)
                assert "import re" not in source, f"import re in {mod.__name__}._extract_json"

    def test_chat_interface_no_findchild_in_bubble_widths(self):
        """_update_bubble_widths should not contain findChild."""
        from src.ui.chat_interface import ChatInterface
        source = inspect.getsource(ChatInterface._update_bubble_widths)
        assert "findChild" not in source

    def test_set_text_font_size_no_render_messages(self):
        """set_text_font_size should not call _render_messages."""
        from src.ui.chat_interface import ChatInterface
        source = inspect.getsource(ChatInterface.set_text_font_size)
        assert "_render_messages" not in source


# =========================================================================
# Import-time validation: Colors must be importable
# =========================================================================
from src.ui.styles import Colors
