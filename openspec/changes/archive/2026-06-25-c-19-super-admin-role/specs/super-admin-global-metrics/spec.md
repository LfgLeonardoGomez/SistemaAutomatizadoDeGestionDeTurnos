# Super-admin Global Metrics

## Purpose

Provide SaaS operators with aggregate operational metrics across all professionals.

## Requirements

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

> **Test deferral note**: Tests for this capability are deferred until the v2.0 backend work is complete, per project decision.
