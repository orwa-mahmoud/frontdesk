"""LLM usage DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class UsageStatsDTO:
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_input_cost: Decimal
    total_cache_read_cost: Decimal
    total_output_cost: Decimal
    total_cost: Decimal
    total_calls: int
