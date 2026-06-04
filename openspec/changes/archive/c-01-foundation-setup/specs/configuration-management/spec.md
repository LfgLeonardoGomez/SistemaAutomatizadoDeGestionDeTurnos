## ADDED Requirements

### Requirement: Required environment variables are validated at startup
The system SHALL validate all required environment variables at application startup using Pydantic Settings. If a required variable is missing or invalid, the application SHALL fail to start with a clear error message indicating which variable is missing.

#### Scenario: Startup with all required variables
- **WHEN** the backend starts with all required environment variables present and valid
- **THEN** the application SHALL start successfully
- **AND** the settings object SHALL be accessible via dependency injection

#### Scenario: Startup with missing required variable
- **WHEN** the backend starts without the `DATABASE_URL` environment variable
- **THEN** the application SHALL raise a `ValidationError` during startup
- **AND** the error message SHALL indicate that `DATABASE_URL` is missing

#### Scenario: Startup with optional variables using defaults
- **WHEN** the backend starts without optional variables such as `RESERVA_TEMPORAL_MINUTOS`
- **THEN** the application SHALL start successfully
- **AND** the variable SHALL use its documented default value (e.g., `10`)
