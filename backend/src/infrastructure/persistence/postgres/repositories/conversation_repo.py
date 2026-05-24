"""PostgreSQL Conversation repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.conversations.entities import Conversation
from src.domain.conversations.value_objects import ConversationChannel
from src.infrastructure.persistence.postgres.models.conversation import ConversationModel


class PostgresConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, conversation: Conversation) -> None:
        if conversation.is_new:
            self._session.add(self._to_model(conversation))
            conversation.mark_persisted()
            return
        model = await self._session.get(ConversationModel, conversation.id)
        if model is None:
            self._session.add(self._to_model(conversation))
            return
        model.updated_at = conversation.updated_at
        model.last_message_at = conversation.last_message_at

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        model = await self._session.get(ConversationModel, conversation_id)
        return self._to_entity(model) if model else None

    async def get_by_thread_id(self, thread_id: str) -> Conversation | None:
        stmt = select(ConversationModel).where(ConversationModel.thread_id == thread_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_model(c: Conversation) -> ConversationModel:
        return ConversationModel(
            id=c.id,
            tenant_id=c.tenant_id,
            thread_id=c.thread_id,
            channel=c.channel.value,
            participant_id=c.participant_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            last_message_at=c.last_message_at,
        )

    @staticmethod
    def _to_entity(m: ConversationModel) -> Conversation:
        return Conversation(
            id=m.id,
            tenant_id=m.tenant_id,
            thread_id=m.thread_id,
            channel=ConversationChannel(m.channel),
            participant_id=m.participant_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            last_message_at=m.last_message_at,
        )
