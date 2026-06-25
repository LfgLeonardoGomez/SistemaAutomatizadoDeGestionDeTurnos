# Super-admin Professional Management

## Purpose

Allow a SaaS operator to list, inspect, activate, and deactivate professionals without participating in professional-scoped flows.

## Requirements

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

> **Test deferral note**: Tests for this capability are deferred until the v2.0 backend work is complete, per project decision.
