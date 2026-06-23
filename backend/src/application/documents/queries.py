"""Document queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class ListDocuments:
    tenant_id: UUID
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True, kw_only=True)
class ListProcessingDocuments:
    tenant_id: UUID
    # Only documents touched since this cutoff are "in flight"; older ones are
    # considered stuck and left to the reaper, so the UI stops polling them.
    active_since: datetime


@dataclass(frozen=True, kw_only=True)
class RetrieveForQuery:
    tenant_id: UUID
    query: str
    top_k: int = 8
