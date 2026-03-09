from src.ai.orchestrator import AIOrchestrator
from src.ai.param_extractor import ParamExtractor
from src.ai.schemas import Intent, IntentType
from src.ai.keyword_filter import KeywordPreFilter


class _DummyResolver:
    def __init__(self, intent: Intent):
        self.intent = intent

    def resolve(self, user_input: str, target_hint=None) -> Intent:
        return self.intent


def test_param_extractor_extracts_vuln_scripts() -> None:
    params = ParamExtractor.extract(
        "192.168.1.1 zafiyet taramasi yap vuln scriptleri ile",
        IntentType.VULN_SCAN,
    )
    assert params["scripts"] == "vuln"


def test_param_extractor_extracts_ssl_port() -> None:
    params = ParamExtractor.extract(
        "example.com SSL sertifikasini kontrol et port 8443",
        IntentType.SSL_SCAN,
    )
    assert params["port"] == 8443


def test_param_extractor_extracts_sqlmap_level_risk() -> None:
    params = ParamExtractor.extract(
        "http://target.com/login SQL injection testi level 3 risk 2",
        IntentType.SQL_INJECTION,
    )
    assert params["level"] == 3
    assert params["risk"] == 2


def test_param_extractor_target_prefers_url() -> None:
    target = ParamExtractor.extract_target("10.0.0.1 ve https://example.com/login test et")
    assert target == "https://example.com/login"


def test_orchestrator_merges_llm_and_regex_params() -> None:
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.PORT_SCAN,
            target="10.10.10.10",
            params={"scan_type": "sS"},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2("10.10.10.10 portlarini T4 hizinda tara")

    assert result["success"] is True
    assert result["intent"].params["scan_type"] == "sS"
    assert result["intent"].params["timing"] == 4


def test_orchestrator_target_fallback_prefers_regex_over_ui_hint() -> None:
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.DNS_LOOKUP,
            target=None,
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2(
        "example.com MX kayitlarini sorgula",
        target="fallback.local",
    )

    assert result["success"] is True
    assert "example.com" in result["command"].arguments


def test_orchestrator_applies_dns_record_override_rule() -> None:
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.WHOIS_LOOKUP,
            target="example.com",
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.81,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2("example.com MX kayitlarini sorgula")

    assert result["success"] is True
    assert result["intent"].intent_type == IntentType.DNS_LOOKUP
    assert result["intent"].params["record_type"] == "MX"


def test_keyword_filter_expanded_info_query_patterns() -> None:
    kf = KeywordPreFilter()
    assert kf.suggest("Nmap ile service detection arasindaki fark nedir?") == IntentType.INFO_QUERY
