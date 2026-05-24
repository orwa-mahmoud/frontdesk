"""Unit tests for the tiktoken-backed token counter."""

from __future__ import annotations

from src.infrastructure.llm.token_counter import count_tokens


def test_empty_string_is_zero() -> None:
    assert count_tokens("") == 0


def test_simple_string_has_expected_token_count() -> None:
    # The exact count is encoding-dependent but always positive and small.
    n = count_tokens("hello world")
    assert 1 <= n <= 5
