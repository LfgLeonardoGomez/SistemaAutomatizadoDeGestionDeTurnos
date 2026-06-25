# Tasks: Super-Admin Role (C-19)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~415 (10 files, 5 new + 5 modified) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (user directive) |
| Delivery strategy | single-pr |
| Chain strategy | none |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: none
400-line budget risk: Medium

## Phase 1: Foundation (Model + Config + Migration)

- [ ] 1.1 Create `backend/app/models/super_admin.py` — `SuperAdmin` model with `id`, `email` (unique), `password_hash`, `creado_en`. No FK to `profesional`.
- [ ] 1.2 Export `SuperAdmin` in `backend/app/models/__init__.py` and add `super_admin` import to `backend/alembic/env.py`.
- [ ] 1.3 Add `super_admin_email: str = ""` and `super_admin_password_hash: str = ""` to `backend/app/config.py` `Settings`.
- [ ] 1.4 Generate Alembic migration `create_super_admin_table` — creates `super_admin` table with unique constraint on `email`. Chain after `f3c8a2b91c4e`.

## Phase 2: Auth Infrastructure

- [ ] 2.1 Add `create_super_admin_access_token(id, email, settings)` to `backend/app/services/auth_service.py` — encodes `role: "super_admin"` claim in JWT payload alongside `sub`, `email`, `iat`, `exp`.
- [ ] 2.2 Add `admin_oauth2_scheme` (OAuth2PasswordBearer with `tokenUrl="/admin/auth/login"`) and `require_super_admin` dependency to `backend/app/dependencies.py` — returns 401 on missing/invalid token, 403 on non-admin role. Add `CurrentSuperAdminDep` type alias.

## Phase 3: Schemas

- [ ] 3.1 Create `backend/app/schemas/super_admin.py` with: `SuperAdminLoginRequest` (email, password), `ProfesionalAdminResponse` (id, nombre, especialidad, email, is_active, creado_en), `GlobalMetricsResponse` (all 11 metric fields per spec).

## Phase 4: Service Layer

- [ ] 4.1 Create `backend/app/services/super_admin_service.py` with `authenticate_super_admin(db, email, password) -> SuperAdmin | None` — queries `super_admin` table, uses `verify_password` from `auth_service`.
- [ ] 4.2 Add professional management functions to `super_admin_service.py`: `list_profesionales(db, skip, limit)`, `get_profesional(db, id)`, `activate_profesional(db, id)`, `deactivate_profesional(db, id)`. Deactivate sets `is_active=False` without deleting related data.
- [ ] 4.3 Add `compute_global_metrics(db) -> GlobalMetricsResponse` to `super_admin_service.py` — aggregate counts for profesionales, turnos (total, hoy, confirmados/cancelados 30d), pacientes, and confirmation/cancellation rates. Return zeros when denominator is zero.

## Phase 5: Router

- [ ] 5.1 Create `backend/app/routers/admin.py` with `POST /admin/auth/login` — authenticates super-admin, returns `TokenResponse` using `create_super_admin_access_token`.
- [ ] 5.2 Add `GET /admin/profesionales` and `GET /admin/profesionales/{id}` to admin router — protected by `require_super_admin`, return `ProfesionalAdminResponse` list/single. 404 on not-found.
- [ ] 5.3 Add `PUT /admin/profesionales/{id}/activar` and `PUT /admin/profesionales/{id}/desactivar` to admin router — idempotent activation/deactivation.
- [ ] 5.4 Add `GET /admin/metricas` to admin router — returns `GlobalMetricsResponse`.

## Phase 6: Integration + Bootstrap

- [ ] 6.1 Add `seed_super_admin(session, settings)` to `backend/app/seed.py` — creates one SuperAdmin from `SUPER_ADMIN_EMAIL` + `SUPER_ADMIN_PASSWORD_HASH` if table is empty. Idempotent.
- [ ] 6.2 Wire admin router in `backend/app/main.py` — `app.include_router(admin_router)` and call `seed_super_admin` in `lifespan` alongside existing `seed_profesional`.
- [ ] 6.3 Update `.env.example` — add `SUPER_ADMIN_EMAIL=` and `SUPER_ADMIN_PASSWORD_HASH=` entries.
