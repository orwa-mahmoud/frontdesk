"""Unit tests for the conversation token estimator."""

from __future__ import annotations

from src.domain.conversations.token_estimate import estimate_tokens


def test_blank_text_is_zero() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("   \n\t ") == 0


def test_short_text_counts_at_least_one() -> None:
    assert estimate_tokens("hi") == 1


def test_scales_with_length() -> None:
    # ~4 chars per token.
    assert estimate_tokens("a" * 40) == 10
    assert estimate_tokens("a" * 4000) == 1000


def test_monotonic() -> None:
    assert estimate_tokens("a" * 100) < estimate_tokens("a" * 200)
