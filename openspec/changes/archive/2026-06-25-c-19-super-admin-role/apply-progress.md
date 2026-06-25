# Apply Progress: C-19 Super-admin Role

## Slice: C-19a (Foundation + Bootstrap) — COMPLETED

### Completed Tasks

- [x] 1.1 Create `backend/app/models/super_admin.py` — `SuperAdmin` model with `id`, `email` (unique), `password_hash`, `creado_en`. No FK to `profesional`.
- [x] 1.2 Export `SuperAdmin` in `backend/app/models/__init__.py` and add `super_admin` import to `backend/alembic/env.py`.
- [x] 1.3 Add `super_admin_email: str = ""` and `super_admin_password_hash: str = ""` to `backend/app/config.py` `Settings`.
- [x] 1.4 Generate Alembic migration `create_super_admin_table` — creates `super_admin` table with unique constraint on `email`. Chain after `f3c8a2b91c4e`.
- [x] 6.1 Add `seed_super_admin(session, settings)` to `backend/app/seed.py` — creates one SuperAdmin from `SUPER_ADMIN_EMAIL` + `SUPER_ADMIN_PASSWORD_HASH` if table is empty. Idempotent.
- [x] 6.2 Wire admin router in `backend/app/main.py` — call `seed_super_admin` in `lifespan` alongside existing `seed_profesional`.
- [x] 6.3 Update `.env.example` — add `SUPER_ADMIN_EMAIL=` and `SUPER_ADMIN_PASSWORD_HASH=` entries.

### Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/super_admin.py` | Created | SuperAdmin SQLAlchemy model (id, email unique, password_hash, creado_en). |
| `backend/app/models/__init__.py` | Modified | Exported SuperAdmin. |
| `backend/alembic/env.py` | Modified | Added super_admin import for autogenerate. |
| `backend/app/config.py` | Modified | Added super_admin_email and super_admin_password_hash settings. |
| `backend/alembic/versions/a1b2c3d4e5f6_create_super_admin_table.py` | Created | Migration: creates super_admin table, chains after f3c8a2b91c4e. |
| `backend/app/seed.py` | Modified | Added seed_super_admin function (idempotent, env-driven). |
| `backend/app/main.py` | Modified | Added seed_super_admin call in lifespan. |
| `.env.example` | Modified | Added SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD_HASH entries. |

---

## Slice: C-19b (Auth Infrastructure) — COMPLETED

### Completed Tasks

- [x] 2.1 Add `create_super_admin_access_token(id, email, settings)` to `backend/app/services/auth_service.py` — encodes `role: "super_admin"` claim in JWT payload alongside `sub`, `email`, `iat`, `exp`.
- [x] 2.2 Add `admin_oauth2_scheme` (OAuth2PasswordBearer with `tokenUrl="/admin/auth/login"`) and `require_super_admin` dependency to `backend/app/dependencies.py` — returns 401 on missing/invalid token, 403 on non-admin role. Add `CurrentSuperAdminDep` type alias.

### Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/auth_service.py` | Modified | Added `create_super_admin_access_token` — mirrors `create_access_token` but includes `role: "super_admin"` claim. |
| `backend/app/dependencies.py` | Modified | Added `admin_oauth2_scheme`, `require_super_admin` dependency, `CurrentSuperAdminDep` type alias, and `SuperAdmin` import. |

---

## Slice: C-19c (Schemas + Service + Router + Integration) — COMPLETED

### Completed Tasks

- [x] 3.1 Create `backend/app/schemas/super_admin.py` with `SuperAdminLoginRequest`, `ProfesionalAdminResponse`, `GlobalMetricsResponse`.
- [x] 4.1 Create `backend/app/services/super_admin_service.py` with `authenticate_super_admin(db, email, password) -> SuperAdmin | None`.
- [x] 4.2 Add professional management functions: `list_profesionales`, `get_profesional`, `activate_profesional`, `deactivate_profesional`.
- [x] 4.3 Add `compute_global_metrics(db) -> GlobalMetricsResponse` — aggregate counts and rates.
- [x] 5.1 Create `backend/app/routers/admin.py` with `POST /admin/auth/login`.
- [x] 5.2 Add `GET /admin/profesionales` and `GET /admin/profesionales/{id}` — 404 on not-found.
- [x] 5.3 Add `PUT /admin/profesionales/{id}/activar` and `PUT /admin/profesionales/{id}/desactivar` — idempotent.
- [x] 5.4 Add `GET /admin/metricas` — returns `GlobalMetricsResponse`.
- [x] 6.2 Wire admin router in `backend/app/main.py` — replaced TODO with `app.include_router(admin_router)`.

### Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/schemas/super_admin.py` | Created | Login request, professional admin response, and global metrics response schemas. |
| `backend/app/services/super_admin_service.py` | Created | Auth, professional CRUD (list/get/activate/deactivate), and metrics aggregation. |
| `backend/app/routers/admin.py` | Created | `/admin` router with login, professional management, and metrics endpoints. |
| `backend/app/main.py` | Modified | Replaced TODO with `app.include_router(admin_router)`. |

---

## All Tasks Complete

C-19 is fully implemented across three slices (C-19a, C-19b, C-19c).

### Deviations from Design

None — implementation matches design across all slices.

### Notes

- Tests are deferred per project directive (v2.0 backend work must finish first).
- Single PR strategy: all v2.0 work (C-19a through C-22) stays in current branch.
- `ProfesionalAdminResponse.email` is `str | None` because `Profesional.email` is nullable (added in C-14 for auth; some professionals may not have email set).
