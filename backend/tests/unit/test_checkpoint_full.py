"""Tests for checkpoint summarization with mocked LLM."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.ai.context.checkpoint import _build_summarizer_input, maybe_create_checkpoint
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.entities import Conversation, Message
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.llm.value_objects import LLMCallResult, TokenUsage
from src.infrastructure.persistence.postgres.database import async_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_not_triggered_below_threshold(client: None) -> None:
    """If tokens since last checkpoint < 3000, no checkpoint is created."""
    tenant_id = uuid4()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.tenants.entities import Tenant

        t = Tenant.create(name="CP", slug=f"cp-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        tenant_id = t.id

        conv = Conversation.start(
            tenant_id=tenant_id, thread_id=f"cp-{uuid4().hex[:8]}", channel=ConversationChannel.WEB
        )
        await uow.conversations.save(conv)
        await uow.flush()

        msg = Message.create(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role=ConversationRole.USER,
            content="short msg",
            token_count=10,
        )
        await uow.messages.save(msg)
        await uow.commit()

        mock_llm = AsyncMock()
        await maybe_create_checkpoint(
            thread_id=conv.thread_id,
            tenant_id=tenant_id,
            channel=ConversationChannel.WEB,
            llm=mock_llm,
            uow=uow,
        )
        # LLM should NOT have been called
        mock_llm.chat_with_tools.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_triggered_above_threshold(client: None) -> None:
    """When tokens exceed 3000, a checkpoint message is created."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.tenants.entities import Tenant

        t = Tenant.create(name="CP2", slug=f"cp2-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()

        thread_id = f"cp2-{uuid4().hex[:8]}"
        conv = Conversation.start(tenant_id=t.id, thread_id=thread_id, channel=ConversationChannel.WEB)
        await uow.conversations.save(conv)
        await uow.flush()

        # Add messages totaling >3000 tokens
        for i in range(10):
            msg = Message.create(
                conversation_id=conv.id,
                tenant_id=t.id,
                role=ConversationRole.USER,
                content=f"message {i}" * 50,
                token_count=400,
            )
            await uow.messages.save(msg)
        await uow.commit()

        mock_llm = AsyncMock()
        mock_llm.chat_with_tools = AsyncMock(
            return_value=LLMCallResult(
                text='{"summary": "User asked 10 questions.", "current_state": {}}',
                usage=TokenUsage(input_tokens=100, output_tokens=50),
            )
        )

        await maybe_create_checkpoint(
            thread_id=thread_id,
            tenant_id=t.id,
            channel=ConversationChannel.WEB,
            llm=mock_llm,
            uow=uow,
        )
        await uow.commit()

        mock_llm.chat_with_tools.assert_called_once()

        # Verify checkpoint message was saved
        all_msgs = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        checkpoints = [m for m in all_msgs if m.is_checkpoint]
        assert len(checkpoints) == 1
        assert "User asked 10 questions" in checkpoints[0].content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_records_summarizer_usage(client: None) -> None:
    """The summarizer LLM call is billable and must be recorded (source=checkpoint)."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.tenants.entities import Tenant

        t = Tenant.create(name="CP3", slug=f"cp3-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()

        thread_id = f"cp3-{uuid4().hex[:8]}"
        conv = Conversation.start(tenant_id=t.id, thread_id=thread_id, channel=ConversationChannel.WEB)
        await uow.conversations.save(conv)
        await uow.flush()
        for i in range(10):
            await uow.messages.save(
                Message.create(
                    conversation_id=conv.id,
                    tenant_id=t.id,
                    role=ConversationRole.USER,
                    content=f"message {i}" * 50,
                    token_count=400,
                )
            )
        await uow.commit()

        mock_llm = AsyncMock()
        mock_llm.chat_with_tools = AsyncMock(
            return_value=LLMCallResult(
                text='{"summary": "Summary.", "current_state": {}}',
                usage=TokenUsage(input_tokens=2200, output_tokens=180),
                provider="openai",
                model="gpt-4o-mini",
            )
        )

        await maybe_create_checkpoint(
            thread_id=thread_id,
            tenant_id=t.id,
            channel=ConversationChannel.WEB,
            llm=mock_llm,
            uow=uow,
        )
        await uow.commit()

        usages = await uow.token_usages.list_for_tenant(t.id)
        checkpoint_usages = [u for u in usages if u.source == "checkpoint"]
        assert len(checkpoint_usages) == 1
        assert checkpoint_usages[0].input_tokens == 2200
        assert checkpoint_usages[0].output_tokens == 180


@pytest.mark.integration
@pytest.mark.asyncio
async def test_saved_messages_accumulate_token_count(client: None) -> None:
    """Messages saved without an explicit token_count get an estimate, so the
    checkpoint trigger (sum_tokens_since_checkpoint) actually accumulates."""
    from src.application.conversations.commands import SaveThreadMessage
    from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="CP4", slug=f"cp4-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        await uow.commit()

        thread_id = f"cp4-{uuid4().hex[:8]}"
        save_uc = SaveThreadMessageUseCase(uow=uow)
        result = None
        for _ in range(5):
            result = await save_uc.execute(
                SaveThreadMessage(
                    tenant_id=t.id,
                    thread_id=thread_id,
                    channel=ConversationChannel.WEB,
                    role=ConversationRole.USER,
                    content="This is a reasonably long message. " * 20,  # no token_count passed
                )
            )
        await uow.commit()

        assert result is not None
        total = await uow.messages.sum_tokens_since_checkpoint(result.conversation_id)
        assert total > 0  # was pinned at 0 before the estimate was populated


def test_build_summarizer_input_truncates() -> None:
    """Long message lists are truncated to _MAX_RECENT_MESSAGES."""
    messages: list[Any] = []
    for i in range(40):
        m = MagicMock()
        m.is_checkpoint = False
        m.role = "user"
        m.content = f"msg {i}"
        m.tool_data = None
        messages.append(m)

    result = _build_summarizer_input(messages)
    assert "older messages omitted" in result


def test_build_summarizer_input_includes_checkpoint() -> None:
    """Previous checkpoint state is included in the input."""
    checkpoint = MagicMock()
    checkpoint.is_checkpoint = True
    checkpoint.content = "previous state summary"
    checkpoint.tool_data = [{"checkpoint": {"summary": "old"}}]

    recent = MagicMock()
    recent.is_checkpoint = False
    recent.role = "user"
    recent.content = "new question"
    recent.tool_data = None

    result = _build_summarizer_input([checkpoint, recent])
    assert "previous state summary" in result
    assert "new question" in result
