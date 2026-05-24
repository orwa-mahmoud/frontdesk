"""Conversation domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MessageSaved(DomainEvent):
    message_id: UUID
    conversation_id: UUID
    tenant_id: UUID
    role: str
    request_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ConversationStarted(DomainEvent):
    conversation_id: UUID
    tenant_id: UUID
    thread_id: str
    channel: str
