# Delta for Professional API Key Authentication

## MODIFIED Requirements

### Requirement: System validates API key on integration endpoints

The system SHALL provide a reusable dependency `get_profesional_by_api_key` that validates an API key passed via HTTP header and loads the active professional. Integration endpoints accepting this dependency — directly, or via the flexible dependency defined in `professional-flexible-auth` — now explicitly include all `/turnos/*` endpoints, in addition to `recordatorios.py`.
(Previously: "integration endpoints" scope was implicit and did not include `/turnos/*`.)

#### Scenario: Valid API key
- **WHEN** a request includes a valid `X-API-Key` header (or configured header name)
- **THEN** `get_profesional_by_api_key` finds the professional by that key and `is_active=True`
- **AND** returns the Profesional instance

#### Scenario: Invalid or missing API key
- **WHEN** a request includes an invalid or missing API key
- **THEN** `get_profesional_by_api_key` raises a 401 Unauthorized HTTPException

#### Scenario: API key belongs to inactive professional
- **WHEN** a request includes a valid API key but the professional has `is_active=False`
- **THEN** `get_profesional_by_api_key` raises a 401 Unauthorized HTTPException

#### Scenario: Applied to turno endpoints (new)
- **WHEN** a request to any `/turnos/*` endpoint includes a valid `X-API-Key`
- **THEN** the professional is authenticated via the same key-resolution logic as `get_profesional_by_api_key`, invoked from `get_current_profesional_flexible`
- **AND** the request proceeds identically to a JWT-authenticated request

## ADDED Requirements

### Requirement: Security hardening stays deferred for this scope expansion

The system SHALL NOT introduce api_key hashing-at-rest or request rate limiting as part of extending API-key acceptance to `/turnos/*`. Both remain plaintext/unthrottled by explicit decision, tracked as separate follow-up work.

#### Scenario: API key comparison stays plaintext
- **GIVEN** the `/turnos/*` scope expansion is deployed
- **WHEN** `get_profesional_by_api_key` compares an incoming key
- **THEN** the comparison is a plaintext equality check against `Profesional.api_key`, unchanged from current behavior

#### Scenario: No rate limiting added
- **GIVEN** a client makes repeated `/turnos/*` requests with a valid or invalid API key
- **WHEN** the requests are processed
- **THEN** the system applies no new rate-limit or throttling logic beyond what existed before this change

### Requirement: Revocation remains overwrite-on-regenerate only

The system SHALL continue to revoke a professional's previous API key only by overwriting it via `POST /auth/api-key` regeneration (existing `professional-api-key` behavior). No dedicated revoke/disable endpoint is introduced by this change.

#### Scenario: No new revoke endpoint
- **GIVEN** a professional wants to invalidate their current API key without generating a replacement
- **WHEN** they look for a dedicated revoke action
- **THEN** none exists; regenerating via `POST /auth/api-key` is the only supported invalidation path
