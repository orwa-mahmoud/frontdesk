"""LLM usage commands."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class RecordTokenUsage:
    tenant_id: UUID
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    thread_id: str | None = None
    request_id: str | None = None
    source: str = "asker"
    channel: str | None = None
