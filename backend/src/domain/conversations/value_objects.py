"""Conversation value objects."""

from __future__ import annotations

from enum import StrEnum


class ConversationRole(StrEnum):
    """Roles for individual messages within a thread."""

    USER = "user"  # the asker (external) or the owner (in owner-AI chat mode)
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationChannel(StrEnum):
    """Channel a conversation originated from."""

    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEB = "web"
    OWNER_DASHBOARD = "owner_dashboard"  # owner chatting with their own AI
    API = "api"
