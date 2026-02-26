"""Track D Tests — Code Quality & Technical Debt

Sprint 3.6 Track D:
  D1: tool_base.py split (backward-compat shim)
  D2: SQLite WAL mode
  D3: Legacy schema cleanup (schemas_legacy.py)
  D4: Singleton thread safety
"""

import sqlite3
import tempfile
import threading
from pathlib import Path

import pytest


# =========================================================================
# D1: tool_base.py backward-compat shim
# =========================================================================

class TestToolBaseSplit:
    """D1: tool_base.py -> src/core/tools/ package split verification."""

    def test_import_from_tool_base_still_works(self):
        """Eski import yolu hala calisir."""
        from src.core.tool_base import (
            BaseTool,
            ToolStatus,
            ToolResult,
            ToolExecutionSignals,
            PingTool,
            NmapPingSweepTool,
            NmapPortScanTool,
            NmapServiceDetectionTool,
            NmapVulnScanTool,
            SslScanTool,
            GobusterDirTool,
            SubdomainEnumTool,
            DnsLookupTool,
            WebAppScanTool,
        )
        assert BaseTool is not None
        assert ToolStatus.IDLE == "idle"

    def test_import_from_tools_package(self):
        """Yeni import yolu da calisir."""
        from src.core.tools import (
            BaseTool,
            ToolStatus,
            ToolResult,
            ToolExecutionSignals,
            PingTool,
        )
        assert BaseTool is not None
        assert ToolStatus.SUCCESS == "success"

    def test_both_paths_same_objects(self):
        """Iki yoldan gelen nesneler ayni."""
        from src.core.tool_base import PingTool as PT1
        from src.core.tools import PingTool as PT2
        assert PT1 is PT2

    def test_tools_package_has_all(self):
        """__all__ listesi eksiksiz."""
        import src.core.tools as tools_pkg
        expected = {
            "BaseTool", "ToolStatus", "ToolResult", "ToolExecutionSignals",
            "PingTool", "NmapPingSweepTool", "NmapPortScanTool",
            "NmapServiceDetectionTool", "NmapVulnScanTool", "SslScanTool",
            "GobusterDirTool", "SubdomainEnumTool", "DnsLookupTool",
            "WebAppScanTool",
        }
        assert set(tools_pkg.__all__) == expected

    def test_ping_tool_build_command(self):
        """PingTool split sonrasi islevsel."""
        from src.core.tools import PingTool
        tool = PingTool()
        cmd = tool.build_command(target="127.0.0.1", count=2)
        assert "ping" in cmd
        assert "127.0.0.1" in cmd

    def test_tool_base_shim_file_is_small(self):
        """Shim dosyasi 50 satirdan kucuk olmali."""
        shim = Path(__file__).resolve().parent.parent / "core" / "tool_base.py"
        lines = shim.read_text(encoding="utf-8").splitlines()
        assert len(lines) < 50, f"Shim {len(lines)} satir — 50'den kucuk olmali"


# =========================================================================
# D2: SQLite WAL Mode
# =========================================================================

class TestSQLiteWAL:
    """D2: WAL mode aktif oldugunu dogrula."""

    def test_wal_mode_enabled(self, tmp_path):
        """SQLiteBackend WAL modunda aciliyor."""
        from src.core.sqlite_backend import SQLiteBackend
        db_path = tmp_path / "test_wal.db"
        backend = SQLiteBackend(str(db_path))

        mode = backend.connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal", f"Beklenen WAL, alinan: {mode}"

    def test_synchronous_normal(self, tmp_path):
        """synchronous=NORMAL ayarlanmis mi."""
        from src.core.sqlite_backend import SQLiteBackend
        db_path = tmp_path / "test_sync.db"
        backend = SQLiteBackend(str(db_path))

        sync = backend.connection.execute("PRAGMA synchronous").fetchone()[0]
        # NORMAL = 1
        assert sync == 1, f"Beklenen NORMAL (1), alinan: {sync}"


# =========================================================================
# D3: Legacy Schema Cleanup
# =========================================================================

class TestLegacySchemaCleanup:
    """D3: Legacy sema ayri dosyada, geriye uyumlu importlar calisir."""

    def test_legacy_file_exists(self):
        """schemas_legacy.py dosyasi mevcut."""
        legacy = Path(__file__).resolve().parent.parent / "ai" / "schemas_legacy.py"
        assert legacy.exists(), "schemas_legacy.py bulunamadi"

    def test_import_from_schemas_still_works(self):
        """Eski import yolu hala calisir."""
        from src.ai.schemas import (
            ToolCommand,
            AIResponse,
            TOOL_COMMAND_SCHEMA,
            AI_RESPONSE_SCHEMA,
            validate_command,
            get_response_format,
            ALLOWED_TOOLS,
        )
        assert ToolCommand is not None
        assert "nmap" in ALLOWED_TOOLS

    def test_import_from_schemas_legacy(self):
        """Dogrudan legacy dosyasindan import."""
        from src.ai.schemas_legacy import (
            ToolCommand,
            AIResponse,
            validate_command,
        )
        assert ToolCommand is not None
        assert AIResponse is not None

    def test_both_paths_same_objects(self):
        """Iki yoldan gelen siniflar ayni."""
        from src.ai.schemas import ToolCommand as TC1
        from src.ai.schemas_legacy import ToolCommand as TC2
        assert TC1 is TC2

    def test_schemas_py_line_count_reduced(self):
        """schemas.py artik ~380 satir civarinda olmali (hedef)."""
        schemas = Path(__file__).resolve().parent.parent / "ai" / "schemas.py"
        lines = schemas.read_text(encoding="utf-8").splitlines()
        # Hedef: 577 -> ~380 (en az 150 satir azalma)
        assert len(lines) < 420, f"schemas.py {len(lines)} satir — 420'den az olmali"

    def test_validate_command_works(self):
        """validate_command legacy fonksiyonu calisiyor."""
        from src.ai.schemas import validate_command
        cmd = validate_command({
            "tool": "nmap",
            "arguments": ["-sn", "192.168.1.0/24"],
            "requires_root": False,
            "risk_level": "low",
        })
        assert cmd.tool == "nmap"


# =========================================================================
# D4: Singleton Thread Safety
# =========================================================================

class TestSingletonThreadSafety:
    """D4: Singleton getter'lar threading.Lock kullaniyor."""

    def test_intent_resolver_has_lock(self):
        """IntentResolver singleton lock var."""
        import src.ai.intent_resolver as mod
        assert hasattr(mod, "_resolver_lock")
        assert isinstance(mod._resolver_lock, type(threading.Lock()))

    def test_orchestrator_has_lock(self):
        """Orchestrator singleton lock var."""
        import src.ai.orchestrator as mod
        assert hasattr(mod, "_orchestrator_lock")
        assert isinstance(mod._orchestrator_lock, type(threading.Lock()))

    def test_command_builder_has_lock(self):
        """CommandBuilder singleton lock var."""
        import src.ai.command_builder as mod
        assert hasattr(mod, "_builder_lock")
        assert isinstance(mod._builder_lock, type(threading.Lock()))

    def test_command_builder_singleton_returns_same_instance(self):
        """get_command_builder() her seferinde ayni instance doner."""
        from src.ai.command_builder import get_command_builder
        b1 = get_command_builder()
        b2 = get_command_builder()
        assert b1 is b2
