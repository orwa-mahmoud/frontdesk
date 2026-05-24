"""PostgreSQL TokenUsage repository."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.llm_usage.entities import TokenUsage
from src.domain.llm_usage.repositories import UsageStats
from src.infrastructure.persistence.postgres.models.token_usage import TokenUsageModel


class PostgresTokenUsageRepository:
    """Concrete TokenUsage repository — implements `TokenUsageRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, usage: TokenUsage) -> None:
        if usage.is_new:
            self._session.add(self._to_model(usage))
            usage.mark_persisted()
            return
        # Token usage rows are append-only; updates aren't expected. If asked,
        # treat as upsert to stay idempotent.
        existing = await self._session.get(TokenUsageModel, usage.id)
        if existing is None:
            self._session.add(self._to_model(usage))

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[TokenUsage]:
        stmt = select(TokenUsageModel).where(TokenUsageModel.tenant_id == tenant_id)
        if since is not None:
            stmt = stmt.where(TokenUsageModel.created_at >= since)
        stmt = stmt.order_by(TokenUsageModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def aggregate_for_tenant(
        self,
        tenant_id: UUID,
        *,
        since: datetime | None = None,
    ) -> UsageStats:
        stmt = select(
            func.coalesce(func.sum(TokenUsageModel.input_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.output_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.cache_read_tokens), 0),
            func.coalesce(func.sum(TokenUsageModel.input_cost), Decimal("0")),
            func.coalesce(func.sum(TokenUsageModel.cache_read_cost), Decimal("0")),
            func.coalesce(func.sum(TokenUsageModel.output_cost), Decimal("0")),
            func.count(TokenUsageModel.id),
        ).where(TokenUsageModel.tenant_id == tenant_id)

        if since is not None:
            stmt = stmt.where(TokenUsageModel.created_at >= since)

        result = await self._session.execute(stmt)
        row = result.one()
        return UsageStats(
            total_input_tokens=int(row[0]),
            total_output_tokens=int(row[1]),
            total_cache_read_tokens=int(row[2]),
            total_input_cost=Decimal(row[3]),
            total_cache_read_cost=Decimal(row[4]),
            total_output_cost=Decimal(row[5]),
            total_calls=int(row[6]),
        )

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(usage: TokenUsage) -> TokenUsageModel:
        return TokenUsageModel(
            id=usage.id,
            tenant_id=usage.tenant_id,
            thread_id=usage.thread_id,
            request_id=usage.request_id,
            source=usage.source,
            channel=usage.channel,
            provider=usage.provider,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=usage.cache_read_tokens,
            input_cost=usage.input_cost,
            cache_read_cost=usage.cache_read_cost,
            output_cost=usage.output_cost,
            created_at=usage.created_at,
        )

    @staticmethod
    def _to_entity(model: TokenUsageModel) -> TokenUsage:
        return TokenUsage(
            id=model.id,
            tenant_id=model.tenant_id,
            thread_id=model.thread_id,
            request_id=model.request_id,
            source=model.source,
            channel=model.channel,
            provider=model.provider,
            model=model.model,
            input_tokens=model.input_tokens,
            output_tokens=model.output_tokens,
            cache_read_tokens=model.cache_read_tokens,
            input_cost=model.input_cost,
            cache_read_cost=model.cache_read_cost,
            output_cost=model.output_cost,
            created_at=model.created_at,
        )
