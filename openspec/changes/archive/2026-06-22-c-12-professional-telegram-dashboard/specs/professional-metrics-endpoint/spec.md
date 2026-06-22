## ADDED Requirements

### Requirement: Metrics endpoint returns calculated summary
The system SHALL expose `GET /profesional/metricas` that returns computed metrics based on turno data.

#### Scenario: Successful metrics retrieval
- **WHEN** a client sends `GET /profesional/metricas`
- **THEN** the system returns `200 OK` with a JSON payload containing:
  - `turnos_hoy` (int): count of `CONFIRMADO` appointments for the current day
  - `tasa_confirmacion_30d` (float): ratio of `CONFIRMADO` to total created appointments in the last 30 days
  - `tasa_cancelacion_30d` (float): ratio of `CANCELADO` to total created appointments in the last 30 days

#### Scenario: Metrics with zero data
- **WHEN** a client sends `GET /profesional/metricas` and there are no turnos in the last 30 days
- **THEN** the system returns `200 OK` with all metric values set to zero

#### Scenario: Metrics endpoint uses response_model
- **WHEN** the backend handles `GET /profesional/metricas`
- **THEN** the endpoint declares a Pydantic v2 `response_model`
- **AND** the return type annotation matches the response model

### Requirement: Metrics endpoint returns typed response
The system SHALL declare strict type hints and a Pydantic v2 response model for the metrics endpoint.

#### Scenario: Metrics response model validation
- **WHEN** the metrics data is serialized
- **THEN** all numeric fields are validated as their declared types (int, float)
- **AND** no extra fields leak into the response
