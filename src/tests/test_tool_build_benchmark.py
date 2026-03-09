from scripts.tool_build_benchmark import (
    NEGATIVE_SCENARIOS,
    POSITIVE_SCENARIOS,
    build_parameter_coverage,
    run_build_benchmark,
)
from src.ai.tool_registry import _EXECUTION_REGISTRY
from src.core.tool_base import TOOL_CLASS_MAP


def test_tool_build_benchmark_matrix_covers_all_tools_and_parameters():
    scenarios = POSITIVE_SCENARIOS + NEGATIVE_SCENARIOS
    coverage = build_parameter_coverage(scenarios)

    assert set(coverage) == set(TOOL_CLASS_MAP)

    for item in coverage.values():
        assert item.missing_parameters == [], f"{item.tool_id} missing params: {item.missing_parameters}"

    covered_tools = {scenario.tool_id for scenario in POSITIVE_SCENARIOS}
    execution_tools = {mapping["tool_id"] for mapping in _EXECUTION_REGISTRY.values()}
    assert execution_tools.issubset(covered_tools)


def test_tool_build_benchmark_passes_all_scenarios():
    report = run_build_benchmark(include_negative=True)

    assert report.total_cases == len(POSITIVE_SCENARIOS) + len(NEGATIVE_SCENARIOS)
    assert report.failed == 0
    assert report.overall_pass is True