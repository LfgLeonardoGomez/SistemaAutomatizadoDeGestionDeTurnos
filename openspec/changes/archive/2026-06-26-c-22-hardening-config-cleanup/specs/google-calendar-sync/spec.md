# Delta for google-calendar-sync

## MODIFIED Requirements

### Requirement: Google Calendar authentication per professional

The system SHALL authenticate with Google Calendar API using each professional's stored `google_refresh_token` together with global OAuth client credentials.
(Previously: Authentication used a service-account JSON via the global `GOOGLE_CALENDAR_CREDENTIALS` environment variable.)

#### Scenario: Authentication succeeds with refresh token
- GIVEN professional has `google_refresh_token` set
- WHEN the calendar service is built for that professional
- THEN it constructs valid OAuth credentials and can call Google Calendar API

#### Scenario: Missing refresh token fails fast
- GIVEN professional has no `google_refresh_token`
- WHEN the calendar service is built for that professional
- THEN it raises a configuration error

### Requirement: Calendar target per professional

The system SHALL target the calendar identified by `profesional.google_calendar_id`, falling back to `"primary"` when the value is null or empty.
(Previously: The target calendar was read from the global `GOOGLE_CALENDAR_ID` setting.)

#### Scenario: Create event on configured calendar
- GIVEN professional with `google_calendar_id="clinic@example.com"`
- WHEN `create_event(turno)` is invoked
- THEN the event is inserted into `"clinic@example.com"`

#### Scenario: Create event with default calendar
- GIVEN professional with `google_calendar_id` unset
- WHEN `create_event(turno)` is invoked
- THEN the event is inserted into `"primary"`

#### Scenario: Update and delete use same calendar
- GIVEN an existing event on the professional's configured calendar
- WHEN `update_event(turno)` or `delete_event(event_id)` is invoked
- THEN the operation targets the same `calendarId` used for creation

### Requirement: Pydantic Settings for Google Calendar

The system SHALL declare only `google_client_id`, `google_client_secret`, `google_calendar_max_retries`, `google_calendar_base_delay`, and `google_calendar_max_delay` as Pydantic Settings fields for Google Calendar integration.
(Previously: Settings also included `GOOGLE_CALENDAR_CREDENTIALS` and `GOOGLE_CALENDAR_ID`.)

#### Scenario: Valid settings present
- WHEN the backend starts with Google OAuth client settings and retry settings
- THEN `Settings` exposes them as typed attributes
- AND startup succeeds without `GOOGLE_CALENDAR_CREDENTIALS` or `GOOGLE_CALENDAR_ID`
