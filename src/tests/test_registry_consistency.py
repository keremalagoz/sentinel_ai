"""Registry consistency guard tests.

Amaç: Mimari drift'i CI seviyesinde erken yakalamak.
"""

from src.ai.tool_registry import (
    get_execution_intents,
    get_required_execution_tool_ids,
    validate_execution_registry,
)
from src.core.sentinel_coordinator import SentinelCoordinator


def test_execution_intents_are_valid_in_tool_registry():
    ok, errors = validate_execution_registry()
    assert ok, f"Execution registry invalid: {errors}"
    assert get_execution_intents(), "Execution intent set should not be empty"


def test_execution_tool_ids_are_registered_in_coordinator():
    coordinator = SentinelCoordinator(db_path=":memory:")
    try:
        registered = set(coordinator.get_available_tools())
        required = get_required_execution_tool_ids()

        missing = sorted(required - registered)
        assert not missing, f"Missing registered tools for execution mapping: {missing}"

        ok, errors = validate_execution_registry(registered)
        assert ok, f"Runtime registry validation failed: {errors}"
    finally:
        coordinator.cleanup()
