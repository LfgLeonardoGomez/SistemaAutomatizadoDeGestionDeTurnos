## ADDED Requirements

### Requirement: Turnos hoy endpoint returns today's confirmed appointments
The system SHALL expose `GET /profesional/turnos-hoy` that returns all `CONFIRMADO` appointments for the current day, including patient details.

#### Scenario: Successful retrieval with appointments
- **WHEN** a client sends `GET /profesional/turnos-hoy`
- **THEN** the system returns `200 OK` with a JSON array of turnos
- **AND** each turno includes `id`, `fecha`, `hora_inicio`, `hora_fin`, `estado`, and nested `paciente` object with `nombre`, `apellido`, `dni`, `telefono`

#### Scenario: Successful retrieval with no appointments
- **WHEN** a client sends `GET /profesional/turnos-hoy` and there are no confirmed appointments today
- **THEN** the system returns `200 OK` with an empty array

#### Scenario: Turnos hoy endpoint uses response_model
- **WHEN** the backend handles `GET /profesional/turnos-hoy`
- **THEN** the endpoint declares a Pydantic v2 `response_model`
- **AND** the return type annotation matches the response model

### Requirement: Turnos hoy endpoint filters by estado CONFIRMADO
The system SHALL query only turnos with `estado = 'CONFIRMADO'` for the current day.

#### Scenario: Exclude non-confirmed appointments
- **WHEN** the system queries turnos for `/profesional/turnos-hoy`
- **THEN** it excludes turnos with estado `DISPONIBLE`, `RESERVADO_TEMPORAL`, `CANCELADO`, or `COMPLETADO`
- **AND** only includes those with `fecha` equal to the current date
