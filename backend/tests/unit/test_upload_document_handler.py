"""Unit tests for the document upload handler's pre-stream guards."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.drivers.api.v1.documents.routes import _MAX_UPLOAD_BYTES, _capped_stream, upload_document


@pytest.mark.asyncio
async def test_rejects_oversized_upload_before_streaming() -> None:
    file = MagicMock()
    file.filename = "big.pdf"
    file.size = _MAX_UPLOAD_BYTES + 1
    file.read = AsyncMock()  # must not be called — we reject before streaming a byte

    with pytest.raises(HTTPException) as exc:
        await upload_document(current_user=MagicMock(), uow=MagicMock(), job_pool=AsyncMock(), file=file)

    assert exc.value.status_code == 413
    file.read.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_missing_filename() -> None:
    file = MagicMock()
    file.filename = ""

    with pytest.raises(HTTPException) as exc:
        await upload_document(current_user=MagicMock(), uow=MagicMock(), job_pool=AsyncMock(), file=file)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_capped_stream_aborts_when_actual_size_exceeds_cap() -> None:
    # A file whose declared size lied: streaming reveals it is over the cap mid-flight.
    file = MagicMock()
    file.read = AsyncMock(side_effect=[b"x" * 4, b"x" * 4, b""])

    collected = b""
    with pytest.raises(HTTPException) as exc:
        async for chunk in _capped_stream(file, cap=6):
            collected += chunk

    assert exc.value.status_code == 413
    assert collected == b"x" * 4  # the first under-cap chunk streamed before the abort
