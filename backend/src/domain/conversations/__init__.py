"""Conversations domain — threads and messages."""

from src.domain.conversations.entities import Conversation, Message
from src.domain.conversations.events import MessageSaved
from src.domain.conversations.repositories import ConversationRepository, MessageRepository
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole

__all__ = [
    "Conversation",
    "ConversationChannel",
    "ConversationRepository",
    "ConversationRole",
    "Message",
    "MessageRepository",
    "MessageSaved",
]
