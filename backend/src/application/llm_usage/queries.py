"""LLM usage queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class GetTenantUsageStats:
    tenant_id: UUID
    since: datetime | None = None
