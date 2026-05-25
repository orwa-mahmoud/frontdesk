"""Unit tests for request ID middleware."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_response_has_request_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_custom_request_id_echoed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Request-ID": "custom-123"})
    assert resp.headers.get("x-request-id") == "custom-123"
