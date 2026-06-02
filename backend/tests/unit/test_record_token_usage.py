"""Unit tests for RecordTokenUsageUseCase (cost-gap observability)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase


def _make_uow() -> MagicMock:
    uow = MagicMock()
    uow.token_usages = MagicMock()
    uow.token_usages.save = AsyncMock()
    uow.track = MagicMock()
    return uow


def _cmd(model: str) -> RecordTokenUsage:
    return RecordTokenUsage(
        tenant_id=uuid4(),
        provider="openai",
        model=model,
        input_tokens=100,
        output_tokens=50,
    )


@pytest.mark.asyncio
async def test_known_model_records_without_warning() -> None:
    uow = _make_uow()
    with patch("src.application.llm_usage.use_cases.record_token_usage.logger") as log:
        await RecordTokenUsageUseCase(uow=uow).execute(_cmd("gpt-4o-mini"))
    uow.token_usages.save.assert_awaited_once()
    log.warning.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_model_warns_but_still_records() -> None:
    uow = _make_uow()
    with patch("src.application.llm_usage.use_cases.record_token_usage.logger") as log:
        await RecordTokenUsageUseCase(uow=uow).execute(_cmd("totally-made-up-model"))
    # Usage is still persisted (cost recorded as 0) — but the gap is logged.
    uow.token_usages.save.assert_awaited_once()
    log.warning.assert_called_once()
