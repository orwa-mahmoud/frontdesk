"""Disk-backed document storage — streams raw uploads to a local volume.

Files live at ``<root>/<tenant_id>/<document_id>``. The root is a volume shared
between the web and worker containers. Swap this for an object-storage adapter
(behind the same DocumentStoragePort) when the worker runs on a separate host.

File I/O is blocking, so each operation is offloaded with ``asyncio.to_thread`` to
keep the event loop free.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID


class DiskDocumentStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _path(self, tenant_id: UUID, document_id: UUID) -> Path:
        return self._root / str(tenant_id) / str(document_id)

    async def save(self, *, tenant_id: UUID, document_id: UUID, chunks: AsyncIterator[bytes]) -> int:
        path = self._path(tenant_id, document_id)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        handle = await asyncio.to_thread(path.open, "wb")
        total = 0
        try:
            async for chunk in chunks:
                await asyncio.to_thread(handle.write, chunk)
                total += len(chunk)
        finally:
            await asyncio.to_thread(handle.close)
        return total

    async def load(self, *, tenant_id: UUID, document_id: UUID) -> bytes:
        return await asyncio.to_thread(self._path(tenant_id, document_id).read_bytes)

    async def delete(self, *, tenant_id: UUID, document_id: UUID) -> None:
        await asyncio.to_thread(self._path(tenant_id, document_id).unlink, missing_ok=True)
