"""ListUsersForAdmin — cross-tenant user listing for the platform admin."""

from __future__ import annotations

from src.application.admin.dtos import AdminUserDTO
from src.application.shared.unit_of_work import UnitOfWork


class ListUsersForAdmin:
    """Returns every user with their (first) tenant + role context."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[AdminUserDTO]:
        users = await self._uow.users.list_all()
        # Each user's primary tenant + role in one query, instead of a per-user
        # membership lookup plus a per-user tenant lookup.
        memberships = await self._uow.user_tenants.primary_membership_by_user()
        rows: list[AdminUserDTO] = []
        for user in users:
            membership = memberships.get(user.id)
            rows.append(
                AdminUserDTO(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_platform_admin=user.is_platform_admin,
                    tenant_id=membership.tenant_id if membership else None,
                    tenant_name=membership.tenant_name if membership else None,
                    role=membership.role.value if membership else None,
                )
            )
        return rows
