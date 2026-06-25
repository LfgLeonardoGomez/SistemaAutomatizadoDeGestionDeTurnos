# Proposal: Super-admin role for SaaS operation

## Intent

Introduce a SaaS operator role (`SUPER_ADMIN`) that is distinct from `Profesional`. The super-admin must manage professionals (list, activate/deactivate) and view global metrics without being mistaken for a professional in normal flows.

## Scope

### In Scope
- New `SuperAdmin` model/table separate from `Profesional`.
- Super-admin email/password login returning a JWT with a distinct `role` claim.
- `require_super_admin` dependency to protect admin endpoints.
- New `/admin` router with endpoints for professional management and global metrics.
- Alembic migration and `.env.example` updates.

### Out of Scope
- Web UI or CLI panel (backend endpoints only).
- Super-admin password reset / self-service account management.
- Role-based granularity beyond `SUPER_ADMIN`.

## Capabilities

### New Capabilities
- `super-admin-auth`: `SuperAdmin` model, login endpoint, JWT claim `role: super_admin`, `require_super_admin` dependency.
- `super-admin-professional-management`: list, get, activate, and deactivate professionals under `/admin/profesionales`.
- `super-admin-global-metrics`: aggregate metrics across all professionals under `/admin/metricas`.

### Modified Capabilities
- None. The `Profesional` model and existing auth capabilities are not changed.

## Approach

Use **Option B (separate `SuperAdmin` table)**. Adding a `role` column to `Profesional` would force admin-specific nulls in professional fields and risk leaking super-admins into professional-scoped queries. A separate table keeps scoping by `profesional_id` untouched and makes the role boundary explicit.

Use **email/password + JWT with `role` claim**. The project already uses JWT for professionals, so we reuse the same library and settings while adding a `role` claim (`super_admin`) that `require_super_admin` checks. A strong API key via env var is simpler but offers no audit trail or multi-admin path; JWT login is only slightly more work and aligns with C-15.

A single super-admin is bootstrapped from env vars (`SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD_HASH`) during seed/migration.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/super_admin.py` | New | SQLAlchemy model for super-admins. |
| `backend/app/schemas/super_admin.py` | New | Pydantic login and response schemas. |
| `backend/app/services/super_admin_service.py` | New | Auth and admin CRUD logic. |
| `backend/app/dependencies.py` | Modified | Add `require_super_admin`. |
| `backend/app/routers/admin.py` | New | `/admin` endpoints. |
| `backend/app/main.py` | Modified | Include admin router. |
| `backend/alembic/versions/` | New | Migration for `super_admin` table. |
| `.env.example` | Modified | Super-admin credentials vars. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TDD deferral from C-14–C-18 causes regressions in auth/scoping. | Med | Schedule test catch-up before C-21; add targeted tests for admin isolation. |
| Super-admin JWT leak grants broad access. | Low | Short token TTL, HTTPS in prod, store secret in env/secret manager. |
| Admin endpoints accidentally scoping by `profesional_id`. | Med | Code review all admin queries; they must aggregate or filter by ID explicitly. |

## Rollback Plan

1. Revert Alembic migration to drop `super_admin` table.
2. Remove `admin` router from `main.py`.
3. Revert `dependencies.py` changes.

## Dependencies

- C-16 `tenant-backend-scoping` must be archived.
- C-17 `telegram-multi-bot` and C-18 `google-multi-calendar` should be archived before merging this change.

## Success Criteria

- [ ] `POST /admin/auth/login` returns a JWT for valid super-admin credentials.
- [ ] `require_super_admin` rejects requests from professional JWTs or missing/invalid tokens.
- [ ] Admin endpoints list, retrieve, activate, and deactivate professionals correctly.
- [ ] `GET /admin/metricas` returns aggregate counts across all professionals.
- [ ] Super-admin records never appear in `/profesional/*` flows.
