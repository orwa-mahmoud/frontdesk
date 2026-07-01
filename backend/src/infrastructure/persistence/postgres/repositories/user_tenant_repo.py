"""PostgreSQL UserTenant repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.entities import UserTenant
from src.domain.users.repositories import PrimaryMembership, TenantMemberSummary
from src.domain.users.value_objects import UserTenantRole
from src.infrastructure.persistence.postgres.models.tenant import TenantModel
from src.infrastructure.persistence.postgres.models.user import UserModel
from src.infrastructure.persistence.postgres.models.user_tenant import UserTenantModel


class PostgresUserTenantRepository:
    """Concrete user-tenant join repository — implements `UserTenantRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, link: UserTenant) -> None:
        if link.is_new:
            self._session.add(self._to_model(link))
            link.mark_persisted()
            return
        model = await self._session.get(UserTenantModel, link.id)
        if model is None:
            self._session.add(self._to_model(link))
            return
        model.role = link.role.value

    async def list_for_user(self, user_id: UUID) -> list[UserTenant]:
        stmt = select(UserTenantModel).where(UserTenantModel.user_id == user_id).order_by(UserTenantModel.joined_at)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_for_tenant(self, tenant_id: UUID) -> list[UserTenant]:
        stmt = select(UserTenantModel).where(UserTenantModel.tenant_id == tenant_id).order_by(UserTenantModel.joined_at)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get(self, user_id: UUID, tenant_id: UUID) -> UserTenant | None:
        stmt = select(UserTenantModel).where(
            UserTenantModel.user_id == user_id,
            UserTenantModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def summarize_members_by_tenant(self) -> dict[UUID, TenantMemberSummary]:
        owner = UserTenantRole.OWNER.value
        stmt = (
            select(
                UserTenantModel.tenant_id,
                func.count().label("user_count"),
                func.max(case((UserTenantModel.role == owner, UserModel.email))).label("owner_email"),
            )
            .join(UserModel, UserModel.id == UserTenantModel.user_id)
            .group_by(UserTenantModel.tenant_id)
        )
        result = await self._session.execute(stmt)
        return {
            row.tenant_id: TenantMemberSummary(owner_email=row.owner_email, user_count=int(row.user_count))
            for row in result
        }

    async def primary_membership_by_user(self) -> dict[UUID, PrimaryMembership]:
        # DISTINCT ON (user_id) with the joined_at tiebreaker keeps the user's first
        # membership — the same one list_for_user + links[0] resolved per user.
        stmt = (
            select(
                UserTenantModel.user_id,
                UserTenantModel.tenant_id,
                TenantModel.name.label("tenant_name"),
                UserTenantModel.role,
            )
            .join(TenantModel, TenantModel.id == UserTenantModel.tenant_id)
            .order_by(UserTenantModel.user_id, UserTenantModel.joined_at)
            .distinct(UserTenantModel.user_id)
        )
        result = await self._session.execute(stmt)
        return {
            row.user_id: PrimaryMembership(
                tenant_id=row.tenant_id, tenant_name=row.tenant_name, role=UserTenantRole(row.role)
            )
            for row in result
        }

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(link: UserTenant) -> UserTenantModel:
        return UserTenantModel(
            id=link.id,
            user_id=link.user_id,
            tenant_id=link.tenant_id,
            role=link.role.value,
            joined_at=link.joined_at,
        )

    @staticmethod
    def _to_entity(model: UserTenantModel) -> UserTenant:
        return UserTenant(
            id=model.id,
            user_id=model.user_id,
            tenant_id=model.tenant_id,
            role=UserTenantRole(model.role),
            joined_at=model.joined_at,
        )
