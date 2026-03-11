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
            params={"scan_type": "sS"},  # LLM-generated param
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2("10.10.10.10 portlarini T4 hizinda tara")

    assert result["success"] is True
    # strict-regex: scan_type dropped (user didn't say SYN/-sS), timing kept (T4 in input)
    assert result["intent"].params["timing"] == 4
    assert "scan_type" not in result["intent"].params


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


# ── Sprint 3.7.1 — Benchmark Accuracy Hardening Tests ──


def test_strict_regex_drops_llm_hallucinated_params() -> None:
    """All action intents should only keep regex-extracted params."""
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.HOST_DISCOVERY,
            target="192.168.1.0/24",
            params={"timing": 5, "scan_type": "sS", "no_ping": True},  # hallucinated
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2("192.168.1.0/24 agini tara")
    assert result["success"] is True
    assert result["intent"].params == {}  # no regex match in input


def test_nl_port_extraction_ve_pattern() -> None:
    """Natural language: '80 ve 443 portlarini'."""
    params = ParamExtractor.extract("80 ve 443 portlarini kontrol et 10.0.0.1 de", IntentType.PORT_SCAN)
    assert params["ports"] == "80,443"


def test_nl_port_extraction_range() -> None:
    """Natural language: 'port 1-1024 arasini'."""
    params = ParamExtractor.extract("hedef sunucunun port 1-1024 arasini tara", IntentType.PORT_SCAN)
    assert params["ports"] == "1-1024"


def test_nl_port_extraction_single() -> None:
    """Single port: '22 portunun'."""
    params = ParamExtractor.extract("172.18.0.12 uzerinde 22 portunun servis surumune bak", IntentType.SERVICE_DETECTION)
    assert params["ports"] == "22"


def test_nl_port_extraction_multiple_comma() -> None:
    """Comma-separated: '21,22,80 portlarini'."""
    params = ParamExtractor.extract("172.16.1.25 uzerinde 21,22,80 portlarini kontrol et", IntentType.PORT_SCAN)
    assert params["ports"] == "21,22,80"


def test_dns_record_type_with_kaydi_suffix() -> None:
    """DNS record with Turkish kaydı suffix: 'A kaydini'."""
    params = ParamExtractor.extract("example.net icin A kaydini sorgula", IntentType.DNS_LOOKUP)
    assert params["record_type"] == "A"


def test_dns_record_type_aaaa() -> None:
    """AAAA record extraction."""
    params = ParamExtractor.extract("cdn.example.io AAAA kaydini sorgula", IntentType.DNS_LOOKUP)
    assert params["record_type"] == "AAAA"


def test_keyword_info_query_ne_demek() -> None:
    """'ne demek' pattern should trigger info_query."""
    kf = KeywordPreFilter()
    assert kf.suggest("nmap service detection ne demek") == IntentType.INFO_QUERY


def test_keyword_info_query_neden_yapilir() -> None:
    """'neden yapilir' pattern should trigger info_query."""
    kf = KeywordPreFilter()
    assert kf.suggest("ssl scan neden yapilir") == IntentType.INFO_QUERY


def test_keyword_info_query_why_do_analysts() -> None:
    """'Why do analysts' pattern should trigger info_query."""
    kf = KeywordPreFilter()
    assert kf.suggest("Why do analysts run WHOIS queries?") == IntentType.INFO_QUERY


def test_keyword_web_dir_enum_gizli_path() -> None:
    """'gizli path ara' should trigger web_dir_enum."""
    kf = KeywordPreFilter()
    assert kf.suggest("gobuster ile gizli path ara") == IntentType.WEB_DIR_ENUM


def test_keyword_web_dir_enum_discover_hidden() -> None:
    """'Discover hidden paths' should trigger web_dir_enum."""
    kf = KeywordPreFilter()
    assert kf.suggest("Discover hidden paths on https://demo.example.org") == IntentType.WEB_DIR_ENUM


def test_keyword_unknown_vague_task() -> None:
    """Vague/uncertain inputs should trigger unknown."""
    kf = KeywordPreFilter()
    assert kf.suggest("I need help with a task but I am not sure what exactly") == IntentType.UNKNOWN


def test_target_prefers_regex_url_over_llm() -> None:
    """Regex URL (with path) should be preferred over LLM target."""
    orchestrator = AIOrchestrator(model="qwen2.5:3b")
    orchestrator._intent_resolver = _DummyResolver(
        Intent(
            intent_type=IntentType.SQL_INJECTION,
            target="http://target.com",  # LLM truncated
            params={},
            needs_clarification=False,
            clarification_reason=None,
            confidence=0.95,
        )
    )
    orchestrator._hierarchical_resolver = None

    result = orchestrator.process_v2(
        "http://target.com/login?id=2 SQL injection testi yap"
    )
    assert result["success"] is True
    # Regex should preserve full URL with path+query
    assert "http://target.com/login?id=2" in str(result["command"].arguments)
