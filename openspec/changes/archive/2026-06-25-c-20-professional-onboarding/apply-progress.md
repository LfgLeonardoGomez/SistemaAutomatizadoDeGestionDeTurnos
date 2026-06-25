# Apply Progress: C-20-professional-onboarding

## Status: ALL TASKS COMPLETE

## Phase 1: Foundation — Model & Migration (C-20a)

- [x] 1.1 Model: `email` changed to `Mapped[str]` NOT NULL
- [x] 1.2 Alembic migration: `profesional_email_not_null`

## Phase 2: Admin Creation Endpoint (C-20b)

- [x] 2.1 `ProfesionalCreateRequest` + `ProfesionalCreateResponse` schemas
- [x] 2.2 `generate_telegram_secret_token()` added to `auth_service.py`
- [x] 2.3 `create_profesional()` in `super_admin_service.py` with defaults + IntegrityError→409
- [x] 2.4 `POST /admin/profesionales` endpoint (201, super-admin only)
- [x] 2.5 `ProfesionalAdminResponse.email`: `str | None` → `str`

## Phase 3: Integration Setup & Cleanup (C-20c)

- [x] 3.1 `ProfesionalIntegracionesUpdate` + `ProfesionalIntegracionesResponse` schemas
- [x] 3.2 `PUT /profesional/integraciones` + `GET /profesional/integraciones` endpoints
- [x] 3.3 `require_https` dependency in `dependencies.py`
- [x] 3.4 Removed `/auth/register` route + imports from `auth.py`
- [x] 3.5 Removed `ProfesionalRegisterRequest` from `schemas/auth.py`

## Additional Cleanup (C-20c)

- Removed `register_profesional()` from `auth_service.py` (was deprecated in C-20b)
- Removed `ProfesionalRegisterRequest` import from `auth_service.py`
- Removed unused `HTTPException`/`status` imports from `auth_service.py`
- Removed unused `Field` import from `schemas/auth.py`
- Removed `TestRegister` class from `tests/test_auth_integration.py` (route no longer exists)

## Phase 4: Verification

- [ ] 4.1-4.4 Deferred — tests deferred per user directive until v2.0 backend work is finished.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/profesional.py` | Modified | `email` → NOT NULL (C-20a) |
| `backend/alembic/versions/xxxx_profesional_email_not_null.py` | Created | Migration (C-20a) |
| `backend/app/schemas/profesional.py` | Modified | Added Create + Integraciones schemas (C-20b, C-20c) |
| `backend/app/services/auth_service.py` | Modified | Added `generate_telegram_secret_token`; removed `register_profesional` (C-20b, C-20c) |
| `backend/app/services/super_admin_service.py` | Modified | Added `create_profesional()` (C-20b) |
| `backend/app/routers/admin.py` | Modified | Added `POST /admin/profesionales` (C-20b) |
| `backend/app/schemas/super_admin.py` | Modified | `email` type updated (C-20b) |
| `backend/app/dependencies.py` | Modified | Added `require_https` dependency (C-20c) |
| `backend/app/routers/profesional.py` | Modified | Added PUT/GET `/integraciones` (C-20c) |
| `backend/app/routers/auth.py` | Modified | Removed `/auth/register` route (C-20c) |
| `backend/app/schemas/auth.py` | Modified | Removed `ProfesionalRegisterRequest` (C-20c) |
| `backend/tests/test_auth_integration.py` | Modified | Removed `TestRegister` class (C-20c) |
