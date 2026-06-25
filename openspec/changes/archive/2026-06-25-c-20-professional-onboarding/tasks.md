# Tasks: Professional Onboarding (C-20)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~280-330 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (C-20a + C-20b + C-20c) |
| Delivery strategy | single-pr-default |
| Chain strategy | none |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: none
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| C-20a | Model + migration (email NOT NULL) | PR 1 (single) | Foundation; no runtime deps |
| C-20b | Admin creation endpoint + credential generation | PR 1 (single) | Depends on C-20a model change |
| C-20c | Integration setup endpoint + remove `/auth/register` | PR 1 (single) | Depends on C-20b schemas |

## Phase 1: Foundation — Model & Migration (C-20a)

- [x] 1.1 In `backend/app/models/profesional.py`, change `email` from `Mapped[Optional[str]]` with `nullable=True` to `Mapped[str]` with `nullable=False`. Remove `Optional` import if unused.
- [x] 1.2 Create Alembic migration `backend/alembic/versions/xxxx_profesional_email_not_null.py` that alters `profesional.email` to `nullable=False`. Verify upgrade and downgrade round-trip.

## Phase 2: Admin Creation Endpoint (C-20b)

- [x] 2.1 In `backend/app/schemas/profesional.py`, add `ProfesionalCreateRequest` (nombre, email: EmailStr, password min_length=8, especialidad) and `ProfesionalCreateResponse` (profile fields + plaintext api_key + telegram_secret_token).
- [x] 2.2 In `backend/app/services/auth_service.py`, add `generate_telegram_secret_token() -> str` using `secrets.token_urlsafe(32)`. `register_profesional()` retained (marked deprecated) — removal deferred to C-20c to keep `/auth/register` functional.
- [x] 2.3 In `backend/app/services/super_admin_service.py`, add `create_profesional(db, data) -> tuple[Profesional, str, str]`. Apply defaults (duracion_turno=30, horario_inicio="09:00", horario_fin="17:00", dias_atencion=Lunes-Viernes), hash password, generate api_key + telegram_secret_token, handle IntegrityError → 409.
- [x] 2.4 In `backend/app/routers/admin.py`, add `POST /admin/profesionales` protected by `CurrentSuperAdminDep`. Return 201 with `ProfesionalCreateResponse` including plaintext secrets.
- [x] 2.5 In `backend/app/schemas/super_admin.py`, update `ProfesionalAdminResponse.email` from `str | None` to `str` (now NOT NULL).

## Phase 3: Integration Setup & Cleanup (C-20c)

- [x] 3.1 In `backend/app/schemas/profesional.py`, add `ProfesionalIntegracionesUpdate` (optional telegram_bot_token + google_refresh_token with empty-string validator) and `ProfesionalIntegracionesResponse` (has_telegram: bool, has_google: bool).
- [x] 3.2 In `backend/app/routers/profesional.py`, add `PUT /profesional/integraciones` (partial update, skip None fields, reject empty strings) and `GET /profesional/integraciones` (return boolean flags, no secrets).
- [x] 3.3 In `backend/app/dependencies.py`, add `require_https` dependency that checks `X-Forwarded-Proto` header when `settings.env == "production"`.
- [x] 3.4 In `backend/app/routers/auth.py`, remove `/auth/register` route, remove `ProfesionalRegisterRequest` and `register_profesional` imports.
- [x] 3.5 In `backend/app/schemas/auth.py`, remove `ProfesionalRegisterRequest` class.

## Phase 4: Verification

- [ ] 4.1 Run `alembic upgrade head` and verify migration applies cleanly.
- [ ] 4.2 Start backend and verify `POST /admin/profesionales` returns 201 with credentials, 409 on duplicate email, 422 on weak password, 403 for non-admin.
- [ ] 4.3 Verify `PUT /profesional/integraciones` updates tokens and `GET /profesional/integraciones` returns masked status.
- [ ] 4.4 Verify `/auth/register` returns 404.
