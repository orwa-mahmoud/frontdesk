"""Unit tests for WhatsApp long-message chunking (Meta's 4096-char body limit)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.channels.whatsapp import _WHATSAPP_TEXT_LIMIT, WhatsAppAdapter, _chunk_text


def test_chunk_text_short_returns_single_piece() -> None:
    assert _chunk_text("hello", 4096) == ["hello"]


def test_chunk_text_splits_long_text_losslessly() -> None:
    text = "a" * (4096 * 2 + 10)
    chunks = _chunk_text(text, 4096)
    assert len(chunks) == 3
    assert all(len(c) <= 4096 for c in chunks)
    assert "".join(chunks) == text  # no data lost across the split


@pytest.mark.asyncio
async def test_send_text_splits_long_reply_into_multiple_sends() -> None:
    adapter = WhatsAppAdapter(phone_number_id="p", access_token="t")
    long_text = "x" * (_WHATSAPP_TEXT_LIMIT * 2 + 5)
    with patch.object(adapter, "_send_text_chunk", new_callable=AsyncMock, return_value={"ok": True}) as mock_chunk:
        await adapter.send_text("+123", long_text)
    assert mock_chunk.await_count == 3


@pytest.mark.asyncio
async def test_send_text_single_send_for_short_reply() -> None:
    adapter = WhatsAppAdapter(phone_number_id="p", access_token="t")
    with patch.object(adapter, "_send_text_chunk", new_callable=AsyncMock, return_value={"ok": True}) as mock_chunk:
        await adapter.send_text("+123", "short reply")
    assert mock_chunk.await_count == 1


@pytest.mark.asyncio
async def test_send_text_without_credentials_returns_none() -> None:
    adapter = WhatsAppAdapter(phone_number_id="", access_token="")
    assert await adapter.send_text("+123", "hi") is None
