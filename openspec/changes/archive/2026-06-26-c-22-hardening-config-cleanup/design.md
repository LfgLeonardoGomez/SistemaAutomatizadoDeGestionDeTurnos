# Design: C-22 `hardening-config-cleanup`

## Status

`design`

## Executive Summary

This change completes the v2.0 configuration cleanup by removing dead global environment variables (`TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID`) and moving the Google Calendar target to `Profesional.google_calendar_id`. It also runs a security/scoping audit of all authenticated endpoints before release.

## Technical Approach

1. **Settings cleanup**: remove the three deprecated fields from `Settings` and `.env.example`. Required vars remain validated at startup; the app must boot without them.
2. **Model change**: add `google_calendar_id` to `Profesional` as a nullable string with server default `"primary"`, so existing rows upgrade safely.
3. **API change**: extend the integration update/read schemas and router with `google_calendar_id`, preserving partial-update semantics and empty-string rejection.
4. **Service change**: update `CalendarService` to read `calendarId` from the professional instance instead of `settings.google_calendar_id`, keeping `"primary"` as fallback.
5. **Test cleanup**: drop all monkeypatches for the removed env vars; set `google_calendar_id` on the shared `profesional` fixture.
6. **Security audit**: review every router for authentication dependency and `profesional_id` filtering; add isolation tests where missing.

## File-by-File Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/app/config.py` | Modify | Remove `telegram_bot_token`, `google_calendar_credentials`, `google_calendar_id`. |
| `backend/.env.example` | Modify | Remove the same three variables. |
| `backend/app/models/profesional.py` | Modify | Add `google_calendar_id: Mapped[Optional[str]]` column. |
| `backend/alembic/versions/...c22...` | Create | Add nullable column with server default `"primary"`. |
| `backend/app/schemas/profesional.py` | Modify | Add `google_calendar_id` to `ProfesionalIntegracionesUpdate` and `ProfesionalIntegracionesResponse`. |
| `backend/app/routers/profesional.py` | Modify | Persist `google_calendar_id` on `PUT /profesional/integraciones`; return it on `GET`. |
| `backend/app/services/calendar_service.py` | Modify | Use `profesional.google_calendar_id or "primary"` for `calendarId`. |
| `backend/tests/conftest.py` | Modify | Remove env-var monkeypatches; set `google_calendar_id="primary"` on `profesional` fixture. |
| `backend/tests/test_config.py` | Modify | Drop deprecated env-var setup; assert fields are absent. |
| `backend/tests/test_calendar_service.py` | Modify | Remove `google_calendar_id` kwarg from fixture factory; assert service uses professional value. |
| `backend/tests/test_scheduler*.py` | Modify | Remove `TELEGRAM_BOT_TOKEN` monkeypatches. |
| `backend/tests/test_telegram_service.py` | Modify | Remove `TELEGRAM_BOT_TOKEN` monkeypatch. |
| `backend/tests/test_auth_jwt.py` | Modify | Remove `TELEGRAM_BOT_TOKEN` monkeypatch. |
| `backend/tests/test_profesional.py` | Modify | Add partial-update and empty-string tests for `google_calendar_id`. |
| `backend/tests/test_*.py` (isolation) | Modify/Add | Add cross-professional isolation tests where lists are returned. |

## Data Model / Migration Details

| Table | Column | Type | Default | Nullable |
|-------|--------|------|---------|----------|
| `profesional` | `google_calendar_id` | `VARCHAR(255)` | `'primary'` | Yes |

- **Upgrade**: `ALTER TABLE profesional ADD COLUMN google_calendar_id VARCHAR(255) NULL DEFAULT 'primary';`.
- **Downgrade**: `ALTER TABLE profesional DROP COLUMN google_calendar_id;`.
- Existing professionals receive `"primary"` automatically; new values are set via `PUT /profesional/integraciones`.

## API Contract Details

### `PUT /profesional/integraciones`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `telegram_bot_token` | string | No | Empty string rejected. |
| `google_refresh_token` | string | No | Empty string rejected. |
| `google_calendar_id` | string | No | Empty string rejected. |

Only provided fields are updated. `google_calendar_id` defaults to `"primary"` at the database level when not supplied.

### `GET /profesional/integraciones`

Response fields: `has_telegram`, `has_google`, `google_calendar_id`.

`google_calendar_id` is returned verbatim; tokens and `password_hash` are never exposed.

## Test Strategy

| Layer | What to test | Approach |
|-------|--------------|----------|
| Unit config | Absence of deprecated env vars | `test_config.py` builds `Settings` without them. |
| Migration | Existing rows default to `"primary"` | Alembic offline/online smoke test or migration unit check. |
| API | Partial update and rejection of empty `google_calendar_id` | `test_profesional.py` with authenticated client. |
| Service | `calendarId` from professional, fallback to `"primary"` | Mock Google API in `test_calendar_service.py`. |
| Fixtures | No monkeypatch for removed vars | `conftest.py` only sets `DATABASE_URL` and `SECRET_KEY`. |
| Security | Endpoint isolation | Cross-professional access attempts return 404/403. |

## Security / Scoping Audit Checklist

- [ ] Every `/profesional/*` endpoint depends on `CurrentProfesionalDep` or API-key/Telegram-secret dependency.
- [ ] Every database query in `/profesional/*` filters by the authenticated `profesional_id`.
- [ ] `/admin/*` endpoints use `CurrentSuperAdminDep` and do not expose professional tokens or passwords.
- [ ] `PUT /profesional/integraciones` enforces HTTPS in production via `require_https`.
- [ ] Responses never include `telegram_bot_token`, `google_refresh_token`, or `password_hash`.
- [ ] Missing isolation tests are added for list endpoints (`/profesional/turnos-hoy`, `/pacientes/*`, `/turnos/*`, `/lista-espera/*`).

## Rollback Notes

1. Revert the Alembic migration: `alembic downgrade <previous_revision>`.
2. Revert commits for `config.py`, schemas, router, service, tests, and `.env.example`.
3. Re-run the full test suite to confirm baseline.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tests still reference removed env vars | High | Inventory every `monkeypatch.setenv` in tasks T-05/T-06 before running tests. |
| Hidden `settings.google_calendar_id` reads | Medium | Search the whole backend for the removed fields during T-01. |
| Cross-professional data leak | Medium | Security audit task T-07 with explicit checklist and new isolation tests. |
| Local dev `.env` break | Low | Update `.env.example` and README env-var table. |

## Skill Resolution

Self-loaded from skill paths: `sdd-design`, `_shared/sdd-phase-common.md`, `_shared/openspec-convention.md`.

## Next Recommended Phase

`sdd-tasks`
