"""Tests for refresh token use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.auth.commands import RegisterOwner
from src.application.auth.use_cases.refresh_token import RefreshTokenUseCase
from src.application.auth.use_cases.register_owner import RegisterOwnerUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthenticationError
from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher
from src.infrastructure.auth.jwt_service import JwtService
from src.infrastructure.persistence.postgres.database import async_session_factory

_H = BcryptPasswordHasher(rounds=4)
_J = JwtService(secret_key="test")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_success(client=None):
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        slug = f"rf-{uuid4().hex[:8]}"
        reg = RegisterOwnerUseCase(uow=uow, password_hasher=_H, jwt_service=_J)
        result = await reg.execute(
            RegisterOwner(
                email=f"{slug}@t.com", password="longpass123", full_name=None, tenant_name="T", tenant_slug=slug
            )
        )
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = RefreshTokenUseCase(uow=uow, jwt_service=_J)
        new_result = await uc.execute(result.user_id)
        assert new_result.access_token
        assert new_result.tenant_id == result.tenant_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_nonexistent_user(client=None):
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = RefreshTokenUseCase(uow=uow, jwt_service=_J)
        with pytest.raises(AuthenticationError):
            await uc.execute(uuid4())
