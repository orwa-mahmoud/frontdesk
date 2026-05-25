"""Unit tests for notification port shape."""

from __future__ import annotations

from src.domain.shared.ports import NotificationPort


def test_port_is_protocol():
    assert hasattr(NotificationPort, "send_text")
