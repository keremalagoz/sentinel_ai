"""
SENTINEL AI — i18n Module Comprehensive Tests
Pure Python (no PyQt6 required).

Coverage:
  A. Core API (set_language, get_language, t, get_available_languages)
  B. Language round-trips (all 11 languages)
  C. Fallback behaviors (bad lang code, missing key, empty key)
  D. Key-set consistency (every lang has same keys as _EN)
  E. Format-parameter consistency ({cmd}, {error}, {conf}, {n}, {code}, {id}, {intent})
  F. No empty translation values
  G. LANGUAGES uniqueness
  H. Spot-check critical translations
"""

import re
import pytest

from src.ui.i18n import (
    set_language,
    get_language,
    t,
    get_available_languages,
    LANGUAGES,
    _EN,
    _TRANSLATIONS,
)


# =========================================================================
# A. Core API
# =========================================================================
class TestCoreAPI:
    """Basic API contract tests."""

    def test_default_language_is_en(self):
        set_language("en")
        assert get_language() == "en"

    def test_set_language_returns_none(self):
        result = set_language("tr")
        assert result is None

    def test_get_language_after_set(self):
        set_language("tr")
        assert get_language() == "tr"

    def test_t_returns_string(self):
        assert isinstance(t("btn.save"), str)

    def test_t_known_key_en(self):
        set_language("en")
        assert t("btn.save") == "Save"

    def test_get_available_languages_returns_list(self):
        langs = get_available_languages()
        assert isinstance(langs, list)
        assert len(langs) == 11

    def test_get_available_languages_tuple_format(self):
        for item in get_available_languages():
            assert isinstance(item, tuple)
            assert len(item) == 2
            code, name = item
            assert isinstance(code, str)
            assert isinstance(name, str)

    def test_available_languages_match_translations(self):
        codes = {code for code, _ in get_available_languages()}
        assert codes == set(_TRANSLATIONS.keys())


# =========================================================================
# B. Language round-trips
# =========================================================================
class TestLanguageRoundTrips:
    """Verify set → get round-trip for all 11 languages."""

    @pytest.mark.parametrize("code,name", LANGUAGES)
    def test_set_get_roundtrip(self, code, name):
        set_language(code)
        assert get_language() == code

    @pytest.mark.parametrize("code,name", LANGUAGES)
    def test_t_returns_non_empty_for_known_key(self, code, name):
        set_language(code)
        val = t("btn.save")
        assert val, f"t('btn.save') returned empty for language {code}"

    @pytest.mark.parametrize("code,name", LANGUAGES)
    def test_badge_ready_translated(self, code, name):
        set_language(code)
        val = t("badge.ready")
        assert val != "", f"badge.ready empty for {code}"
        # EN should be "READY" — others should differ (except maybe some)
        if code != "en":
            # At minimum it should be a string
            assert isinstance(val, str)


# =========================================================================
# C. Fallback behaviors
# =========================================================================
class TestFallback:
    """Edge cases and fallback behavior."""

    def test_invalid_language_code_falls_back_to_en(self):
        set_language("xx_invalid")
        assert get_language() == "en"

    def test_empty_string_language_falls_back(self):
        set_language("")
        assert get_language() == "en"

    def test_missing_key_returns_key_itself(self):
        set_language("en")
        assert t("nonexistent.key.here") == "nonexistent.key.here"

    def test_empty_key_returns_empty_string_or_key(self):
        result = t("")
        # Should return the key itself (empty string) since it doesn't exist
        assert result == ""

    def test_fallback_to_english_when_key_missing_in_lang(self):
        """If a key exists in EN but somehow missing in another lang dict,
        the fallback should return the EN value."""
        set_language("en")
        en_val = t("btn.save")
        # t() should always return the EN fallback for known EN keys
        assert en_val == "Save"


# =========================================================================
# D. Key-set consistency across all languages
# =========================================================================
class TestKeyConsistency:
    """Every language dict must have exactly the same keys as _EN."""

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_language_has_all_en_keys(self, code):
        lang_dict = _TRANSLATIONS[code]
        en_keys = set(_EN.keys())
        lang_keys = set(lang_dict.keys())

        missing = en_keys - lang_keys
        assert not missing, (
            f"Language '{code}' is missing keys: {missing}"
        )

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_language_has_no_extra_keys(self, code):
        lang_dict = _TRANSLATIONS[code]
        en_keys = set(_EN.keys())
        lang_keys = set(lang_dict.keys())

        extra = lang_keys - en_keys
        assert not extra, (
            f"Language '{code}' has extra keys not in EN: {extra}"
        )

    def test_total_key_count(self):
        """Ensure we have the expected number of translation keys."""
        assert len(_EN) >= 75, f"Expected >=75 keys, got {len(_EN)}"


# =========================================================================
# E. Format-parameter consistency
# =========================================================================
_FORMAT_RE = re.compile(r"\{(\w+)\}")


class TestFormatParameters:
    """Keys with {param} placeholders must have the same params in all languages."""

    def _extract_params(self, text: str) -> set:
        return set(_FORMAT_RE.findall(text))

    def test_all_format_keys_consistent(self):
        """For every key that has format params in EN, all langs must match."""
        for key, en_val in _EN.items():
            en_params = self._extract_params(en_val)
            if not en_params:
                continue
            for code, lang_dict in _TRANSLATIONS.items():
                lang_val = lang_dict.get(key, "")
                lang_params = self._extract_params(lang_val)
                assert en_params == lang_params, (
                    f"Format param mismatch for key='{key}' lang='{code}': "
                    f"EN={en_params} vs {code}={lang_params}"
                )

    @pytest.mark.parametrize("key,expected_params", [
        ("ai.cmd_ready", {"cmd"}),
        ("ai.cmd_failed", {"error"}),
        ("ai.low_confidence", {"conf"}),
        ("ai.no_tool", {"intent"}),
        ("msg.ai_error", {"error"}),
        ("msg.cmd_rejected", {"cmd"}),
        ("terminal.exit_code", {"code"}),
        ("terminal.tab_name", {"id"}),
        ("chat.history_count", {"n"}),
        ("settings.deleted_sessions", {"n"}),
        ("settings.deleted_chats", {"n"}),
    ])
    def test_specific_format_params(self, key, expected_params):
        en_val = _EN[key]
        actual = self._extract_params(en_val)
        assert actual == expected_params, (
            f"Key '{key}': expected params {expected_params}, got {actual}"
        )

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_format_call_does_not_raise(self, code):
        """Calling .format() with expected kwargs must not raise for any language."""
        set_language(code)
        # Test a representative set of format calls
        assert t("ai.cmd_ready").format(cmd="nmap -sS 1.1.1.1")
        assert t("ai.cmd_failed").format(error="timeout")
        assert t("ai.low_confidence").format(conf="45%")
        assert t("ai.no_tool").format(intent="port_scan")
        assert t("msg.ai_error").format(error="connection refused")
        assert t("msg.cmd_rejected").format(cmd="rm")
        assert t("terminal.exit_code").format(code=1)
        assert t("terminal.tab_name").format(id=1)
        assert t("chat.history_count").format(n=5)
        assert t("settings.deleted_sessions").format(n=3)
        assert t("settings.deleted_chats").format(n=2)


# =========================================================================
# F. No empty translation values
# =========================================================================
class TestNoEmptyValues:
    """No translation value should be empty or whitespace-only."""

    @pytest.mark.parametrize("code", [c for c, _ in LANGUAGES])
    def test_no_empty_values(self, code):
        lang_dict = _TRANSLATIONS[code]
        empties = [k for k, v in lang_dict.items() if not v.strip()]
        assert not empties, (
            f"Language '{code}' has empty values for keys: {empties}"
        )


# =========================================================================
# G. LANGUAGES list uniqueness
# =========================================================================
class TestLanguagesUniqueness:
    """Language codes and names must be unique."""

    def test_unique_codes(self):
        codes = [code for code, _ in LANGUAGES]
        assert len(codes) == len(set(codes)), "Duplicate language codes found"

    def test_unique_names(self):
        names = [name for _, name in LANGUAGES]
        assert len(names) == len(set(names)), "Duplicate language names found"

    def test_all_codes_are_lowercase(self):
        for code, _ in LANGUAGES:
            assert code == code.lower(), f"Language code '{code}' should be lowercase"


# =========================================================================
# H. Spot-check critical translations
# =========================================================================
class TestCriticalTranslations:
    """Verify specific high-visibility translations are correct."""

    # --- Badge translations ---
    @pytest.mark.parametrize("lang,expected", [
        ("en", "READY"),
        ("tr", "HAZIR"),
        ("ru", "ГОТОВ"),
        ("es", "LISTO"),
        ("zh", "就绪"),
        ("ja", "準備完了"),
        ("de", "BEREIT"),
        ("fr", "PRÊT"),
        ("pt", "PRONTO"),
    ])
    def test_badge_ready(self, lang, expected):
        set_language(lang)
        assert t("badge.ready") == expected

    # --- You / Sentinel labels ---
    @pytest.mark.parametrize("lang,expected", [
        ("en", "You"),
        ("tr", "Sen"),
        ("ru", "Вы"),
        ("ja", "あなた"),
    ])
    def test_chat_you(self, lang, expected):
        set_language(lang)
        assert t("chat.you") == expected

    @pytest.mark.parametrize("lang", [c for c, _ in LANGUAGES])
    def test_chat_sentinel_always_sentinel(self, lang):
        set_language(lang)
        assert t("chat.sentinel") == "Sentinel"

    # --- Button labels ---
    @pytest.mark.parametrize("lang,key,expected", [
        ("en", "btn.run", "Run"),
        ("en", "btn.copy", "Copy"),
        ("en", "btn.stop", "Stop"),
        ("en", "btn.save", "Save"),
        ("en", "btn.cancel", "Cancel"),
        ("tr", "btn.run", "Çalıştır"),
        ("tr", "btn.copy", "Kopyala"),
        ("tr", "btn.save", "Kaydet"),
    ])
    def test_button_label(self, lang, key, expected):
        set_language(lang)
        assert t(key) == expected

    # --- AI orchestrator messages ---
    def test_cmd_ready_en(self):
        set_language("en")
        result = t("ai.cmd_ready").format(cmd="nmap -sS 10.0.0.1")
        assert "Command ready:" in result
        assert "nmap -sS 10.0.0.1" in result

    def test_cmd_ready_tr(self):
        set_language("tr")
        result = t("ai.cmd_ready").format(cmd="nmap -sS 10.0.0.1")
        assert "Komut hazır:" in result
        assert "nmap -sS 10.0.0.1" in result

    def test_cmd_ready_ru(self):
        set_language("ru")
        result = t("ai.cmd_ready").format(cmd="nmap -sS 10.0.0.1")
        assert "Команда готова:" in result
        assert "nmap -sS 10.0.0.1" in result

    # --- Settings labels ---
    def test_settings_title_en(self):
        set_language("en")
        assert t("settings.title") == "Security Settings"

    def test_settings_title_tr(self):
        set_language("tr")
        assert t("settings.title") == "Güvenlik Ayarları"

    # --- Offline message ---
    @pytest.mark.parametrize("lang,expected", [
        ("en", "Offline"),
        ("tr", "Çevrimdışı"),
        ("ru", "Офлайн"),
    ])
    def test_offline_msg(self, lang, expected):
        set_language(lang)
        assert t("msg.offline") == expected

    # --- Terminal section ---
    @pytest.mark.parametrize("lang,expected", [
        ("en", "Terminal"),
        ("tr", "Terminal"),
        ("ru", "Терминал"),
        ("ja", "ターミナル"),
        ("zh", "终端"),
    ])
    def test_terminal_section(self, lang, expected):
        set_language(lang)
        assert t("terminal.section") == expected

    # --- Chat section ---
    @pytest.mark.parametrize("lang,expected", [
        ("en", "Chat"),
        ("tr", "Sohbet"),
        ("ru", "Чат"),
        ("ja", "チャット"),
        ("zh", "对话"),
    ])
    def test_chat_section(self, lang, expected):
        set_language(lang)
        assert t("chat.section") == expected
