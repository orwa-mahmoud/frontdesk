"""Notification routing port -- determines how to reach a recipient."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from src.domain.shared.exceptions import DomainError


@dataclass(frozen=True)
class ResolvedRoute:
    """Result of resolving how to reach a recipient."""

    channel: str  # "whatsapp", "telegram", "api"
    thread_id: str  # conversation thread_id to send in
    conversation_id: UUID | None = None  # existing conversation, if found
    tenant_id: UUID | None = None
    recipient_id: UUID | None = None


class NotificationRoutingError(DomainError):
    """Raised when no delivery channel could be resolved for a recipient."""

    http_status = 400

    def __init__(self, reason: str, *, context_data: dict[str, Any] | None = None) -> None:
        self.reason = reason
        self.context_data = context_data or {}
        super().__init__(reason)


class NotificationRoutingPort(Protocol):
    """Port for resolving the best delivery channel for a notification recipient."""

    async def resolve_route(
        self,
        *,
        tenant_id: UUID,
        recipient_id: UUID,
        recipient_type: str,
    ) -> ResolvedRoute: ...
