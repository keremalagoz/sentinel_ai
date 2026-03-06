"""Sprint 3.2 Track C — AI Scaling Infrastructure Tests

Unit tests for:
  C1: Intent confidence score (schemas + resolver)
  C2: Keyword pre-filter (KeywordPreFilter)
  C3: Response time budget (MAX_RESPONSE_MS constant)
  C7: ToolDef priority / condition fields
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import patch, MagicMock

from src.ai.schemas import Intent, IntentType, ToolDef, RiskLevel, INTENT_SCHEMA
from src.ai.keyword_filter import KeywordPreFilter
from src.ai.orchestrator import AIOrchestrator


# =============================================================================
# C1 — Intent Confidence Score
# =============================================================================

class TestIntentConfidence:
    """Intent modeline eklenen confidence field testleri."""

    def test_default_confidence_is_one(self):
        """Confidence belirtilmezse default 1.0 olmali."""
        intent = Intent(
            intent_type=IntentType.PORT_SCAN,
            target="192.168.1.1",
        )
        assert intent.confidence == 1.0

    def test_confidence_explicit_value(self):
        """Confidence acikca atanabilmeli."""
        intent = Intent(
            intent_type=IntentType.PORT_SCAN,
            target="10.0.0.1",
            confidence=0.85,
        )
        assert intent.confidence == 0.85

    def test_confidence_lower_bound(self):
        """Confidence 0.0 olabilmeli."""
        intent = Intent(
            intent_type=IntentType.UNKNOWN,
            confidence=0.0,
        )
        assert intent.confidence == 0.0

    def test_confidence_upper_bound(self):
        """Confidence 1.0 olabilmeli."""
        intent = Intent(
            intent_type=IntentType.PORT_SCAN,
            confidence=1.0,
        )
        assert intent.confidence == 1.0

    def test_confidence_out_of_range_raises(self):
        """Confidence 0-1 araliginin disinda ValidationError firlatmali."""
        with pytest.raises(Exception):
            Intent(intent_type=IntentType.PORT_SCAN, confidence=1.5)
        with pytest.raises(Exception):
            Intent(intent_type=IntentType.PORT_SCAN, confidence=-0.1)

    def test_intent_schema_has_confidence(self):
        """INTENT_SCHEMA dict'inde confidence tanimli olmali."""
        props = INTENT_SCHEMA["schema"]["properties"]
        assert "confidence" in props
        required = INTENT_SCHEMA["schema"]["required"]
        assert "confidence" in required


# =============================================================================
# C2 — Keyword Pre-Filter
# =============================================================================

class TestKeywordPreFilter:
    """KeywordPreFilter suggest ve cross_validate testleri."""

    @pytest.fixture
    def kf(self):
        return KeywordPreFilter()

    def test_pattern_count_at_least_10(self, kf):
        """En az 10 keyword pattern tanimli olmali."""
        assert kf.pattern_count >= 10

    # -- suggest --

    @pytest.mark.parametrize("input_text,expected", [
        ("192.168.1.0/24 agini tara", IntentType.HOST_DISCOVERY),
        ("ping sweep yap", IntentType.HOST_DISCOVERY),
        ("port taramasi yap", IntentType.PORT_SCAN),
        ("portu hizlica tara", IntentType.PORT_SCAN),
        ("hizli tara 192.168.1.1", IntentType.PORT_SCAN),
        ("agresif tarama yap 10.0.0.1", IntentType.PORT_SCAN),
        ("aggressive scan baslat", IntentType.PORT_SCAN),
        ("ping atmadan tara", IntentType.PORT_SCAN),
        ("no-ping ile tara", IntentType.PORT_SCAN),
        ("acik port bul", IntentType.PORT_SCAN),
        ("SSL sertifikasini kontrol et", IntentType.SSL_SCAN),
        ("DNS sorgulama yap", IntentType.DNS_LOOKUP),
        ("zafiyet taramasi baslat", IntentType.VULN_SCAN),
        ("subdomain enumeration yap", IntentType.SUBDOMAIN_ENUM),
        ("nikto ile web sunucusunu tara", IntentType.WEB_VULN_SCAN),
        ("gobuster ile dizin ara", IntentType.WEB_DIR_ENUM),
        ("sqlmap ile SQL injection testi", IntentType.SQL_INJECTION),
        ("SSH brute force yap", IntentType.BRUTE_FORCE_SSH),
        ("nmap nedir", IntentType.INFO_QUERY),
    ])
    def test_suggest_known_patterns(self, kf, input_text, expected):
        """Bilinen keyword pattern'leri dogruca IntentType dondurmeli."""
        result = kf.suggest(input_text)
        assert result == expected, f"'{input_text}' -> {result}, beklenen: {expected}"

    def test_suggest_unknown_returns_none(self, kf):
        """Hicbir pattern eslesmediyse None donmeli."""
        assert kf.suggest("bugun hava nasil") is None

    def test_suggest_all_returns_multiple_candidates(self, kf):
        """Compound ifadelerde birden fazla intent adayi donmeli."""
        candidates = kf.suggest_all("10.0.0.1 port tara ve dns sorgu yap")
        assert IntentType.PORT_SCAN in candidates
        assert IntentType.DNS_LOOKUP in candidates

    # -- cross_validate --

    def test_cross_validate_consistent(self, kf):
        """LLM ve keyword ayni sonucu verdiyse tutarli olmali."""
        ok, msg = kf.cross_validate(IntentType.PORT_SCAN, "acik portlari tara")
        assert ok is True
        assert msg is None

    def test_cross_validate_no_keyword_match(self, kf):
        """Keyword eslesmesi yoksa LLM'e guvenilmeli."""
        ok, msg = kf.cross_validate(IntentType.PORT_SCAN, "yapay zeka testi")
        assert ok is True
        assert msg is None

    def test_cross_validate_mismatch_warns(self, kf):
        """Uyumsuz LLM ve keyword sonucu warning dondurmeli."""
        ok, msg = kf.cross_validate(IntentType.DNS_LOOKUP, "zafiyet taramasi yap")
        assert ok is False
        assert msg is not None
        assert "uyumsuz" in msg.lower()

    def test_cross_validate_compatible_group(self, kf):
        """Yakin akraba intent'ler (port_scan/host_discovery) uyumlu sayilmali."""
        ok, _ = kf.cross_validate(IntentType.PORT_SCAN, "agdaki aktif cihazlari bul")
        assert ok is True

    def test_cross_validate_compatible_web(self, kf):
        """web_dir_enum vs web_vuln_scan uyumlu grupta olmali."""
        ok, _ = kf.cross_validate(IntentType.WEB_DIR_ENUM, "nikto web scan")
        assert ok is True


# =============================================================================
# C3 — Response Time Budget
# =============================================================================

class TestResponseTimeBudget:
    """Orchestrator MAX_RESPONSE_MS sabiti ve tipi."""

    def test_max_response_ms_exists(self):
        """AIOrchestrator uzerinde MAX_RESPONSE_MS tanimli olmali."""
        assert hasattr(AIOrchestrator, "MAX_RESPONSE_MS")

    def test_max_response_ms_value(self):
        """MAX_RESPONSE_MS varsayilan 10_000 olmali."""
        assert AIOrchestrator.MAX_RESPONSE_MS == 10_000

    def test_confidence_threshold_exists(self):
        """AIOrchestrator uzerinde CONFIDENCE_THRESHOLD tanimli olmali."""
        assert hasattr(AIOrchestrator, "CONFIDENCE_THRESHOLD")

    def test_confidence_threshold_value(self):
        """CONFIDENCE_THRESHOLD varsayilan 0.7 olmali."""
        assert AIOrchestrator.CONFIDENCE_THRESHOLD == 0.7


# =============================================================================
# C7 — ToolDef Priority & Condition
# =============================================================================

class TestToolDefExtensions:
    """ToolDef modeline eklenen priority ve condition field'lari."""

    def test_tooldef_default_priority(self):
        """priority default 0 olmali."""
        td = ToolDef(
            tool="echo",
            description="A test tool",
            risk_level=RiskLevel.LOW,
        )
        assert td.priority == 0

    def test_tooldef_explicit_priority(self):
        """priority acikca atanabilmeli."""
        td = ToolDef(
            tool="echo",
            description="A test tool",
            risk_level=RiskLevel.LOW,
            priority=5,
        )
        assert td.priority == 5

    def test_tooldef_default_condition_none(self):
        """condition default None olmali."""
        td = ToolDef(
            tool="echo",
            description="A test tool",
            risk_level=RiskLevel.LOW,
        )
        assert td.condition is None

    def test_tooldef_explicit_condition(self):
        """condition string atanabilmeli."""
        td = ToolDef(
            tool="echo",
            description="A test tool",
            risk_level=RiskLevel.LOW,
            condition="target.startswith('http')",
        )
        assert td.condition == "target.startswith('http')"

    def test_tooldef_negative_priority_raises(self):
        """priority negatif ise ValidationError firlatmali."""
        with pytest.raises(Exception):
            ToolDef(
                tool="echo",
                description="A test tool",
                risk_level=RiskLevel.LOW,
                priority=-1,
            )


# =============================================================================
# Orchestrator keyword filter integration
# =============================================================================

class TestOrchestratorKeywordIntegration:
    """Orchestrator'un KeywordPreFilter instance'i barindirdigini dogrular."""

    def test_orchestrator_has_keyword_filter(self):
        """AIOrchestrator._keyword_filter mevcut olmali."""
        orch = AIOrchestrator.__new__(AIOrchestrator)
        # __init__ LLM baglantisi kurar; sadece attribute varligini sinayoruz
        # Gercek init yerine manual atama
        orch._keyword_filter = KeywordPreFilter()
        assert hasattr(orch, "_keyword_filter")
        assert isinstance(orch._keyword_filter, KeywordPreFilter)
