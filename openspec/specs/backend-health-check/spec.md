## ADDED Requirements

### Requirement: Health endpoint returns 200 OK
The system SHALL expose an HTTP GET endpoint at `/health` that returns HTTP 200 OK with a JSON payload containing at least `status`, `version`, and `timestamp` fields.

#### Scenario: Health check on running backend
- **WHEN** a client sends `GET /health` to the running FastAPI application
- **THEN** the response status code SHALL be `200`
- **AND** the response body SHALL contain a JSON object with `status` equal to `"ok"`
- **AND** the response body SHALL contain `version` as a non-empty string
- **AND** the response body SHALL contain `timestamp` as a valid ISO 8601 string

#### Scenario: Health check response time
- **WHEN** a client sends `GET /health` to the running FastAPI application
- **THEN** the response SHALL be returned within 1 second
