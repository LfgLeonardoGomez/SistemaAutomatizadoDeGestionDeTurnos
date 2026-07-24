# Professional Flexible Authentication Specification

## Purpose

Allow n8n (a 24/7 machine caller) to authenticate against `/turnos/*` endpoints without hitting the 24h JWT expiry, by accepting either a non-expiring `X-API-Key` or the existing `Authorization: Bearer` JWT as equivalent professional-scoped credentials.

**Non-goals** (explicitly deferred): api_key hashing-at-rest, rate limiting, an explicit revoke endpoint (v1 uses overwrite-on-regenerate, already covered by `professional-api-key`), and any change to `pacientes.py`, `lista_espera.py`, `recordatorios.py`, dashboard, Telegram-webhook, or super-admin auth.

## Requirements

### Requirement: Turno endpoints accept dual authentication

The system MUST authenticate requests to all `/turnos/*` endpoints via either a valid `X-API-Key` header or a valid `Authorization: Bearer` JWT, treating both as equivalent professional-scoped identities.

#### Scenario: Authenticate via API key only
- **GIVEN** a request to `/turnos/*` with a valid `X-API-Key` header and no `Authorization` header
- **WHEN** the request is processed
- **THEN** the professional is resolved by API key (active only) and the request proceeds

#### Scenario: Authenticate via JWT only (unchanged)
- **GIVEN** a request to `/turnos/*` with a valid Bearer JWT and no `X-API-Key` header
- **WHEN** the request is processed
- **THEN** the professional is resolved by JWT exactly as before this change

#### Scenario: Both headers present and valid
- **GIVEN** a request with both a valid `X-API-Key` and a valid Bearer JWT
- **WHEN** the request is processed
- **THEN** `X-API-Key` takes precedence and its resolved professional is used, even if the JWT resolves to a different professional

#### Scenario: X-API-Key present but invalid, valid JWT also present
- **GIVEN** a request with an invalid/unknown `X-API-Key` and a valid Bearer JWT
- **WHEN** the request is processed
- **THEN** the system falls through and authenticates using the JWT (OR semantics: any one valid scheme is sufficient)

#### Scenario: Neither credential valid
- **GIVEN** a request with no auth headers, or with an invalid `X-API-Key` and no/invalid Bearer JWT
- **WHEN** the request is processed
- **THEN** the system responds `401 Unauthorized` with a single generic message
- **AND** the message does not reveal which scheme(s) were attempted or why they failed

#### Scenario: Inactive professional under either scheme
- **GIVEN** a request whose `X-API-Key` or JWT resolves to a professional with `is_active=False`
- **WHEN** the request is processed
- **THEN** the system responds `401 Unauthorized`, regardless of which scheme was used

### Requirement: Flexible auth scope is limited to turno endpoints

The system MUST apply the flexible dependency (`X-API-Key` OR Bearer JWT) only to the 7 `/turnos/*` endpoints in this change. Other professional-scoped routers MUST retain their current, unmodified auth dependency.

#### Scenario: Non-turno endpoint is unaffected
- **GIVEN** a request to a non-`/turnos/*` professional endpoint (e.g. `/pacientes/*`, `/lista-espera/*`) carrying only an `X-API-Key` header
- **WHEN** the request is processed
- **THEN** the endpoint's existing dependency (JWT-only, unless already API-key-based) applies unchanged — the flexible dependency is not used

### Requirement: Tenant isolation preserved under dual auth

The system MUST ensure both auth schemes resolve to exactly one `Profesional.id`, with no cross-tenant data access introduced by accepting the additional scheme.

#### Scenario: Professional-scoped queries use the resolved id
- **GIVEN** a `/turnos/*` request authenticated via either scheme
- **WHEN** turno data is queried or written
- **THEN** all operations are scoped to the single `profesional.id` returned by the flexible dependency, identical to JWT-only scoping today
