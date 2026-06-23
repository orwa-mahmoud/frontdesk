"""Unit tests for the on-disk document storage adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest

from src.infrastructure.storage.disk_document_storage import DiskDocumentStorage


async def _chunks(*parts: bytes) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


@pytest.mark.asyncio
async def test_save_load_delete_roundtrip(tmp_path: Path) -> None:
    storage = DiskDocumentStorage(str(tmp_path))
    tenant_id, document_id = uuid4(), uuid4()

    written = await storage.save(tenant_id=tenant_id, document_id=document_id, chunks=_chunks(b"hello ", b"world"))
    assert written == 11

    # Stored under <root>/<tenant_id>/<document_id> and reads back byte-for-byte.
    assert (tmp_path / str(tenant_id) / str(document_id)).is_file()
    assert await storage.load(tenant_id=tenant_id, document_id=document_id) == b"hello world"

    await storage.delete(tenant_id=tenant_id, document_id=document_id)
    with pytest.raises(FileNotFoundError):
        await storage.load(tenant_id=tenant_id, document_id=document_id)


@pytest.mark.asyncio
async def test_delete_missing_is_a_noop(tmp_path: Path) -> None:
    storage = DiskDocumentStorage(str(tmp_path))
    # Deleting a never-written document must not raise (delete is idempotent).
    await storage.delete(tenant_id=uuid4(), document_id=uuid4())
