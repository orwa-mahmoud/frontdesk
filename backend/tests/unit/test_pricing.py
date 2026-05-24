"""Unit tests for the pricing module — pure math, no IO."""

from __future__ import annotations

from decimal import Decimal

from src.domain.llm_usage.pricing import calculate_cost, get_model_pricing


def test_known_model_resolves() -> None:
    pricing = get_model_pricing("gpt-4o-mini")
    assert pricing is not None
    assert pricing.provider == "openai"


def test_unknown_model_costs_zero() -> None:
    cost = calculate_cost(model="nonexistent-model", input_tokens=1000, cache_read_tokens=0, output_tokens=500)
    assert cost.total == Decimal("0")


def test_gpt_4o_mini_cost_math() -> None:
    # $0.15 per 1M input, $0.60 per 1M output. 100k in + 50k out:
    # input = 0.15 * 0.1 = 0.015 ; output = 0.60 * 0.05 = 0.03 ; total = 0.045
    cost = calculate_cost(
        model="gpt-4o-mini",
        input_tokens=100_000,
        cache_read_tokens=0,
        output_tokens=50_000,
    )
    assert cost.input_cost == Decimal("0.01500000")
    assert cost.output_cost == Decimal("0.03000000")
    assert cost.total == Decimal("0.04500000")


def test_anthropic_cache_read_is_cheaper() -> None:
    pricing = get_model_pricing("claude-sonnet-4-5")
    assert pricing is not None
    assert pricing.cache_read_per_million < pricing.input_per_million


def test_total_includes_all_three_segments() -> None:
    cost = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # input 3.00 + cache 0.30 + output 15.00 = 18.30
    assert cost.total == Decimal("18.30000000")
