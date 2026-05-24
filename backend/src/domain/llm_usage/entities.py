"""TokenUsage aggregate — one row per LLM call."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.domain.llm_usage.events import TokenUsageRecorded
from src.domain.llm_usage.pricing import calculate_cost
from src.domain.shared.entities import BaseEntity


@dataclass(eq=False, kw_only=True)
class TokenUsage(BaseEntity):
    tenant_id: UUID
    thread_id: str | None
    request_id: str | None
    source: str  # e.g. "asker", "owner", "ingestion"
    channel: str | None  # e.g. "whatsapp", "telegram", "web"
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    input_cost: Decimal
    cache_read_cost: Decimal
    output_cost: Decimal
    created_at: datetime

    @classmethod
    def record(
        cls,
        *,
        tenant_id: UUID,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        thread_id: str | None = None,
        request_id: str | None = None,
        source: str = "asker",
        channel: str | None = None,
    ) -> TokenUsage:
        cost = calculate_cost(
            model=model,
            input_tokens=input_tokens,
            cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens,
        )
        usage = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            thread_id=thread_id,
            request_id=request_id,
            source=source,
            channel=channel,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            input_cost=cost.input_cost,
            cache_read_cost=cost.cache_read_cost,
            output_cost=cost.output_cost,
            created_at=datetime.now(UTC),
        )
        usage._is_new = True
        usage._emit(
            TokenUsageRecorded(
                usage_id=usage.id,
                tenant_id=tenant_id,
                request_id=request_id,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=cost.total,
            )
        )
        return usage

    @property
    def total_cost(self) -> Decimal:
        return self.input_cost + self.cache_read_cost + self.output_cost
