"""
Shared test fixtures for Sentinel AI test suite.

Provides:
- QApplication singleton (session-scoped, autouse)
- i18n language reset (autouse per-test)
"""

import sys
import os
import pytest

# ---------------------------------------------------------------------------
# QApplication — must be created once per process for PyQt6 widget tests.
# session + autouse ensures it's created before ANY test runs, so that
# QProcess / QTimer objects in non-UI tests also have a valid event loop.
# ---------------------------------------------------------------------------
_qapp = None


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Session-scoped QApplication instance — created before all tests."""
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


def pytest_addoption(parser):
    """Add explicit opt-in switch for live LLM tests."""
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="run tests marked with @pytest.mark.llm",
    )


def pytest_collection_modifyitems(config, items):
    """Skip LLM tests by default to keep CI deterministic and fast."""
    run_llm = config.getoption("--run-llm") or os.getenv("RUN_LLM_TESTS") == "1"
    if run_llm:
        return

    skip_llm = pytest.mark.skip(reason="LLM tests are skipped by default. Use --run-llm or RUN_LLM_TESTS=1.")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)
