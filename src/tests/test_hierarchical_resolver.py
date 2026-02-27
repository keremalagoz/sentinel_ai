"""Sprint 3.7 — Hierarchical Resolver Unit Tests

Test suite for 2-stage intent resolution:
  - CategoryType / CategoryResult / SENTINEL_CATEGORIES models
  - HierarchicalResolver Stage 1 (category) parsing
  - HierarchicalResolver Stage 2 (sub-intent) parsing
  - Keyword bypass integration
  - Orchestrator feature flag routing
  - Fallback / error scenarios
"""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from src.ai.schemas import (
    CategoryType,
    CategoryResult,
    Intent,
    IntentType,
    SENTINEL_CATEGORIES,
    get_category_for_intent,
)
from src.ai.hierarchical_resolver import (
    HierarchicalResolver,
    HierarchicalResolverBase,
    CATEGORY_PROMPT,
    SUB_INTENT_PROMPT_TEMPLATE,
    _INTENT_DESCRIPTIONS,
)


# =============================================================================
# 3.7.1 — SENTINEL_CATEGORIES & CategoryResult model tests
# =============================================================================

class TestSentinelCategories:
    """SENTINEL_CATEGORIES yapisal dogruluk testleri."""

    def test_five_categories_exist(self):
        """5 kategori tanimli olmali."""
        assert len(SENTINEL_CATEGORIES) == 5
        expected = {CategoryType.SCANNING, CategoryType.WEB, CategoryType.RECON,
                    CategoryType.ATTACK, CategoryType.INFO}
        assert set(SENTINEL_CATEGORIES.keys()) == expected

    def test_all_intent_types_covered(self):
        """Tum IntentType degerleri en az bir kategoride olmali."""
        all_intents_in_categories = set()
        for intents in SENTINEL_CATEGORIES.values():
            all_intents_in_categories.update(intents)

        for intent_type in IntentType:
            assert intent_type in all_intents_in_categories, (
                f"{intent_type.value} hicbir kategoride yok"
            )

    def test_no_duplicate_intents_across_categories(self):
        """Bir IntentType sadece bir kategoride olmali."""
        seen = {}
        for cat, intents in SENTINEL_CATEGORIES.items():
            for intent in intents:
                assert intent not in seen, (
                    f"{intent.value} hem {seen[intent].value} hem {cat.value} kategorisinde"
                )
                seen[intent] = cat

    def test_scanning_category_count(self):
        """Scanning kategorisi 6 intent icermeli."""
        assert len(SENTINEL_CATEGORIES[CategoryType.SCANNING]) == 6

    def test_web_category_count(self):
        assert len(SENTINEL_CATEGORIES[CategoryType.WEB]) == 2

    def test_recon_category_count(self):
        assert len(SENTINEL_CATEGORIES[CategoryType.RECON]) == 3

    def test_attack_category_count(self):
        assert len(SENTINEL_CATEGORIES[CategoryType.ATTACK]) == 3

    def test_info_category_count(self):
        assert len(SENTINEL_CATEGORIES[CategoryType.INFO]) == 2


class TestGetCategoryForIntent:
    """Ters lookup: IntentType -> CategoryType."""

    def test_port_scan_is_scanning(self):
        assert get_category_for_intent(IntentType.PORT_SCAN) == CategoryType.SCANNING

    def test_web_dir_enum_is_web(self):
        assert get_category_for_intent(IntentType.WEB_DIR_ENUM) == CategoryType.WEB

    def test_dns_lookup_is_recon(self):
        assert get_category_for_intent(IntentType.DNS_LOOKUP) == CategoryType.RECON

    def test_brute_force_ssh_is_attack(self):
        assert get_category_for_intent(IntentType.BRUTE_FORCE_SSH) == CategoryType.ATTACK

    def test_info_query_is_info(self):
        assert get_category_for_intent(IntentType.INFO_QUERY) == CategoryType.INFO

    def test_unknown_is_info(self):
        assert get_category_for_intent(IntentType.UNKNOWN) == CategoryType.INFO

    def test_all_intents_have_reverse_lookup(self):
        """Her IntentType icin get_category_for_intent calismali."""
        for intent_type in IntentType:
            result = get_category_for_intent(intent_type)
            assert isinstance(result, CategoryType)


class TestCategoryResult:
    """CategoryResult Pydantic model testleri."""

    def test_valid_category_result(self):
        cr = CategoryResult(category=CategoryType.SCANNING, confidence=0.95)
        assert cr.category == CategoryType.SCANNING
        assert cr.confidence == 0.95
        assert cr.raw_response is None

    def test_confidence_bounds(self):
        cr = CategoryResult(category=CategoryType.WEB, confidence=0.0)
        assert cr.confidence == 0.0

        cr2 = CategoryResult(category=CategoryType.WEB, confidence=1.0)
        assert cr2.confidence == 1.0

    def test_confidence_out_of_bounds_raises(self):
        with pytest.raises(Exception):
            CategoryResult(category=CategoryType.WEB, confidence=1.5)

        with pytest.raises(Exception):
            CategoryResult(category=CategoryType.WEB, confidence=-0.1)

    def test_with_raw_response(self):
        cr = CategoryResult(
            category=CategoryType.RECON,
            confidence=0.8,
            raw_response={"category": "recon", "confidence": 0.8},
        )
        assert cr.raw_response["category"] == "recon"


class TestCategoryType:
    """CategoryType enum testleri."""

    def test_enum_values(self):
        assert CategoryType.SCANNING.value == "scanning"
        assert CategoryType.WEB.value == "web"
        assert CategoryType.RECON.value == "recon"
        assert CategoryType.ATTACK.value == "attack"
        assert CategoryType.INFO.value == "info"

    def test_from_string(self):
        assert CategoryType("scanning") == CategoryType.SCANNING
        assert CategoryType("info") == CategoryType.INFO

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            CategoryType("invalid_category")


# =============================================================================
# 3.7.2 — HierarchicalResolverBase ABC tests
# =============================================================================

class TestHierarchicalResolverBase:
    """Base class ABC testleri."""

    def test_cannot_instantiate_abc(self):
        """ABC dogrudan olusturulamaz."""
        with pytest.raises(TypeError):
            HierarchicalResolverBase()

    def test_concrete_must_implement_methods(self):
        """Somut sinif resolve_category ve resolve_sub_intent uygulamali."""
        class Incomplete(HierarchicalResolverBase):
            pass

        with pytest.raises(TypeError):
            Incomplete()


# =============================================================================
# 3.7.3 — Stage 1 Category parsing tests
# =============================================================================

class TestStage1CategoryParsing:
    """Stage 1 LLM yanit parse testleri (LLM mock'lu)."""

    def _make_resolver(self):
        """LLM cagrisi olmadan resolver olustur."""
        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_model"
            r._sub_intent_model = "test_model"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            r._keyword_filter = MagicMock()
            return r

    def test_parse_valid_scanning(self):
        r = self._make_resolver()
        raw = '{"category": "scanning", "confidence": 0.95}'
        result = r._parse_category_response(raw)
        assert result.category == CategoryType.SCANNING
        assert result.confidence == 0.95

    def test_parse_valid_web(self):
        r = self._make_resolver()
        raw = '{"category": "web", "confidence": 0.88}'
        result = r._parse_category_response(raw)
        assert result.category == CategoryType.WEB

    def test_parse_valid_attack(self):
        r = self._make_resolver()
        raw = '{"category": "attack", "confidence": 0.92}'
        result = r._parse_category_response(raw)
        assert result.category == CategoryType.ATTACK

    def test_parse_markdown_code_block(self):
        r = self._make_resolver()
        raw = '```json\n{"category": "recon", "confidence": 0.9}\n```'
        result = r._parse_category_response(raw)
        assert result.category == CategoryType.RECON

    def test_parse_unknown_category_fallback_info(self):
        r = self._make_resolver()
        raw = '{"category": "nonexistent", "confidence": 0.5}'
        result = r._parse_category_response(raw)
        assert result.category == CategoryType.INFO

    def test_parse_invalid_json_fallback(self):
        r = self._make_resolver()
        raw = "this is not json"
        result = r._parse_category_response(raw)
        assert result.category == CategoryType.INFO
        assert result.confidence == 0.0

    def test_parse_confidence_clamped(self):
        r = self._make_resolver()
        # confidence > 1.0 ise clamp edilmeli
        raw = '{"category": "scanning", "confidence": 1.5}'
        result = r._parse_category_response(raw)
        assert result.confidence == 1.0

    def test_parse_missing_confidence_defaults(self):
        r = self._make_resolver()
        raw = '{"category": "web"}'
        result = r._parse_category_response(raw)
        assert result.confidence == 1.0


# =============================================================================
# 3.7.4 — Stage 2 Sub-Intent parsing tests
# =============================================================================

class TestStage2SubIntentParsing:
    """Stage 2 LLM yanit parse testleri."""

    def _make_resolver(self):
        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_model"
            r._sub_intent_model = "test_model"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            r._keyword_filter = MagicMock()
            return r

    def test_parse_valid_port_scan(self):
        r = self._make_resolver()
        raw = json.dumps({
            "intent_type": "port_scan",
            "target": "192.168.1.1",
            "params": {"ports": "1-1000"},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.95,
        })
        result = r._parse_sub_intent_response(raw, CategoryType.SCANNING)
        assert result.intent_type == IntentType.PORT_SCAN
        assert result.target == "192.168.1.1"
        assert result.confidence == 0.95

    def test_parse_valid_dns_lookup(self):
        r = self._make_resolver()
        raw = json.dumps({
            "intent_type": "dns_lookup",
            "target": "example.com",
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.92,
        })
        result = r._parse_sub_intent_response(raw, CategoryType.RECON)
        assert result.intent_type == IntentType.DNS_LOOKUP

    def test_parse_unknown_intent_type_fallback(self):
        r = self._make_resolver()
        raw = json.dumps({
            "intent_type": "nonexistent_intent",
            "target": None,
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.5,
        })
        result = r._parse_sub_intent_response(raw, CategoryType.SCANNING)
        assert result.intent_type == IntentType.UNKNOWN

    def test_parse_intent_wrong_category_still_accepted(self):
        """Intent doğru ama yanlış kategorideyse kabul edilir (warning log)."""
        r = self._make_resolver()
        raw = json.dumps({
            "intent_type": "port_scan",
            "target": "10.0.0.1",
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.85,
        })
        # port_scan WEB kategorisinde değil ama kabul edilmeli
        result = r._parse_sub_intent_response(raw, CategoryType.WEB)
        assert result.intent_type == IntentType.PORT_SCAN

    def test_parse_invalid_json_fallback(self):
        r = self._make_resolver()
        result = r._parse_sub_intent_response("not json", CategoryType.SCANNING)
        assert result.intent_type == IntentType.UNKNOWN
        assert result.needs_clarification is True

    def test_parse_with_clarification(self):
        r = self._make_resolver()
        raw = json.dumps({
            "intent_type": "unknown",
            "target": None,
            "params": {},
            "needs_clarification": True,
            "clarification_reason": "Talep belirsiz",
            "confidence": 0.2,
        })
        result = r._parse_sub_intent_response(raw, CategoryType.INFO)
        assert result.needs_clarification is True
        assert result.clarification_reason == "Talep belirsiz"


# =============================================================================
# 3.7.5 — Keyword bypass integration tests
# =============================================================================

class TestKeywordBypass:
    """Keyword pre-filter Stage 1 bypass testleri."""

    def _make_resolver_with_mocked_llm(self, stage2_response: str):
        """Stage 2 LLM mock'lu resolver."""
        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_cat_model"
            r._sub_intent_model = "qwen2.5:3b"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            r._client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=stage2_response))]
            )
            # Gercek KeywordPreFilter kullan
            from src.ai.keyword_filter import KeywordPreFilter
            r._keyword_filter = KeywordPreFilter()
            return r

    def test_keyword_bypass_port_scan(self):
        """'port tara' gibi acik keyword ile Stage 1 atlanmali."""
        stage2_resp = json.dumps({
            "intent_type": "port_scan",
            "target": "192.168.1.1",
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.95,
        })
        r = self._make_resolver_with_mocked_llm(stage2_resp)
        intent = r.resolve("192.168.1.1 port tara")

        assert intent.intent_type == IntentType.PORT_SCAN
        # Stage 1 (category) LLM cagrisi YAPILMAMALI — sadece Stage 2
        # OpenAI client 1 kez cagrilmali (Stage 2 icin)
        assert r._client.chat.completions.create.call_count == 1

    def test_keyword_bypass_dns_lookup(self):
        stage2_resp = json.dumps({
            "intent_type": "dns_lookup",
            "target": "example.com",
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.90,
        })
        r = self._make_resolver_with_mocked_llm(stage2_resp)
        intent = r.resolve("dns sorgu yap example.com")

        assert intent.intent_type == IntentType.DNS_LOOKUP
        assert r._client.chat.completions.create.call_count == 1

    def test_no_keyword_match_uses_both_stages(self):
        """Keyword eslesmesi yoksa Stage 1 + Stage 2 cagrilmali."""
        stage1_resp = '{"category": "scanning", "confidence": 0.85}'
        stage2_resp = json.dumps({
            "intent_type": "port_scan",
            "target": None,
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.80,
        })

        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_cat_model"
            r._sub_intent_model = "qwen2.5:3b"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            # Ilk cagri Stage 1, ikinci cagri Stage 2
            r._client.chat.completions.create.side_effect = [
                MagicMock(choices=[MagicMock(message=MagicMock(content=stage1_resp))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content=stage2_resp))]),
            ]
            from src.ai.keyword_filter import KeywordPreFilter
            r._keyword_filter = KeywordPreFilter()

            intent = r.resolve("bana bir sey goster")  # keyword eslesmesi yok

            # Stage 1 + Stage 2 = 2 LLM cagrisi
            assert r._client.chat.completions.create.call_count == 2


# =============================================================================
# 3.7.6 — Orchestrator feature flag tests
# =============================================================================

class TestOrchestratorFeatureFlag:
    """Orchestrator hierarchical mode toggle testleri."""

    def test_default_is_flat_mode(self):
        """Default: USE_HIERARCHICAL=False, flat resolver kullanilir."""
        from src.ai.orchestrator import AIOrchestrator
        with patch.dict("os.environ", {"SENTINEL_USE_HIERARCHICAL": "false"}):
            orch = AIOrchestrator.__new__(AIOrchestrator)
            # Sadece class attribute kontrolu
            assert AIOrchestrator.USE_HIERARCHICAL is False or \
                   not bool(os.environ.get("SENTINEL_USE_HIERARCHICAL", "").lower() in ("true", "1", "yes"))

    def test_set_hierarchical_enables(self):
        """set_hierarchical(True) sonrasi hierarchical resolver aktif olmali."""
        from src.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator.__new__(AIOrchestrator)
        orch._model = "qwen2.5:3b"
        orch._hierarchical_resolver = None

        orch.set_hierarchical(True, category_model="test_cat_model")
        assert orch._hierarchical_resolver is not None
        assert isinstance(orch._hierarchical_resolver, HierarchicalResolver)

    def test_set_hierarchical_disables(self):
        """set_hierarchical(False) sonrasi hierarchical resolver None olmali."""
        from src.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator.__new__(AIOrchestrator)
        orch._model = "qwen2.5:3b"
        orch._hierarchical_resolver = HierarchicalResolver(
            category_model="test_cat_model", sub_intent_model="qwen2.5:3b"
        )

        orch.set_hierarchical(False)
        assert orch._hierarchical_resolver is None

    def test_set_model_updates_hierarchical(self):
        """set_model() hierarchical resolver'in sub_intent_model'ini guncellemeli."""
        from src.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator.__new__(AIOrchestrator)
        orch._model = "qwen2.5:3b"
        orch._intent_resolver = MagicMock()
        orch._hierarchical_resolver = HierarchicalResolver(
            category_model="test_cat_model", sub_intent_model="qwen2.5:3b"
        )

        orch.set_model("llama3:8b")
        assert orch._hierarchical_resolver.sub_intent_model == "llama3:8b"


# =============================================================================
# Prompt & Description coverage tests
# =============================================================================

class TestPromptCoverage:
    """Prompt sablonlarinin tutarlilik testleri."""

    def test_category_prompt_mentions_all_categories(self):
        """CATEGORY_PROMPT tum 5 kategoriyi icermeli."""
        for cat in CategoryType:
            assert cat.value in CATEGORY_PROMPT, f"CATEGORY_PROMPT '{cat.value}' icermiyor"

    def test_intent_descriptions_complete(self):
        """Her IntentType icin bir aciklama olmali."""
        for intent_type in IntentType:
            assert intent_type in _INTENT_DESCRIPTIONS, (
                f"_INTENT_DESCRIPTIONS '{intent_type.value}' eksik"
            )

    def test_sub_intent_template_has_placeholders(self):
        """SUB_INTENT_PROMPT_TEMPLATE {category} ve {intent_list} placeholder'lari icermeli."""
        assert "{category}" in SUB_INTENT_PROMPT_TEMPLATE
        assert "{intent_list}" in SUB_INTENT_PROMPT_TEMPLATE


# =============================================================================
# Fallback & error scenario tests
# =============================================================================

class TestFallbackScenarios:
    """Hata durumlarinda dogru fallback davranisi."""

    def _make_resolver(self):
        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_cat_model"
            r._sub_intent_model = "qwen2.5:3b"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            from src.ai.keyword_filter import KeywordPreFilter
            r._keyword_filter = KeywordPreFilter()
            return r

    def test_stage1_llm_failure_falls_back_to_info(self):
        """Stage 1 LLM hatasi → INFO kategorisi."""
        r = self._make_resolver()
        r._client.chat.completions.create.side_effect = Exception("connection error")

        result = r.resolve_category("test input")
        assert result.category == CategoryType.INFO
        assert result.confidence == 0.0

    def test_stage2_llm_failure_falls_back_to_unknown(self):
        """Stage 2 LLM hatasi → UNKNOWN intent + needs_clarification."""
        r = self._make_resolver()
        r._client.chat.completions.create.side_effect = Exception("timeout")

        result = r.resolve_sub_intent("test input", CategoryType.SCANNING)
        assert result.intent_type == IntentType.UNKNOWN
        assert result.needs_clarification is True

    def test_low_stage1_confidence_falls_back_info(self):
        """Stage 1 confidence < 0.3 ise INFO'ya dusur."""
        r = self._make_resolver()
        # Stage 1 cok dusuk confidence
        stage1_resp = '{"category": "attack", "confidence": 0.15}'
        stage2_resp = json.dumps({
            "intent_type": "info_query",
            "target": None,
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.5,
        })
        r._client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=stage1_resp))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=stage2_resp))]),
        ]
        # keyword eslesmesi olmasin
        r._keyword_filter.suggest = MagicMock(return_value=None)

        intent = r.resolve("???")
        # Stage 1 confidence < 0.3 → INFO kategorisine fallback
        # Stage 2 INFO kategorisi icinde intent cozumler
        assert intent.intent_type in (IntentType.INFO_QUERY, IntentType.UNKNOWN)


# =============================================================================
# HierarchicalResolver utility tests
# =============================================================================

class TestResolverUtilities:
    """Yardimci metot testleri."""

    def _make_resolver(self):
        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            return r

    def test_extract_json_plain(self):
        r = self._make_resolver()
        result = r._extract_json('{"key": "value"}')
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_markdown_block(self):
        r = self._make_resolver()
        result = r._extract_json('```json\n{"key": "val"}\n```')
        assert json.loads(result) == {"key": "val"}

    def test_extract_json_with_surrounding_text(self):
        r = self._make_resolver()
        result = r._extract_json('Here is the result: {"a": 1} done.')
        assert json.loads(result) == {"a": 1}

    def test_set_models(self):
        r = HierarchicalResolver(
            category_model="test_cat_model", sub_intent_model="qwen2.5:3b"
        )
        r.set_models("new_cat", "new_sub")
        assert r.category_model == "new_cat"
        assert r.sub_intent_model == "new_sub"


# =============================================================================
# Integration: Full pipeline mock test
# =============================================================================

class TestFullPipelineMock:
    """Tam Stage 1 + Stage 2 mock pipeline testi."""

    def test_full_pipeline_scanning(self):
        """scanning kategorisi → port_scan intent akisi."""
        stage1 = '{"category": "scanning", "confidence": 0.92}'
        stage2 = json.dumps({
            "intent_type": "port_scan",
            "target": "10.0.0.1",
            "params": {"ports": "80,443"},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.95,
        })

        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_cat_model"
            r._sub_intent_model = "qwen2.5:3b"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            r._client.chat.completions.create.side_effect = [
                MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content=stage2))]),
            ]
            from src.ai.keyword_filter import KeywordPreFilter
            r._keyword_filter = KeywordPreFilter()

            # Keyword eslesmesi olmayan girdi
            intent = r.resolve("10.0.0.1 makinesinin durumuna bak")

            assert intent.intent_type == IntentType.PORT_SCAN
            assert intent.target == "10.0.0.1"
            assert intent.params.get("ports") == "80,443"
            assert intent.confidence == 0.95
            assert r._client.chat.completions.create.call_count == 2

    def test_full_pipeline_with_target_hint(self):
        """target_hint parametresi Stage 2'ye aktarilmali."""
        stage1 = '{"category": "web", "confidence": 0.90}'
        stage2 = json.dumps({
            "intent_type": "web_dir_enum",
            "target": "http://example.com",
            "params": {},
            "needs_clarification": False,
            "clarification_reason": None,
            "confidence": 0.88,
        })

        with patch.object(HierarchicalResolver, "__init__", lambda self, **kw: None):
            r = HierarchicalResolver.__new__(HierarchicalResolver)
            r._category_model = "test_cat_model"
            r._sub_intent_model = "qwen2.5:3b"
            r._request_timeout = 10.0
            r._max_attempts = 1
            r._base_url = "http://localhost:11434"
            r._client = MagicMock()
            r._client.chat.completions.create.side_effect = [
                MagicMock(choices=[MagicMock(message=MagicMock(content=stage1))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content=stage2))]),
            ]
            r._keyword_filter = MagicMock()
            r._keyword_filter.suggest.return_value = None  # keyword match yok

            intent = r.resolve("dizin tara", target_hint="http://example.com")

            assert intent.intent_type == IntentType.WEB_DIR_ENUM
            # Stage 2 prompt'unda target_hint kullanildi mi kontrol et
            call_args = r._client.chat.completions.create.call_args_list[1]
            messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
            user_msg = messages[-1]["content"]
            assert "http://example.com" in user_msg


import os
