"""GetTenantUsageStats — aggregated rollup for the dashboard."""

from __future__ import annotations

from src.application.llm_usage.dtos import UsageStatsDTO
from src.application.llm_usage.queries import GetTenantUsageStats
from src.application.shared.unit_of_work import UnitOfWork


class GetTenantUsageStatsUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetTenantUsageStats) -> UsageStatsDTO:
        stats = await self._uow.token_usages.aggregate_for_tenant(
            query.tenant_id,
            since=query.since,
        )
        return UsageStatsDTO(
            total_input_tokens=stats.total_input_tokens,
            total_output_tokens=stats.total_output_tokens,
            total_cache_read_tokens=stats.total_cache_read_tokens,
            total_input_cost=stats.total_input_cost,
            total_cache_read_cost=stats.total_cache_read_cost,
            total_output_cost=stats.total_output_cost,
            total_cost=stats.total_cost,
            total_calls=stats.total_calls,
        )
