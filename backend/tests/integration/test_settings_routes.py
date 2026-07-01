"""Integration tests for the settings routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.asyncio
async def test_get_settings(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "llm_provider" in body
    assert "bot_name" in body


@pytest.mark.asyncio
async def test_update_llm(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "gpt-4o", "max_tokens": 2048, "temperature": 0.5},
    )
    assert resp.status_code == 200
    assert resp.json()["llm_model"] == "gpt-4o"
    assert resp.json()["llm_max_tokens"] == 2048


@pytest.mark.asyncio
async def test_update_llm_invalidates_cached_client(client: AsyncClient) -> None:
    """Updating LLM config must drop the cached client so the change takes effect."""
    from uuid import UUID

    from src.ai.gateway import _get_llm_factory
    from src.domain.tenant_config.entities import TenantConfig

    token, _, tenant_id = await register_and_token(client)

    # Prime the per-tenant client cache as a live chat would.
    factory = _get_llm_factory()
    cfg = TenantConfig.create_default(tenant_id=UUID(tenant_id))
    cfg.llm_api_key = "sk-old-key-12345678"
    factory.get_or_build(UUID(tenant_id), cfg)
    assert tenant_id in factory._cache

    resp = await client.put(
        "/api/v1/settings/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "gpt-4o", "max_tokens": 2048},
    )
    assert resp.status_code == 200
    # The stale client was evicted; the next chat rebuilds with the new config.
    assert tenant_id not in factory._cache


@pytest.mark.asyncio
async def test_update_embedding(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/embedding",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "text-embedding-3-small", "dimensions": 512},
    )
    assert resp.status_code == 200
    assert resp.json()["embedding_model"] == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_update_embedding_rejects_unsupported_model(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/embedding",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "voyage-3"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_embedding_blocked_when_documents_exist(client: AsyncClient) -> None:
    """Switching the embedding model after ingestion would orphan existing vectors."""
    from uuid import UUID

    from src.application.shared.unit_of_work import UnitOfWork
    from src.domain.documents.entities import Chunk, Document
    from src.domain.documents.value_objects import DocumentMimeType
    from src.infrastructure.persistence.postgres.database import async_session_factory

    token, _, tenant_id = await register_and_token(client)

    # Seed one ingested chunk for this tenant, embedded under the current model.
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        doc = Document.upload(
            tenant_id=UUID(tenant_id),
            uploaded_by_user_id=None,
            filename="policy.txt",
            mime_type=DocumentMimeType.PLAIN,
            size_bytes=10,
        )
        await uow.documents.save(doc)
        await uow.flush()
        uow.chunks.save_many(
            [
                Chunk.create(
                    document_id=doc.id,
                    tenant_id=UUID(tenant_id),
                    chunk_index=0,
                    content="hello",
                    embedding=[0.0] * 1536,
                )
            ]
        )
        await uow.commit()

    # Changing the model is now blocked; the api key can still be rotated.
    blocked = await client.put(
        "/api/v1/settings/embedding",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "text-embedding-3-small"},
    )
    assert blocked.status_code == 400

    rotate = await client.put(
        "/api/v1/settings/embedding",
        headers={"Authorization": f"Bearer {token}"},
        json={"api_key": "sk-rotated-key"},
    )
    assert rotate.status_code == 200


@pytest.mark.asyncio
async def test_update_whatsapp(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/whatsapp",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone_number_id": "12345", "access_token": "EAA-secret", "verify_token": "vt-secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["whatsapp_phone_number_id"] == "12345"


@pytest.mark.asyncio
async def test_update_telegram(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/telegram",
        headers={"Authorization": f"Bearer {token}"},
        json={"bot_token": "123:ABC", "webhook_secret": "ws-secret"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_bot(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/bot",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "FD Bot", "welcome_message": "Hi!", "language": "en"},
    )
    assert resp.status_code == 200
    assert resp.json()["bot_name"] == "FD Bot"


@pytest.mark.asyncio
async def test_settings_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 401
