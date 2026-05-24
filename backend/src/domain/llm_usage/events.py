"""LLM usage domain events."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class TokenUsageRecorded(DomainEvent):
    usage_id: UUID
    tenant_id: UUID
    request_id: str | None
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_cost: Decimal
