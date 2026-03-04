"""
Shared test fixtures for Sentinel AI test suite.

Provides:
- QApplication singleton (session-scoped)
- i18n language reset (autouse per-test)
"""

import sys
import pytest

# ---------------------------------------------------------------------------
# QApplication — must be created once per process for PyQt6 widget tests.
# ---------------------------------------------------------------------------
_qapp = None


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication instance for widget tests."""
    global _qapp
    if _qapp is None:
        from PyQt6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)
    return _qapp


@pytest.fixture(autouse=True)
def _reset_i18n():
    """Reset i18n language to English before every test."""
    from src.ui.i18n import set_language
    set_language("en")
    yield
    set_language("en")
