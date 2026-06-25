# Proposal: Professional Onboarding

## Intent

Replace self-service professional registration with an invitation-only, super-admin-created onboarding flow. The professional receives credentials once and configures Telegram and Google Calendar integrations afterwards via an authenticated endpoint.

## Scope

### In Scope
- Admin-only creation endpoint `POST /admin/profesionales`.
- Auto-generation of `api_key` and `telegram_secret_token` at creation.
- Removal of public `/auth/register` self-service registration.
- `PUT /profesional/integraciones` for `telegram_bot_token` and `google_refresh_token`.
- Masking secrets in all read responses.

### Out of Scope
- Email verification, password reset, OAuth authorization-code flow.
- Web UI or multi-step wizard.
- Separate "regenerate telegram secret" endpoint (deferred).

## Capabilities

### New Capabilities
- `professional-onboarding`: super-admin-only professional creation with initial credentials.
- `professional-integration-setup`: authenticated update and masked read of integration tokens.

### Modified Capabilities
- `professional-jwt-auth`: remove self-service `/auth/register`; keep login and API-key regeneration.
- `super-admin-professional-management`: add `POST /admin/profesionales` to create professionals.

## Approach

Add `POST /admin/profesionales` protected by `CurrentSuperAdminDep`. The service creates a `Profesional` with `is_active=True`, hashes the password, generates `api_key` and `telegram_secret_token`, and returns the profile plus the two plaintext secrets exactly once. Validate email uniqueness via DB constraint / 409 response.

Remove the public `/auth/register` route and `ProfesionalRegisterRequest` schema from `auth.py`; update any tests or docs that reference it.

Add `PUT /profesional/integraciones` to `routers/profesional.py`, allowing the authenticated professional to update `telegram_bot_token` and/or `google_refresh_token`. Return a masked status object that never includes the plaintext tokens. Existing `PUT /profesional/configuracion` remains the place for schedule/duration settings.

Multi-tenancy continues to be scoped by `profesional_id`; no `tenant_id` is introduced.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/routers/admin.py` | Modified | Add `POST /admin/profesionales`. |
| `backend/app/routers/auth.py` | Modified | Remove `/auth/register`; keep login/api-key. |
| `backend/app/routers/profesional.py` | Modified | Add `/profesional/integraciones` PUT/GET. |
| `backend/app/services/auth_service.py` | Modified | Move/reuse credential generation for admin flow. |
| `backend/app/services/super_admin_service.py` | Modified | Add create-profesional service. |
| `backend/app/schemas/auth.py` | Modified | Remove register request schema. |
| `backend/app/schemas/profesional.py` | Modified | Add integration request/response schemas. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TDD deferral lets regressions slip | High | Document deferral; schedule catch-up tests before v2.0 PR. |
| Removing `/auth/register` breaks existing tests/clients | Med | Update tests and API consumers in the same PR. |
| Plaintext credentials returned once may be leaked | Med | Return only on creation; never log or include in GET responses. |

## Rollback Plan

1. Revert changes to `admin.py`, `auth.py`, `profesional.py`, related services and schemas.
2. No DB migration rollback is required because all columns already exist from C-14.
3. Re-deploy; restore previous `/auth/register` behavior if needed.

## Dependencies

- C-16 `tenant-backend-scoping`
- C-17 `telegram-multi-bot`
- C-18 `google-multi-calendar`
- C-19 `super-admin-role`

## Success Criteria

- [ ] `POST /admin/profesionales` creates an active professional and returns profile + credentials once.
- [ ] Duplicate email returns 409.
- [ ] `PUT /profesional/integraciones` updates Telegram/Google tokens and returns masked values.
- [ ] `GET /profesional/integraciones` shows status without exposing secrets.
- [ ] `/auth/register` is no longer publicly reachable.
