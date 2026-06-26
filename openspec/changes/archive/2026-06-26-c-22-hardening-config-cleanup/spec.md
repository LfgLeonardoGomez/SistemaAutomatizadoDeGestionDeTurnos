# Spec: C-22 `hardening-config-cleanup`

## Status

`spec`

## Executive Summary

This change removes dead global environment variables (`TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID`) that were replaced by per-professional configuration, adds `profesional.google_calendar_id` with a `"primary"` default, and runs a security/scoping audit of all authenticated endpoints before v2.0 release.

## Functional Requirements

### Domain: configuration-management

#### REMOVED: Telegram bot token via global environment
- The system SHALL NOT declare `TELEGRAM_BOT_TOKEN` in Pydantic Settings.
- (Reason: per-professional storage after C-14/C-20. Migration: `PUT /profesional/integraciones`.)

#### REMOVED: Google service-account credentials via global environment
- The system SHALL NOT declare `GOOGLE_CALENDAR_CREDENTIALS` in Pydantic Settings.
- (Reason: per-professional `google_refresh_token` after C-14/C-20. Migration: `PUT /profesional/integraciones`.)

#### REMOVED: Global Google Calendar ID fallback
- The system SHALL NOT declare `GOOGLE_CALENDAR_ID` in Pydantic Settings.
- (Reason: target calendar is now per-professional. Migration: `PUT /profesional/integraciones` or accept default `"primary"`.)

#### MODIFIED: Required environment variables are validated at startup
- The system SHALL validate required environment variables at startup. It SHALL start successfully when deprecated variables are absent.
- Scenario: Startup without deprecated variables → app starts and `Settings` does not expose them.

### Domain: professional-integration-setup

#### MODIFIED: Update integration tokens
- The system SHALL allow an authenticated professional to update `telegram_bot_token`, `google_refresh_token`, and/or `google_calendar_id` via `PUT /profesional/integraciones`.
- Scenario: Partial update calendar ID only → only `google_calendar_id` changes.
- Scenario: Empty calendar ID rejected → `422 Unprocessable Entity`.

#### MODIFIED: Read integration status
- The system SHALL expose `GET /profesional/integraciones` returning `has_telegram`, `has_google`, and `google_calendar_id` without secrets.
- Scenario: Read status → returns `google_calendar_id="primary"` when unset.

#### ADDED: Default calendar ID
- The system SHALL store `google_calendar_id` on `Profesional` with server default `"primary"`.

### Domain: google-calendar-sync

#### MODIFIED: Google Calendar authentication per professional
- The system SHALL authenticate using the professional's `google_refresh_token` and global OAuth client credentials.
- Scenario: Missing refresh token → configuration error.

#### MODIFIED: Calendar target per professional
- The system SHALL target `profesional.google_calendar_id`, falling back to `"primary"`.
- Scenario: Create event on configured calendar → uses professional value.
- Scenario: Create event with default calendar → uses `"primary"`.

#### MODIFIED: Pydantic Settings for Google Calendar
- The system SHALL declare only `google_client_id`, `google_client_secret`, and retry settings for Google Calendar.

## Non-Functional Requirements

| Requirement | Description |
|-------------|-------------|
| Security | No plaintext secrets in logs; HTTPS required in production for `/profesional/integraciones`. |
| Backward compatibility | Existing professionals receive `"primary"` via database default. |
| Testability | All deprecated env-var monkeypatches removed; tests run with per-professional fixtures. |
| Auditability | Security/scoping checklist executed and results recorded in verify report. |

## API Contract Details

### `PUT /profesional/integraciones`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `telegram_bot_token` | string | No | Partial update; empty string rejected. |
| `google_refresh_token` | string | No | Partial update; empty string rejected. |
| `google_calendar_id` | string | No | Partial update; empty string rejected; defaults to `"primary"`. |

Response: `200 OK` with `ProfesionalIntegracionesResponse`.

### `GET /profesional/integraciones`

Response: `200 OK` with `ProfesionalIntegracionesResponse` extended with `google_calendar_id: string`.

## Data Model Changes

| Table | Change |
|-------|--------|
| `profesional` | ADD `google_calendar_id VARCHAR(255) NULL DEFAULT 'primary'`. |

## Test Requirements

1. `test_config.py` asserts `Settings` has no `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, or `GOOGLE_CALENDAR_ID`.
2. Migration test confirms existing rows default to `"primary"`.
3. `test_profesional.py` covers partial update of `google_calendar_id` and rejection of empty values.
4. `test_calendar_service.py` verifies `calendarId` is read from the professional instance with `"primary"` fallback.
5. All monkeypatches for deprecated env vars are removed from `conftest.py` and individual test files.

## Security / Scoping Audit Checklist

- [ ] Every endpoint under `/profesional/*` uses `CurrentProfesionalDep` or API-key dependency.
- [ ] Every database query in `/profesional/*` filters by `profesional_id`.
- [ ] Super-admin endpoints under `/admin/*` are authenticated with super-admin credentials and do not leak professional-scoped data.
- [ ] `PUT /profesional/integraciones` rejects HTTP in production (`ENV=production`).
- [ ] `telegram_bot_token`, `google_refresh_token`, and `password_hash` never appear in logs or responses.
- [ ] Missing isolation tests are added for any endpoint that returns lists scoped to a professional.

## Skill Resolution

Self-loaded from skill paths: `sdd-spec`, `_shared/sdd-phase-common.md`, `_shared/openspec-convention.md`.

## Next Recommended Phase

`sdd-design`
