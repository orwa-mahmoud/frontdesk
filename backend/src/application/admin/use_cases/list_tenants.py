"""ListTenantsForAdmin — cross-tenant listing for the platform admin."""

from __future__ import annotations

from src.application.admin.dtos import AdminTenantDTO
from src.application.shared.unit_of_work import UnitOfWork


class ListTenantsForAdmin:
    """Returns every tenant with its owner email and basic usage counts."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[AdminTenantDTO]:
        tenants = await self._uow.tenants.list_all()
        # Owner email + member count for every tenant in one query, instead of a
        # per-tenant memberships lookup plus a per-tenant owner lookup.
        members = await self._uow.user_tenants.summarize_members_by_tenant()
        rows: list[AdminTenantDTO] = []
        for tenant in tenants:
            summary = members.get(tenant.id)
            # The document count stays per-tenant: `documents` is RLS-protected, so a
            # single global GROUP BY would return zero rows under a non-superuser role
            # (fail-closed). Re-scope and count within each tenant.
            await self._uow.set_tenant_scope(tenant.id)
            doc_count = await self._uow.documents.count_for_tenant(tenant.id)
            rows.append(
                AdminTenantDTO(
                    id=tenant.id,
                    name=tenant.name,
                    slug=tenant.slug,
                    status=tenant.status.value,
                    owner_email=summary.owner_email if summary else None,
                    user_count=summary.user_count if summary else 0,
                    document_count=doc_count,
                )
            )
        return rows
