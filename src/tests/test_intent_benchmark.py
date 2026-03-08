from dataclasses import asdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from src.ai.schemas import CategoryType, Intent, IntentType


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "intent_benchmark.py"
SPEC = spec_from_file_location("intent_benchmark", SCRIPT_PATH)
intent_benchmark = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(intent_benchmark)


def test_evaluate_case_exact_match():
    case = intent_benchmark.BenchmarkCase(
        input_text="80 ve 443 portlarini kontrol et 10.0.0.1 de",
        expected_intent=IntentType.PORT_SCAN,
        expected_category=CategoryType.SCANNING,
        expected_target="10.0.0.1",
        expected_params={"ports": "80,443"},
    )
    intent = Intent(
        intent_type=IntentType.PORT_SCAN,
        target="10.0.0.1",
        params={"ports": "80,443"},
        needs_clarification=False,
        clarification_reason=None,
        confidence=0.91,
    )

    result = intent_benchmark.evaluate_case(
        case,
        intent,
        latency_ms=42.4,
        actual_category=CategoryType.SCANNING,
    )

    assert result.correct is True
    assert result.target_correct is True
    assert result.params_correct is True
    assert result.clarification_correct is True
    assert result.exact_match is True
    assert result.score_pct == 100.0


def test_evaluate_case_flags_param_hallucination():
    case = intent_benchmark.BenchmarkCase(
        input_text="example.com domain bilgilerini getir",
        expected_intent=IntentType.WHOIS_LOOKUP,
        expected_category=CategoryType.RECON,
        expected_target="example.com",
    )
    intent = Intent(
        intent_type=IntentType.WHOIS_LOOKUP,
        target="example.com",
        params={"unexpected": "value"},
        needs_clarification=False,
        clarification_reason=None,
        confidence=0.74,
    )

    result = intent_benchmark.evaluate_case(
        case,
        intent,
        latency_ms=19.8,
        actual_category=CategoryType.RECON,
    )

    assert result.correct is True
    assert result.target_correct is True
    assert result.params_correct is False
    assert result.exact_match is False
    assert result.score_pct == 90.0


def test_build_prompt_signatures_is_hierarchical_only():
    signatures = intent_benchmark.build_prompt_signatures()

    assert set(signatures) == {"category_prompt", "sub_intent_prompt_template"}


def test_finalize_summary_computes_prompt_metrics():
    summary = intent_benchmark.BenchmarkSummary(total=2, mode="hierarchical", model="test-model")
    summary.results = [
        asdict(
            intent_benchmark.CaseResult(
                input_text="case-1",
                expected=IntentType.PORT_SCAN.value,
                actual=IntentType.PORT_SCAN.value,
                confidence=0.9,
                keyword_suggestion=None,
                correct=True,
                latency_ms=10.0,
                expected_category=CategoryType.SCANNING.value,
                actual_category=CategoryType.SCANNING.value,
                category_correct=True,
                target_correct=True,
                params_correct=True,
                clarification_correct=True,
                exact_match=True,
                score_pct=100.0,
            )
        ),
        asdict(
            intent_benchmark.CaseResult(
                input_text="case-2",
                expected=IntentType.WHOIS_LOOKUP.value,
                actual=IntentType.DNS_LOOKUP.value,
                confidence=0.6,
                keyword_suggestion=None,
                correct=False,
                latency_ms=30.0,
                expected_category=CategoryType.RECON.value,
                actual_category=CategoryType.RECON.value,
                category_correct=True,
                target_correct=False,
                params_correct=False,
                clarification_correct=True,
                exact_match=False,
                score_pct=20.0,
            )
        ),
    ]

    finalized = intent_benchmark.finalize_summary(summary)

    assert finalized.resolved == 2
    assert finalized.correct == 1
    assert finalized.accuracy_pct == 50.0
    assert finalized.exact_match_pct == 50.0
    assert finalized.category_accuracy_pct == 100.0
    assert finalized.target_accuracy_pct == 50.0
    assert finalized.params_accuracy_pct == 50.0
    assert finalized.clarification_accuracy_pct == 100.0
    assert finalized.prompt_quality_pct == 60.0
    assert finalized.avg_latency_ms == 20.0
    assert finalized.confusion_matrix[IntentType.PORT_SCAN.value][IntentType.PORT_SCAN.value] == 1
    assert finalized.confusion_matrix[IntentType.WHOIS_LOOKUP.value][IntentType.DNS_LOOKUP.value] == 1
