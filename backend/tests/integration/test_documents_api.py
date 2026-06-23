"""Integration tests for document upload + list + delete.

Ingestion now runs on the Arq worker, not in-request. Under tests the job pool is a
no-op mock (see conftest), so an upload leaves the document `uploaded` with its bytes
on disk; tests that need the heavy pipeline call the worker's `ingest_document` directly.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.config.settings import get_settings
from src.drivers.jobs.ingestion import ingest_document
from tests.conftest import register_and_token


def _stored_path(tenant_id: str, document_id: str) -> Path:
    return Path(get_settings().upload_storage_dir) / tenant_id / document_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_unsupported_file_type(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("image.png", b"fake png data", "image/png")},
    )
    # The type is rejected at registration, before anything is stored or enqueued.
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_registers_uploaded_and_persists_file(client: AsyncClient) -> None:
    """An upload streams the bytes to disk and records the document as `uploaded`,
    ready for the worker to pick up — it is not processed in the request."""
    token, _, tenant_id = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("faq.md", b"# FAQ\n\nWe are open 9-5.", "text/markdown")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "uploaded"
    doc_id = body["id"]

    # The raw file is on disk at <dir>/<tenant_id>/<document_id> for the worker to read.
    assert _stored_path(tenant_id, doc_id).is_file()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_enqueues_ingestion_job(client: AsyncClient) -> None:
    """The web request hands the heavy work to the queue: only the document id
    (not the file bytes) is enqueued."""
    from unittest.mock import AsyncMock

    from src.drivers.api.dependencies import get_job_pool
    from src.drivers.jobs.queue import PROCESS_DOCUMENT
    from src.main import app

    pool = AsyncMock()
    app.dependency_overrides[get_job_pool] = lambda: pool  # capture what gets enqueued

    token, _, tenant_id = await register_and_token(client)
    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("faq.md", b"# FAQ\n\nopen 9-5", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    pool.enqueue_job.assert_awaited_once()
    name, *job_args = pool.enqueue_job.await_args.args
    assert name == PROCESS_DOCUMENT
    assert job_args == [tenant_id, doc_id, "faq.md"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_ingestion_persists_as_failed_document(client: AsyncClient) -> None:
    """A document that fails ingestion is recorded as FAILED, not lost.

    An empty file parses to zero chunks, so the worker's ingestion job fails before
    embedding (no API key needed) and records the failure on the document.
    """
    token, _, tenant_id = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("empty.md", b"", "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # Run the worker's job directly (the queue is mocked under tests).
    await ingest_document(tenant_id=UUID(tenant_id), document_id=UUID(doc_id), filename="empty.md")

    resp = await client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) == 1
    assert docs[0]["status"] == "failed"
    assert docs[0]["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_then_delete_removes_document_and_file(client: AsyncClient) -> None:
    token, _, tenant_id = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    md_content = b"# FAQ\n\nWe are open 9-5 Sunday to Thursday.\n\nWe accept walk-ins."
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("faq.md", md_content, "text/markdown")},
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]
    stored = _stored_path(tenant_id, doc_id)
    assert stored.is_file()

    # Delete removes both the document row and its stored file.
    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 204
    assert not stored.exists()

    resp = await client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []
