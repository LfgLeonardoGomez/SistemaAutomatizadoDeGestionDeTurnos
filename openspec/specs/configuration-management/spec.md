# Spec: configuration-management

## Purpose
Define how the application manages its runtime configuration: which environment variables are required, which are optional, and the validation contract for startup.
## Requirements
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

#### Scenario: Startup without deprecated variables
- **GIVEN** `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, and `GOOGLE_CALENDAR_ID` are absent
- **WHEN** the backend starts
- **THEN** the application SHALL start successfully
- **AND** `Settings` SHALL NOT expose those attributes

### Requirement: N8N_WEBHOOK_URL is not declared in Pydantic Settings
The system SHALL NOT declare `N8N_WEBHOOK_URL` in Pydantic Settings.

#### Scenario: Startup without N8N_WEBHOOK_URL
- **GIVEN** `N8N_WEBHOOK_URL` is absent from the environment
- **WHEN** the backend starts
- **THEN** the application SHALL start successfully
- **AND** `Settings` SHALL NOT expose an `n8n_webhook_url` attribute

### Requirement: TELEGRAM_WEBHOOK_SECRET is not declared in Pydantic Settings
The system SHALL NOT declare `TELEGRAM_WEBHOOK_SECRET` in Pydantic Settings.

#### Scenario: Startup without TELEGRAM_WEBHOOK_SECRET
- **GIVEN** `TELEGRAM_WEBHOOK_SECRET` is absent from the environment
- **WHEN** the backend starts
- **THEN** the application SHALL start successfully
- **AND** `Settings` SHALL NOT expose a `telegram_webhook_secret` attribute

### Requirement: Single canonical .env.example at repository root
The system SHALL maintain exactly one `.env.example` file at the repository root. The file SHALL contain every environment variable declared in `backend/app/config.py`, with descriptive comments and sensible defaults.

#### Scenario: .env.example completeness
- **WHEN** an operator inspects `.env.example` at the repository root
- **THEN** it SHALL contain all variables names declared in `config.py`
- **AND** it SHALL NOT contain variables absent from `config.py`
- **AND** there SHALL be no `.env.example` inside `backend/`

### Requirement: docker-compose.yml injects all critical backend variables
The `docker-compose.yml` service `backend` SHALL declare every environment variable required by `backend/app/config.py` in its `environment` block, either with a direct value or with a `${VAR:-default}` fallback where applicable.

#### Scenario: docker-compose backend environment completeness
- **WHEN** inspecting the `backend` service definition in `docker-compose.yml`
- **THEN** it SHALL declare `DATABASE_URL`, `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_CALENDAR_MAX_RETRIES`, `GOOGLE_CALENDAR_BASE_DELAY`, `GOOGLE_CALENDAR_MAX_DELAY`, `RESERVA_TEMPORAL_MINUTOS`, `LISTA_ESPERA_MINUTOS`, `RECORDATORIO_HORAS_ANTES`, `RECORDATORIO_JOB_INTERVAL_MINUTOS`, `COMPLETADO_JOB_INTERVAL_MINUTOS`, `ENV`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `SEED_DEFAULT_PASSWORD`, `SUPER_ADMIN_EMAIL`, and `SUPER_ADMIN_PASSWORD`

### Requirement: SQLite artifacts are excluded from version control
The repository SHALL NOT contain `*.db` files. The `.gitignore` SHALL exclude them.

#### Scenario: No SQLite database in repository
- **WHEN** listing tracked files matching `*.db`
- **THEN** the result SHALL be empty
- **AND** `.gitignore` SHALL contain `*.db`

