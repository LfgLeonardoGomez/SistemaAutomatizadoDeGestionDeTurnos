# C-19 Super-admin Role — Delta Specs

> This change introduces three new capabilities. Each capability is detailed in its own file under `specs/`. This document provides a consolidated view.

## Capabilities

1. `super-admin-auth`: model, login, JWT role claim, `require_super_admin` dependency.
2. `super-admin-professional-management`: list, get, activate, deactivate professionals.
3. `super-admin-global-metrics`: aggregate operational metrics across all professionals.

---

## Domain: super-admin-auth

### Requirement: SuperAdmin data model
The system SHALL store super-admins in a dedicated `super_admin` table, isolated from `profesional`.

#### Scenario: Table structure
- **GIVEN** the database migration runs
- **THEN** a `super_admin` table exists with columns `id` (PK), `email` (unique), `password_hash`, and `creado_en`
- **AND** no column references `profesional_id`

#### Scenario: Unique email constraint
- **GIVEN** a SuperAdmin with email `admin@example.com` exists
- **WHEN** another SuperAdmin with the same email is inserted
- **THEN** the database raises a unique constraint violation

### Requirement: Super-admin login issues a JWT
The system SHALL expose `POST /admin/auth/login` that returns a JWT for valid credentials.

#### Scenario: Successful login
- **GIVEN** a SuperAdmin exists with a bcrypt password hash
- **WHEN** a client sends the correct email and password
- **THEN** the system returns `200 OK` with `access_token` and `token_type: bearer`

#### Scenario: Invalid credentials
- **GIVEN** a SuperAdmin exists
- **WHEN** a client sends an incorrect password or unknown email
- **THEN** the system returns `401 Unauthorized` with no token

### Requirement: Super-admin JWT contains a role claim
The system SHALL encode `role: "super_admin"` in super-admin access tokens.

#### Scenario: Token payload
- **GIVEN** a successful super-admin login
- **WHEN** the token is decoded
- **THEN** it contains `sub` (super_admin id), `email`, `role: "super_admin"`, `iat`, and `exp`

### Requirement: require_super_admin dependency rejects non-admin tokens
The system SHALL provide `require_super_admin` that validates Bearer tokens and rejects professional or missing tokens.

#### Scenario: Valid super-admin token
- **GIVEN** a request with a valid super-admin JWT
- **WHEN** `require_super_admin` runs
- **THEN** it returns the SuperAdmin record

#### Scenario: Professional JWT rejected
- **GIVEN** a request with a valid `Profesional` JWT
- **WHEN** `require_super_admin` runs
- **THEN** it returns `403 Forbidden`

#### Scenario: Missing or invalid token
- **GIVEN** a request without a token or with an expired/malformed token
- **WHEN** `require_super_admin` runs
- **THEN** it returns `401 Unauthorized`

### Requirement: Super-admin password hashing
The system SHALL hash super-admin passwords with bcrypt using the same `CryptContext` used for professionals.

#### Scenario: Hash verification
- **GIVEN** a stored bcrypt hash
- **WHEN** the correct plain password is verified
- **THEN** verification succeeds; incorrect passwords fail

### Requirement: Bootstrap super-admin from environment
The system SHALL create an initial SuperAdmin from `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD_HASH` during migration/seed.

#### Scenario: Seed creates one admin
- **GIVEN** the environment variables are set
- **WHEN** the migration or seed runs
- **THEN** exactly one SuperAdmin exists with the configured email

---

## Domain: super-admin-professional-management

### Requirement: List all professionals
The system SHALL expose `GET /admin/profesionales` returning all professionals paginated.

#### Scenario: Successful list
- **GIVEN** multiple professionals exist
- **WHEN** an authenticated super-admin sends `GET /admin/profesionales`
- **THEN** the system returns `200 OK` with a list of `ProfesionalAdminResponse` items

#### Scenario: Pagination
- **GIVEN** more professionals than the page size
- **WHEN** the super-admin requests `?skip=0&limit=10`
- **THEN** the system returns at most 10 items

#### Scenario: Unauthenticated request
- **GIVEN** no valid super-admin token
- **WHEN** a client sends `GET /admin/profesionales`
- **THEN** the system returns `401 Unauthorized` or `403 Forbidden`

### Requirement: Get a single professional
The system SHALL expose `GET /admin/profesionales/{id}` returning one professional.

#### Scenario: Existing professional
- **GIVEN** a professional with `id=5` exists
- **WHEN** an authenticated super-admin sends `GET /admin/profesionales/5`
- **THEN** the system returns `200 OK` with the professional details

#### Scenario: Not found
- **GIVEN** no professional with `id=999` exists
- **WHEN** an authenticated super-admin sends `GET /admin/profesionales/999`
- **THEN** the system returns `404 Not Found`

### Requirement: Activate a professional
The system SHALL expose `PUT /admin/profesionales/{id}/activar` setting `is_active=True`.

#### Scenario: Successful activation
- **GIVEN** a deactivated professional with `id=5`
- **WHEN** an authenticated super-admin sends `PUT /admin/profesionales/5/activar`
- **THEN** the system sets `is_active=True` and returns `200 OK`

#### Scenario: Idempotent activation
- **GIVEN** a professional with `is_active=True`
- **WHEN** an authenticated super-admin sends the activate request
- **THEN** the system returns `200 OK` with no error

### Requirement: Deactivate a professional
The system SHALL expose `PUT /admin/profesionales/{id}/desactivar` setting `is_active=False` without deleting data.

#### Scenario: Successful deactivation
- **GIVEN** an active professional with `id=5` and related turnos and pacientes
- **WHEN** an authenticated super-admin sends `PUT /admin/profesionales/5/desactivar`
- **THEN** the system sets `is_active=False` and returns `200 OK`
- **AND** all professional-owned turnos and pacientes remain in the database

#### Scenario: Deactivated professional cannot log in
- **GIVEN** a deactivated professional
- **WHEN** the professional calls `/auth/login`
- **THEN** the system returns `401 Unauthorized`

### Requirement: No relationship between SuperAdmin and Profesional
The system SHALL ensure a super-admin is never treated as a professional.

#### Scenario: Separate tables
- **GIVEN** a SuperAdmin exists
- **WHEN** any professional-scoped query runs
- **THEN** the SuperAdmin record is not included

---

## Domain: super-admin-global-metrics

### Requirement: Global metrics endpoint
The system SHALL expose `GET /admin/metricas` returning aggregate counts and ratios across all professionals.

#### Scenario: Successful retrieval
- **GIVEN** professionals, turnos, and pacientes exist
- **WHEN** an authenticated super-admin sends `GET /admin/metricas`
- **THEN** the system returns `200 OK` with the exact metrics defined below

#### Scenario: Empty system
- **GIVEN** no professionals exist
- **WHEN** an authenticated super-admin sends `GET /admin/metricas`
- **THEN** the system returns `200 OK` with all counts zero and ratios `0.0`

#### Scenario: Unauthorized access
- **GIVEN** no valid super-admin token
- **WHEN** a client sends `GET /admin/metricas`
- **THEN** the system returns `401 Unauthorized` or `403 Forbidden`

### Requirement: Exact metric definitions
The system SHALL compute the following fields on each request:

| Field | Definition |
|-------|------------|
| `total_profesionales` | Count of all `Profesional` records |
| `profesionales_activos` | Count of `Profesional` with `is_active=True` |
| `profesionales_inactivos` | Count of `Profesional` with `is_active=False` |
| `total_turnos` | Count of all `Turno` records |
| `turnos_hoy` | Count of `Turno` with `fecha = current UTC date` |
| `turnos_confirmados_30d` | Count of `Turno` with `estado="CONFIRMADO"` and `creado_en` within last 30 days |
| `turnos_cancelados_30d` | Count of `Turno` with `estado="CANCELADO"` and `creado_en` within last 30 days |
| `total_pacientes` | Count of all `Paciente` records |
| `tasa_confirmacion_30d` | `turnos_confirmados_30d / total_turnos_30d`; `0.0` if denominator is zero |
| `tasa_cancelacion_30d` | `turnos_cancelados_30d / total_turnos_30d`; `0.0` if denominator is zero |

> **Note**: `total_turnos_30d` = count of `Turno` with `creado_en` within last 30 days.

### Requirement: Metrics response uses a typed model
The system SHALL declare a Pydantic v2 response model for `GET /admin/metricas`.

#### Scenario: Response serialization
- **GIVEN** the metrics endpoint returns data
- **WHEN** FastAPI serializes the response
- **THEN** all numeric fields match their declared types and no extra fields leak

---

## Test Deferral Note

Tests for all three capabilities are deferred until the v2.0 backend work is complete, per project decision. This spec documents the deferral and does not include test scenarios.
