# Proposal: C-22 `hardening-config-cleanup`

## Status

`proposal`

## Executive Summary

Final cleanup change for v2.0: remove global environment variables now replaced by per-professional database configuration, move `google_calendar_id` to `Profesional`, and run a security/scoping audit before declaring v2.0 complete.

## Intent

- Eliminate dead global configuration (`TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`) that became redundant after C-14/C-20 moved those values into `Profesional`.
- Fix the remaining global calendar ID so each professional can target their own Google Calendar.
- Harden the backend by verifying JWT/API-key isolation and endpoint scoping before release.

## Scope

### In Scope
- Remove `TELEGRAM_BOT_TOKEN` and `GOOGLE_CALENDAR_CREDENTIALS` from `backend/app/config.py` and `backend/.env.example`.
- Add `profesional.google_calendar_id` column (nullable, default `"primary"`) with Alembic migration.
- Update `PUT /profesional/integraciones` request/response schemas to accept and return `google_calendar_id`.
- Update `calendar_service.py` to use `profesional.google_calendar_id or "primary"`.
- Adjust `conftest.py`, `test_config.py`, `test_calendar_service.py`, and all test files that monkeypatch the deprecated env vars.
- Security/scoping audit of JWT/API-key isolation and endpoint scoping.

### Out of Scope
- C-21 data migration (already N/A); no legacy data to re-tag.
- New onboarding UI or Telegram flows.
- Refactor of Google OAuth credential strategy beyond the per-professional `google_refresh_token` already in place.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `professional-integration-setup`: add `google_calendar_id` to the integration resource and partial-update semantics.
- `google-calendar-sync`: calendar target is now per-professional instead of global.
- `configuration-management`: remove deprecated environment variables from Pydantic Settings.

## Approach and Key Decisions

1. **Settings cleanup**: delete the two dead fields from `Settings`; validate that the app still starts without them.
2. **Database change**: add `google_calendar_id` to `Profesional`, nullable, server default `"primary"`.
3. **API change**: extend `ProfesionalIntegracionesUpdate`/`ProfesionalIntegracionesResponse` with `google_calendar_id`; persist only when provided.
4. **Service change**: pass the professional instance into `calendar_service` operations and read `profesional.google_calendar_id`, falling back to `"primary"`.
5. **Test cleanup**: remove monkeypatches for `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, and global `GOOGLE_CALENDAR_ID`; set `google_calendar_id` on the test professional fixture.
6. **Security audit**: review every router for `get_current_profesional` or API-key dependency and confirm queries filter by `profesional_id`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/config.py` | Removed | `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS` fields |
| `backend/app/models/profesional.py` | New | `google_calendar_id` column |
| `backend/app/routers/profesional.py` | Modified | `PUT /profesional/integraciones` handles new field |
| `backend/app/schemas/profesional.py` | Modified | request/response schemas include `google_calendar_id` |
| `backend/app/services/calendar_service.py` | Modified | uses per-professional calendar ID |
| `backend/.env.example` | Removed | deprecated env vars |
| `backend/tests/` | Modified | fixtures and monkeypatches cleaned up |

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tests fail because fixtures still reference removed env vars | High | Inventory all monkeypatches in the task breakdown and update before running the suite |
| `calendar_service` still references global `GOOGLE_CALENDAR_ID` | Med | Centralize reads through the professional instance and keep `"primary"` fallback |
| Hidden endpoint leaks data across professionals | Med | Security audit task with explicit checklist; add missing isolation tests |
| Backward break for local dev `.env` files | Low | Update `.env.example` and README; dev must drop deprecated keys |

## Non-Goals

- No new tenant model changes.
- No changes to Telegram bot token storage or multi-bot routing.
- No new user-facing features; this is cleanup and hardening only.

## Rollback Plan

1. Revert the Alembic migration that adds `google_calendar_id`.
2. Restore the previous commit for `config.py`, schemas, router, and `calendar_service.py`.
3. Restore previous `.env.example`.
4. Re-run the test suite to confirm baseline.

## Dependencies

- C-19 `super-admin-role` (archived)
- C-20 `professional-onboarding` (archived)

## Success Criteria

- [ ] `TELEGRAM_BOT_TOKEN` and `GOOGLE_CALENDAR_CREDENTIALS` are absent from `Settings` and `.env.example`.
- [ ] `Profesional.google_calendar_id` exists, defaults to `"primary"`, and is returned by `GET /profesional/integraciones`.
- [ ] `PUT /profesional/integraciones` persists `google_calendar_id` without requiring other fields.
- [ ] `calendar_service.py` no longer reads a global calendar ID.
- [ ] All tests pass after deprecated env var monkeypatches are removed.
- [ ] Security audit checklist confirms every scoped endpoint filters by the authenticated professional.

## Suggested Task Breakdown

1. **T-01 Remove deprecated env vars from Settings and `.env.example`** — delete fields, update `test_config.py` assertions.
2. **T-02 Add `google_calendar_id` to `Profesional` model and migration** — Alembic upgrade/downgrade, seed default.
3. **T-03 Update integration schemas and `PUT /profesional/integraciones`** — request/response, partial update, masked secrets preserved.
4. **T-04 Update `calendar_service.py` to use per-professional calendar ID** — inject professional, fallback to `"primary"`.
5. **T-05 Clean `conftest.py` and `test_calendar_service.py` fixtures** — remove global env var patches, set field on professional fixture.
6. **T-06 Clean remaining test monkeypatches** — `test_scheduler*.py`, `test_turno_service.py`, `test_lista_espera*.py`, `test_telegram_service.py`, `test_auth_jwt.py`, `test_database.py`.
7. **T-07 Security/scoping audit** — review all routers; add isolation tests where missing.
8. **T-08 Update docs** — env var table in README/knowledge-base if still referenced.

## Proposal Question Round

Before finalizing, confirm or correct these assumptions:

1. Should `google_calendar_id` remain optional with fallback `"primary"`, or become required once the professional saves integrations?
2. Do we keep the global `GOOGLE_CALENDAR_ID` env var as a system-wide fallback, or remove it entirely in favor of the per-professional column?
3. For the security audit, should we verify **all** authenticated endpoints or only the professional-scoped ones (super-admin endpoints excluded)?

## Skill Resolution

Self-loaded from skill paths: `sdd-propose`, `_shared/sdd-phase-common.md`, `_shared/openspec-convention.md`.

## Next Recommended Phase

`sdd-spec`
