"""Shared domain ports — cross-cutting contracts."""

from __future__ import annotations

from typing import Protocol


class NotificationPort(Protocol):
    """Send a notification to an asker via their original channel."""

    async def send_text(self, *, recipient: str, channel: str, message: str) -> bool: ...
