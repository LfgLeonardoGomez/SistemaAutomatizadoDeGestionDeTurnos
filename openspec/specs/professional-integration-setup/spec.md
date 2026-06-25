# Professional Integration Setup

## Purpose

Authenticated professionals set Telegram/Google Calendar tokens; secrets never exposed in reads.

## Requirements

### Requirement: Update integration tokens
The system SHALL allow an authenticated professional to set or update `telegram_bot_token` and/or `google_refresh_token` via `PUT /profesional/integraciones`.

#### Scenario: Update both tokens
- GIVEN authenticated professional
- WHEN `PUT /profesional/integraciones` with both tokens
- THEN the system persists both and returns `200 OK` with profile masking all secrets

#### Scenario: Partial update
- GIVEN professional with Google token set
- WHEN `PUT /profesional/integraciones` with only `telegram_bot_token`
- THEN the system updates only Telegram token and leaves Google unchanged

#### Scenario: Empty token rejected
- WHEN request provides empty `telegram_bot_token` or `google_refresh_token`
- THEN the system returns `422 Unprocessable Entity`

### Requirement: Read integration status
The system SHALL expose `GET /profesional/integraciones` returning configured status without secrets.

#### Scenario: Read status
- GIVEN professional with Telegram configured and Google missing
- WHEN `GET /profesional/integraciones`
- THEN the system returns `200 OK` with `has_telegram=true`, `has_google=false`, and no plaintext credentials

### Requirement: HTTPS in production
The system SHALL require HTTPS for `/profesional/integraciones` when `ENV=production`.

#### Scenario: HTTP rejected in production
- GIVEN `ENV=production`
- WHEN HTTP request hits `/profesional/integraciones`
- THEN the system rejects or redirects the request

### Requirement: No plaintext secrets in logs
The system SHALL not log `telegram_bot_token`, `google_refresh_token`, or `password_hash`.

#### Scenario: Logs omit secrets
- GIVEN integration update request
- WHEN request/response is logged
- THEN logs contain no plaintext credentials
