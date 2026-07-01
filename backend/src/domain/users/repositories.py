"""User + UserTenant repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.domain.users.entities import User, UserTenant
from src.domain.users.value_objects import UserTenantRole


@dataclass(frozen=True, kw_only=True)
class TenantMemberSummary:
    """Per-tenant membership rollup for the admin tenants list (one row per tenant)."""

    owner_email: str | None
    user_count: int


@dataclass(frozen=True, kw_only=True)
class PrimaryMembership:
    """A user's first tenant membership, for the admin users list (one per user)."""

    tenant_id: UUID
    tenant_name: str
    role: UserTenantRole


class UserRepository(Protocol):
    async def save(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def list_all(self) -> list[User]: ...


class UserTenantRepository(Protocol):
    async def save(self, link: UserTenant) -> None: ...

    async def list_for_user(self, user_id: UUID) -> list[UserTenant]: ...

    async def list_for_tenant(self, tenant_id: UUID) -> list[UserTenant]: ...

    async def get(self, user_id: UUID, tenant_id: UUID) -> UserTenant | None: ...

    async def summarize_members_by_tenant(self) -> dict[UUID, TenantMemberSummary]:
        """One-query rollup of member count + owner email per tenant, for the admin
        tenants list (avoids a per-tenant membership + owner lookup)."""
        ...

    async def primary_membership_by_user(self) -> dict[UUID, PrimaryMembership]:
        """Each user's first tenant membership (tenant id + name + role) in one
        query, for the admin users list (avoids a per-user membership + tenant
        lookup)."""
        ...
