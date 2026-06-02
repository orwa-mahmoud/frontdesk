"""RecordTokenUsage — append a usage row for one LLM call."""

from __future__ import annotations

import structlog

from src.application.llm_usage.commands import RecordTokenUsage
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.llm_usage.entities import TokenUsage
from src.domain.llm_usage.pricing import get_model_pricing

logger = structlog.get_logger()


class RecordTokenUsageUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: RecordTokenUsage) -> None:
        if get_model_pricing(cmd.model) is None:
            # Cost is recorded as $0 for models absent from the pricing table — warn
            # so the silent under-count is visible and the rate can be added (the
            # model field is owner-editable free text).
            logger.warning("llm_usage.unknown_model_pricing", model=cmd.model, provider=cmd.provider)

        usage = TokenUsage.record(
            tenant_id=cmd.tenant_id,
            provider=cmd.provider,
            model=cmd.model,
            input_tokens=cmd.input_tokens,
            output_tokens=cmd.output_tokens,
            cache_read_tokens=cmd.cache_read_tokens,
            thread_id=cmd.thread_id,
            request_id=cmd.request_id,
            source=cmd.source,
            channel=cmd.channel,
        )
        await self._uow.token_usages.save(usage)
        self._uow.track(usage)
