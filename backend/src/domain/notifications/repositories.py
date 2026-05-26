"""Notification failure repository port."""

from __future__ import annotations

from typing import Protocol

from src.domain.notifications.entities import NotificationFailure


class NotificationFailureRepository(Protocol):
    """Port for persisting notification failures."""

    async def save(self, failure: NotificationFailure) -> None: ...
