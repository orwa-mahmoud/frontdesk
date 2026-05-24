"""Integration tests for the conversation persistence layer."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.queries import LoadThreadHistory
from src.application.conversations.use_cases.load_thread_history import LoadThreadHistoryUseCase
from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory


async def _seed_tenant() -> Tenant:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="Test Tenant", slug=f"t-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.commit()
        return tenant


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_then_load_round_trip(client: None) -> None:
    tenant = await _seed_tenant()
    thread_id = f"thread-{uuid4().hex[:8]}"

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await SaveThreadMessageUseCase(uow=uow).execute(
            SaveThreadMessage(
                tenant_id=tenant.id,
                thread_id=thread_id,
                channel=ConversationChannel.WEB,
                role=ConversationRole.USER,
                content="What are your office hours?",
                token_count=8,
            )
        )
        await SaveThreadMessageUseCase(uow=uow).execute(
            SaveThreadMessage(
                tenant_id=tenant.id,
                thread_id=thread_id,
                channel=ConversationChannel.WEB,
                role=ConversationRole.ASSISTANT,
                content="We're open 9-5 Sunday to Thursday.",
                token_count=10,
            )
        )
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        history = await LoadThreadHistoryUseCase(uow=uow).execute(LoadThreadHistory(thread_id=thread_id))

    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "What are your office hours?"
    assert history[1].role == "assistant"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_call_args_and_result_preserved(client: None) -> None:
    tenant = await _seed_tenant()
    thread_id = f"thread-{uuid4().hex[:8]}"

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await SaveThreadMessageUseCase(uow=uow).execute(
            SaveThreadMessage(
                tenant_id=tenant.id,
                thread_id=thread_id,
                channel=ConversationChannel.WEB,
                role=ConversationRole.ASSISTANT,
                content="",
                tool_call_id="call_abc",
                tool_args={"query": "office hours", "filters": {"area": "main"}},
            )
        )
        await SaveThreadMessageUseCase(uow=uow).execute(
            SaveThreadMessage(
                tenant_id=tenant.id,
                thread_id=thread_id,
                channel=ConversationChannel.WEB,
                role=ConversationRole.TOOL,
                content="Found 3 matching FAQs.",
                tool_call_id="call_abc",
                tool_result={"chunks": [{"id": "1"}, {"id": "2"}, {"id": "3"}]},
            )
        )
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        history = await LoadThreadHistoryUseCase(uow=uow).execute(LoadThreadHistory(thread_id=thread_id))

    assistant_msg = next(m for m in history if m.role == "assistant")
    tool_msg = next(m for m in history if m.role == "tool")
    assert assistant_msg.tool_call_id == "call_abc"
    assert assistant_msg.tool_args == {"query": "office hours", "filters": {"area": "main"}}
    assert tool_msg.tool_result == {"chunks": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_aware_query(client: None) -> None:
    tenant = await _seed_tenant()
    thread_id = f"thread-{uuid4().hex[:8]}"

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        # Older messages
        for i in range(3):
            await SaveThreadMessageUseCase(uow=uow).execute(
                SaveThreadMessage(
                    tenant_id=tenant.id,
                    thread_id=thread_id,
                    channel=ConversationChannel.WEB,
                    role=ConversationRole.USER,
                    content=f"old msg {i}",
                    token_count=5,
                )
            )
        # Checkpoint row
        await SaveThreadMessageUseCase(uow=uow).execute(
            SaveThreadMessage(
                tenant_id=tenant.id,
                thread_id=thread_id,
                channel=ConversationChannel.WEB,
                role=ConversationRole.ASSISTANT,
                content="(structured summary)",
                hidden=True,
                is_checkpoint=True,
            )
        )
        # Newer messages
        for i in range(2):
            await SaveThreadMessageUseCase(uow=uow).execute(
                SaveThreadMessage(
                    tenant_id=tenant.id,
                    thread_id=thread_id,
                    channel=ConversationChannel.WEB,
                    role=ConversationRole.USER,
                    content=f"new msg {i}",
                    token_count=7,
                )
            )
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = await uow.conversations.get_by_thread_id(thread_id)
        assert conv is not None
        since_ckpt = await uow.messages.list_since_last_checkpoint(conv.id)
        # 1 checkpoint + 2 new messages
        assert len(since_ckpt) == 3
        token_sum = await uow.messages.sum_tokens_since_checkpoint(conv.id)
        # Only non-checkpoint messages after the checkpoint contribute: 2 * 7 = 14
        assert token_sum == 14
