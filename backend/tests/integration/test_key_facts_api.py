"""Integration tests for key facts API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_empty(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/key-facts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/key-facts")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readiness_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint_v2(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
