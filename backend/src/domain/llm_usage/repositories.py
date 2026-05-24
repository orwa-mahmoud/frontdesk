"""TokenUsage repository port + aggregated-stats projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.llm_usage.entities import TokenUsage


@dataclass(frozen=True, kw_only=True)
class UsageStats:
    """Aggregated per-tenant usage projection."""

    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_input_cost: Decimal
    total_cache_read_cost: Decimal
    total_output_cost: Decimal
    total_calls: int

    @property
    def total_cost(self) -> Decimal:
        return self.total_input_cost + self.total_cache_read_cost + self.total_output_cost


class TokenUsageRepository(Protocol):
    async def save(self, usage: TokenUsage) -> None: ...

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[TokenUsage]: ...

    async def aggregate_for_tenant(
        self,
        tenant_id: UUID,
        *,
        since: datetime | None = None,
    ) -> UsageStats: ...
