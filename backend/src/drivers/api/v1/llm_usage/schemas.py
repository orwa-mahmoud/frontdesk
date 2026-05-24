"""LLM usage API schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class UsageStatsResponse(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_input_cost: Decimal
    total_cache_read_cost: Decimal
    total_output_cost: Decimal
    total_cost: Decimal
    total_calls: int
