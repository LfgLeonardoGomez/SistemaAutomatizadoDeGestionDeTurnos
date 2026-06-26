# Delta for professional-integration-setup

## MODIFIED Requirements

### Requirement: Update integration tokens

The system SHALL allow an authenticated professional to set or update `telegram_bot_token`, `google_refresh_token`, and/or `google_calendar_id` via `PUT /profesional/integraciones`.
(Previously: The endpoint accepted only `telegram_bot_token` and `google_refresh_token`.)

#### Scenario: Update all integration fields
- GIVEN authenticated professional
- WHEN `PUT /profesional/integraciones` with all three fields
- THEN the system persists all and returns `200 OK` with a response that masks all secrets

#### Scenario: Partial update calendar ID only
- GIVEN professional with Telegram and Google tokens already set
- WHEN `PUT /profesional/integraciones` with only `google_calendar_id`
- THEN the system updates only the calendar ID and leaves tokens unchanged

#### Scenario: Empty token rejected
- WHEN request provides empty `telegram_bot_token` or `google_refresh_token`
- THEN the system returns `422 Unprocessable Entity`

#### Scenario: Empty calendar ID rejected
- WHEN request provides empty `google_calendar_id`
- THEN the system returns `422 Unprocessable Entity`

### Requirement: Read integration status

The system SHALL expose `GET /profesional/integraciones` returning configured status and `google_calendar_id` without secrets.
(Previously: The response returned only `has_telegram` and `has_google`.)

#### Scenario: Read status
- GIVEN professional with Telegram configured, Google missing, and default calendar ID
- WHEN `GET /profesional/integraciones`
- THEN the system returns `200 OK` with `has_telegram=true`, `has_google=false`, and `google_calendar_id="primary"`

## ADDED Requirements

### Requirement: Default calendar ID

The system SHALL store `google_calendar_id` on `Profesional` with a server default of `"primary"` when no value is provided.

#### Scenario: New professional defaults to primary
- GIVEN a newly created professional
- WHEN `GET /profesional/integraciones` is called
- THEN `google_calendar_id` is `"primary"`
