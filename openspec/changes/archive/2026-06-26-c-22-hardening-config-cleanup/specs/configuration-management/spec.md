# Delta for configuration-management

## REMOVED Requirements

### Requirement: Telegram bot token via global environment

The system SHALL NOT declare `TELEGRAM_BOT_TOKEN` in Pydantic Settings.

(Reason: The token is stored per-professional after C-14/C-20; a global value is dead configuration.)
(Migration: Use `PUT /profesional/integraciones` to persist the token on each professional.)

### Requirement: Google service-account credentials via global environment

The system SHALL NOT declare `GOOGLE_CALENDAR_CREDENTIALS` in Pydantic Settings.

(Reason: Google Calendar authentication moved to per-professional `google_refresh_token` after C-14/C-20.)
(Migration: Use `PUT /profesional/integraciones` to persist the refresh token on each professional.)

### Requirement: Global Google Calendar ID fallback

The system SHALL NOT declare `GOOGLE_CALENDAR_ID` in Pydantic Settings.

(Reason: Calendar target is per-professional via `profesional.google_calendar_id` introduced in this change.)
(Migration: Set `google_calendar_id` via `PUT /profesional/integraciones` or accept the default `"primary"`.)

## MODIFIED Requirements

### Requirement: Required environment variables are validated at startup

The system SHALL validate all required environment variables at application startup using Pydantic Settings. If a required variable is missing or invalid, the application SHALL fail to start with a clear error message indicating which variable is missing.
(Previously: Settings also required `TELEGRAM_BOT_TOKEN` and `GOOGLE_CALENDAR_CREDENTIALS`.)

#### Scenario: Startup with all required variables
- WHEN the backend starts with all required environment variables present and valid
- THEN the application SHALL start successfully
- AND the settings object SHALL be accessible via dependency injection

#### Scenario: Startup with missing required variable
- WHEN the backend starts without the `DATABASE_URL` environment variable
- THEN the application SHALL raise a `ValidationError` during startup
- AND the error message SHALL indicate that `DATABASE_URL` is missing

#### Scenario: Startup without deprecated variables
- GIVEN `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, and `GOOGLE_CALENDAR_ID` are absent
- WHEN the backend starts
- THEN the application SHALL start successfully
- AND `Settings` SHALL NOT expose those attributes
