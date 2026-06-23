"""Document storage port — durable storage for raw uploaded files.

The raw file is the heavy payload, so only the document id travels through the job
queue; a worker (or the reaper) reloads the bytes from here. Disk-backed today; an
object-storage adapter can drop in behind the same interface when the worker runs
on a separate host.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID


class DocumentStoragePort(Protocol):
    async def save(self, *, tenant_id: UUID, document_id: UUID, chunks: AsyncIterator[bytes]) -> int:
        """Stream the chunks to durable storage; return total bytes written."""
        ...

    async def load(self, *, tenant_id: UUID, document_id: UUID) -> bytes: ...

    async def delete(self, *, tenant_id: UUID, document_id: UUID) -> None: ...
