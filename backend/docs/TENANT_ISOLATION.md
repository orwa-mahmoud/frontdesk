# Tenant Isolation

Frontdesk is multi-tenant: every tenant's data (conversations, documents,
contacts, questions, key facts, usage, invitations, config) must be invisible to
every other tenant. This document describes how isolation is enforced today and
the roadmap to defense-in-depth.

## How isolation works today (application layer)

1. **Tenant is never trusted from the client.** It is resolved from the
   authenticated context — the JWT `sub` → user → `user_tenants` link — or, for
   channel webhooks, from the URL path. See `drivers/api/dependencies.py`.
2. **Every repository query filters by `tenant_id`.** Reads and writes are
   scoped in the SQL `WHERE` clause (e.g. `conversation_repo`, `document_repo`,
   `invitation_repo`).
3. **The only cross-tenant view is the platform-admin console** (`/api/v1/admin`),
   guarded by `require_platform_admin`. Regular tenant users get 403.
4. **Owner vs. staff** within a tenant: owner-only routes (settings mutations,
   invitations, tenant management) are guarded by `require_owner`.

Regression coverage: `tests/integration/test_tenant_isolation.py` asserts a
tenant cannot read or act on another tenant's data. Treat a failure there as a
release blocker.

## The gap

App-layer enforcement is correct but relies on every present and future query
remembering to filter by `tenant_id`. A single missed filter is a cross-tenant
leak with nothing to catch it at the database boundary.

## Roadmap: PostgreSQL Row-Level Security (RLS)

RLS makes the database itself refuse cross-tenant rows, as a backstop beneath the
app-layer filters.

**Prerequisite — stop connecting as a superuser.** RLS policies are *ignored*
for a Postgres role with `BYPASSRLS` (which includes superusers like the default
`postgres`). The app must connect as a dedicated non-superuser role
(e.g. `frontdesk_app`) with only the DML privileges it needs. This is a
deployment change (new role + grants + `DATABASE_URL`), so it is intentionally
not enabled by default.

**Sketch once the role exists:**

1. Create the role and grant table privileges (no `BYPASSRLS`).
2. For each tenant-scoped table: `ENABLE ROW LEVEL SECURITY` and add a policy
   `USING (tenant_id = current_setting('app.current_tenant')::uuid)`.
3. Per request/transaction, after resolving the tenant, run
   `SET LOCAL app.current_tenant = '<uuid>'`.
4. Identity tables (`users`, `tenants`, `user_tenants`) stay outside RLS — they
   are queried *before* a tenant is known (login, registration).
5. A future platform-admin DB path can use a `BYPASSRLS` role or a wildcard
   session flag — the single, auditable exception.

Until then, the app-layer filters + the isolation regression suite are the
guarantee.
