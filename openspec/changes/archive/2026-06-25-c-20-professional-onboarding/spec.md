# Delta Specs for C-20-professional-onboarding

> **TDD deferral note**: Test specs deferred per user directive.
> Multi-tenancy scoped by `profesional_id`; no `tenant_id`.

## professional-onboarding (NEW)

### Purpose
Invitation-only professional creation by super-admin; credentials shown once.

### Requirements

#### Requirement: Super-admin creates a professional
The system SHALL expose `POST /admin/profesionales` for super-admins only, creating an active professional with default schedule values.

##### Scenario: Successful creation
- GIVEN a valid super-admin JWT
- WHEN `POST /admin/profesionales` with `nombre`, unique `email`, `password` (>= 8 chars), and `especialidad`
- THEN the system creates a `Profesional` with `is_active=True`, bcrypt `password_hash`, generated `api_key` and `telegram_secret_token`, and default schedule (`duracion_turno=30`, `horario_inicio=09:00`, `horario_fin=17:00`, `dias_atencion` Lunes-Viernes)
- AND returns `201 Created` with the profile plus plaintext `api_key` and `telegram_secret_token`

##### Scenario: Duplicate email
- GIVEN existing professional with same email
- WHEN admin posts that email
- THEN the system returns `409 Conflict`

##### Scenario: Weak password
- WHEN admin posts password < 8 chars
- THEN the system returns `422 Unprocessable Entity`

##### Scenario: Missing required field
- WHEN request omits a required field
- THEN the system returns `422 Unprocessable Entity`

##### Scenario: Non-admin request
- GIVEN non-admin or missing token
- WHEN posting to `/admin/profesionales`
- THEN the system returns `403 Forbidden`

#### Requirement: New professionals are active by default
The system SHALL set `is_active=True` when a professional is created.

##### Scenario: Active by default
- GIVEN a successful creation
- THEN the created professional has `is_active=True`

## professional-integration-setup (NEW)

### Purpose
Authenticated professionals set Telegram/Google Calendar tokens; secrets never exposed in reads.

### Requirements

#### Requirement: Update integration tokens
The system SHALL allow an authenticated professional to set or update `telegram_bot_token` and/or `google_refresh_token` via `PUT /profesional/integraciones`.

##### Scenario: Update both tokens
- GIVEN authenticated professional
- WHEN `PUT /profesional/integraciones` with both tokens
- THEN the system persists both and returns `200 OK` with profile masking all secrets

##### Scenario: Partial update
- GIVEN professional with Google token set
- WHEN `PUT /profesional/integraciones` with only `telegram_bot_token`
- THEN the system updates only Telegram token and leaves Google unchanged

##### Scenario: Empty token rejected
- WHEN request provides empty `telegram_bot_token` or `google_refresh_token`
- THEN the system returns `422 Unprocessable Entity`

#### Requirement: Read integration status
The system SHALL expose `GET /profesional/integraciones` returning configured status without secrets.

##### Scenario: Read status
- GIVEN professional with Telegram configured and Google missing
- WHEN `GET /profesional/integraciones`
- THEN the system returns `200 OK` with `has_telegram=true`, `has_google=false`, and no plaintext credentials

## professional-jwt-auth (MODIFIED)

### REMOVED Requirements

#### Requirement: Profesional can register an account
(Reason: Invitation-only onboarding by super-admin; public self-registration removed.)
(Migration: Use `POST /admin/profesionales`; update or remove `/auth/register` tests.)

## super-admin-professional-management (MODIFIED)

### ADDED Requirements

#### Requirement: Super-admin can create a professional
Expose `POST /admin/profesionales` restricted to super-admin.
(See `professional-onboarding` for scenarios.)

#### Requirement: Admin read responses mask secrets
The system SHALL omit `api_key`, `telegram_secret_token`, `telegram_bot_token`, and `google_refresh_token` from admin list/detail responses.

##### Scenario: Admin list omits secrets
- WHEN super-admin lists professionals
- THEN the response contains no plaintext credentials

## Security & Business Rules

### Requirement: Email uniqueness
The system SHALL enforce unique professional emails and return `409 Conflict` on duplicates.

##### Scenario: Concurrent duplicate creation
- GIVEN two creation requests with same email
- WHEN both reach the database
- THEN only one succeeds and the other receives `409 Conflict`

### Requirement: HTTPS in production
The system SHALL require HTTPS for `/admin/profesionales` and `/profesional/integraciones` when `ENV=production`.

##### Scenario: HTTP rejected in production
- GIVEN `ENV=production`
- WHEN HTTP request hits those endpoints
- THEN the system rejects or redirects the request

### Requirement: No plaintext secrets in logs
The system SHALL not log `api_key`, `telegram_secret_token`, `telegram_bot_token`, `google_refresh_token`, or `password_hash`.

##### Scenario: Logs omit secrets
- GIVEN creation or integration update request
- WHEN request/response is logged
- THEN logs contain no plaintext credentials
