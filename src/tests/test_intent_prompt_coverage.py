"""Prompt coverage tests for intent resolver templates."""

import pytest

from src.ai.intent_resolver import INTENT_RESOLVER_PROMPT


@pytest.mark.parametrize("param_key", ["verbose", "no_ping", "aggressive", "traceroute", "osscan_guess", "scripts"])
def test_intent_resolver_prompt_mentions_extended_params(param_key: str):
    assert param_key in INTENT_RESOLVER_PROMPT
