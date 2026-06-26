# Tasks: C-22 `hardening-config-cleanup`

## Status

`tasks`

## Executive Summary

Break C-22 into 12 small, well-delimited tasks across 5 phases. Work is split into 4 chained PRs to stay within the 800-line review budget. Each PR has autonomous scope, clear verification, and safe rollback.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 500–670 |
| 800-line budget risk | Low |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | chained-from-start |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Remove deprecated env vars from Settings, .env.example, test_config | PR 1 | Foundation; no runtime behavior change yet |
| 2 | Add `google_calendar_id` to model, migration, schemas, router, CalendarService | PR 2 | Core feature; depends on PR 1 (clean Settings) |
| 3 | Clean all test monkeypatches and fixtures | PR 3 | Depends on PR 1 + PR 2 (fields removed/added) |
| 4 | Security audit, isolation tests, docs | PR 4 | Independent verification; depends on PR 2 for endpoint changes |

---

## Phase 1: Configuration Cleanup

- [x] **T-01** Remove deprecated fields from `Settings`
  - **Files**: `backend/app/config.py`
  - **Change**: Delete `telegram_bot_token`, `google_calendar_credentials`, `google_calendar_id` fields and their validators.
  - **Acceptance**: `Settings()` instantiates without those env vars. `grep` finds zero references to removed fields in `config.py`.
  - **Est. lines**: ~10
  - **Deps**: None

- [x] **T-02** Remove deprecated vars from `.env.example`
  - **Files**: `backend/.env.example`
  - **Change**: Delete `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID` lines.
  - **Acceptance**: `.env.example` contains no references to the three removed vars.
  - **Est. lines**: ~3
  - **Deps**: T-01

- [x] **T-03** Update `test_config.py` assertions
  - **Files**: `backend/tests/test_config.py`
  - **Change**: Remove all `monkeypatch.setenv` calls for the three deprecated vars. Remove assertions that check their values. Add assertions that `Settings` has no such attributes (`assert not hasattr(settings, "telegram_bot_token")`, etc.).
  - **Acceptance**: `pytest test_config.py` passes. All 7 test methods updated.
  - **Est. lines**: ~25
  - **Deps**: T-01

## Phase 2: Data Model + API + Service

- [x] **T-04** Add `google_calendar_id` column to `Profesional` model
  - **Files**: `backend/app/models/profesional.py`
  - **Change**: Add `google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, server_default="primary")`.
  - **Acceptance**: Model imports cleanly. Column definition matches design spec (VARCHAR(255), nullable, server_default "primary").
  - **Est. lines**: ~5
  - **Deps**: None

- [x] **T-05** Create Alembic migration for `google_calendar_id`
  - **Files**: `backend/alembic/versions/<timestamp>_c22_add_google_calendar_id.py`
  - **Change**: `op.add_column("profesional", sa.Column("google_calendar_id", sa.String(255), nullable=True, server_default="primary"))`. Downgrade: `op.drop_column`.
  - **Acceptance**: `alembic upgrade head` succeeds on test DB. `alembic downgrade -1` reverses cleanly. Existing rows get `"primary"`.
  - **Est. lines**: ~30
  - **Deps**: T-04

- [x] **T-06** Update integration schemas
  - **Files**: `backend/app/schemas/profesional.py`
  - **Change**: Add `google_calendar_id: Optional[str] = None` to `ProfesionalIntegracionesUpdate`. Add `google_calendar_id: str` to `ProfesionalIntegracionesResponse`. Add empty-string rejection validator for `google_calendar_id`.
  - **Acceptance**: Schema accepts partial updates with `google_calendar_id`. Empty string raises `ValidationError`. Response includes `google_calendar_id`.
  - **Est. lines**: ~15
  - **Deps**: T-04

- [x] **T-07** Update integration router
  - **Files**: `backend/app/routers/profesional.py`
  - **Change**: In `PUT /profesional/integraciones`: persist `google_calendar_id` when provided (same partial-update pattern as existing fields). In `GET /profesional/integraciones`: return `google_calendar_id` from the professional record.
  - **Acceptance**: `PUT` with only `google_calendar_id` updates just that field. `GET` returns `google_calendar_id="primary"` for unset professionals. Empty string returns 422.
  - **Est. lines**: ~20
  - **Deps**: T-06

- [x] **T-08** Update `CalendarService` to use per-professional calendar ID
  - **Files**: `backend/app/services/calendar_service.py`
  - **Change**: Replace `self.settings.google_calendar_id` with `profesional.google_calendar_id or "primary"` at lines 79, 92, 101. Method signatures must accept `profesional` (or `google_calendar_id` string) as parameter.
  - **Acceptance**: Service no longer references `settings.google_calendar_id`. Fallback to `"primary"` when professional value is None/empty.
  - **Est. lines**: ~15
  - **Deps**: T-04, T-01

## Phase 3: Test Fixture Cleanup

- [x] **T-09** Clean `conftest.py` fixtures
  - **Files**: `backend/tests/conftest.py`
  - **Change**: Remove `TELEGRAM_BOT_TOKEN` monkeypatches from `client` (line 22) and `api_client` (line 91) fixtures. Add `google_calendar_id="primary"` to `profesional` fixture (lines 66-84).
  - **Acceptance**: Fixtures instantiate without deprecated env vars. `profesional` fixture has `google_calendar_id` set.
  - **Est. lines**: ~10
  - **Deps**: T-01, T-04

- [x] **T-10** Clean `test_calendar_service.py`
  - **Files**: `backend/tests/test_calendar_service.py`
  - **Change**: Remove `google_calendar_id="primary"` from Settings constructor calls in all 8 test methods. Ensure `profesional_con_refresh` fixture includes `google_calendar_id`. Assert service reads from professional, not settings.
  - **Acceptance**: All 8 tests pass. No Settings constructor receives `google_calendar_id`.
  - **Est. lines**: ~20
  - **Deps**: T-08, T-09

- [x] **T-11** Clean remaining test monkeypatches (batch 1: scheduler)
  - **Files**: `backend/tests/test_scheduler.py`, `backend/tests/test_scheduler_timeout.py`, `backend/tests/test_scheduler_job.py`, `backend/tests/test_scheduler_isolation.py`
  - **Change**: Remove `TELEGRAM_BOT_TOKEN` monkeypatches (test_scheduler.py:24, test_scheduler_timeout.py:28,41). Remove `GOOGLE_CALENDAR_CREDENTIALS` and `GOOGLE_CALENDAR_ID` monkeypatches from test_scheduler_job.py (9 methods) and test_scheduler_isolation.py (1 method).
  - **Acceptance**: All scheduler tests pass without deprecated env var patches.
  - **Est. lines**: ~40
  - **Deps**: T-01

- [x] **T-12** Clean remaining test monkeypatches (batch 2: service + other)
  - **Files**: `backend/tests/test_turno_service.py`, `backend/tests/test_lista_espera_service.py`, `backend/tests/test_lista_espera_integration.py`, `backend/tests/test_telegram_service.py`, `backend/tests/test_auth_jwt.py`, `backend/tests/test_database.py`
  - **Change**: Remove `GOOGLE_CALENDAR_CREDENTIALS` from `test_settings` fixtures (test_turno_service.py:28-29, test_lista_espera_service.py:28-29). Remove `TELEGRAM_BOT_TOKEN` monkeypatches (test_telegram_service.py:328, test_auth_jwt.py:14, test_database.py:14,48, test_lista_espera_integration.py:47).
  - **Acceptance**: All listed tests pass without deprecated env var patches.
  - **Est. lines**: ~30
  - **Deps**: T-01

## Phase 4: Security Audit + Isolation Tests

- [x] **T-13** Security/scoping audit of all routers
  - **Files**: `backend/app/routers/profesional.py`, `backend/app/routers/admin.py`, `backend/app/routers/paciente.py`, `backend/app/routers/turno.py`, `backend/app/routers/lista_espera.py`
  - **Change**: Verify every endpoint uses correct auth dependency (`CurrentProfesionalDep` or `CurrentSuperAdminDep`). Verify every DB query filters by `profesional_id`. Verify `PUT /profesional/integraciones` enforces HTTPS in production. Verify responses never expose `telegram_bot_token`, `google_refresh_token`, or `password_hash`. Document findings.
  - **Acceptance**: Checklist from design completed. No unscoped queries found (or gaps documented with follow-up tasks).
  - **Est. lines**: ~30 (code changes if gaps found; otherwise documentation)
  - **Deps**: T-07

- [x] **T-14** Add missing isolation tests
  - **Files**: `backend/tests/test_profesional.py`, `backend/tests/test_isolation_*.py` (new if needed)
  - **Change**: Add partial-update test for `google_calendar_id` on `PUT /profesional/integraciones`. Add empty-string rejection test. Add cross-professional isolation tests for list endpoints (`/profesional/turnos-hoy`, `/pacientes/*`, `/turnos/*`, `/lista-espera/*`) — verify professional A cannot see professional B's data.
  - **Acceptance**: New tests pass. Cross-professional access returns 404/403.
  - **Est. lines**: ~60
  - **Deps**: T-07, T-13

## Phase 5: Documentation

- [x] **T-15** Update documentation references
  - **Files**: `knowledge-base/` (if env vars referenced), `README.md` (if env var table exists)
  - **Change**: Remove references to `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID` from any documentation. Document `profesional.google_calendar_id` if integration setup is described.
  - **Acceptance**: `grep` across docs finds zero references to removed env vars.
  - **Est. lines**: ~15
  - **Deps**: T-02

---

## PR Boundaries

| PR | Tasks | Est. Lines | Scope |
|----|-------|-----------|-------|
| **PR 1**: Config cleanup | T-01, T-02, T-03 | ~38 | Remove dead env vars. App boots without them. |
| **PR 2**: Model + API + Service | T-04, T-05, T-06, T-07, T-08 | ~85 | Per-professional calendar ID end-to-end. |
| **PR 3**: Test cleanup | T-09, T-10, T-11, T-12 | ~100 | Remove all deprecated monkeypatches. Full suite green. |
| **PR 4**: Security + Docs | T-13, T-14, T-15 | ~105 | Audit, isolation tests, documentation. |
| **Total** | 15 tasks | ~328–670 | |

## Risks

| Risk | Mitigation |
|------|------------|
| Tests still reference removed env vars after T-01 | T-09 through T-12 inventory every monkeypatch; run full suite after each batch |
| Hidden `settings.google_calendar_id` reads | `grep` entire backend in T-08 before modifying CalendarService |
| Migration fails on existing data | Server default `"primary"` handles all existing rows; test upgrade+downgrade in T-05 |
| Isolation gaps found in audit | T-13 documents findings; T-14 adds targeted tests |

## Skill Resolution

`fallback-path` — loaded `sdd-tasks`, `_shared/sdd-phase-common.md`, `_shared/openspec-convention.md`.

## Next Recommended Phase

`sdd-apply` — start with PR 1 (T-01 → T-02 → T-03).
