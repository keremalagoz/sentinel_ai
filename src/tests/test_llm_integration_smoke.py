import pytest

from src.ai.hierarchical_resolver import HierarchicalResolver
from src.ai.schemas import IntentType


@pytest.mark.llm
def test_live_hierarchical_resolver_smoke_dns_lookup() -> None:
    """Live LLM smoke test for nightly/manual runs."""
    resolver = HierarchicalResolver(sub_intent_model="qwen2.5:3b")

    if not resolver.check_available():
        pytest.skip("Ollama/LLM service is not available")

    intent = resolver.resolve("example.com MX kayitlarini sorgula")

    assert intent.intent_type in {
        IntentType.DNS_LOOKUP,
        IntentType.INFO_QUERY,
        IntentType.UNKNOWN,
    }
