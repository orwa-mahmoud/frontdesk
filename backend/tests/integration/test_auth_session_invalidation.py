"""Integration tests: changing a password invalidates previously-issued tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.infrastructure.persistence.postgres.database import async_session_factory
from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_issued_before_password_change_is_rejected(client: AsyncClient) -> None:
    token, user_id, _ = await register_and_token(client)

    # The token is valid now.
    ok = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    # Simulate a later password change by pushing password_changed_at past the
    # token's iat (deterministic — no sleeping on wall-clock seconds).
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        user = await uow.users.get_by_id(UUID(user_id))
        assert user is not None
        user.password_changed_at = datetime.now(UTC) + timedelta(seconds=60)
        await uow.users.save(user)
        await uow.commit()

    # The old token is now rejected everywhere, including on /refresh.
    stale = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert stale.status_code == 401
    stale_refresh = await client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert stale_refresh.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password_keeps_current_session_and_rotates_credentials(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "supersecure123", "new_password": "brandnewpass456"},
    )
    assert resp.status_code == 204
    # A fresh cookie is issued so the caller stays signed in.
    assert resp.cookies.get("sight_token")

    # The new cookie (auto-stored by the client) authorizes requests without the
    # old bearer token — the current session survives the password change.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200

    # Old password no longer works; the new one does.
    email = me.json()["email"]
    old_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecure123"})
    assert old_login.status_code == 401
    new_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "brandnewpass456"})
    assert new_login.status_code == 200
