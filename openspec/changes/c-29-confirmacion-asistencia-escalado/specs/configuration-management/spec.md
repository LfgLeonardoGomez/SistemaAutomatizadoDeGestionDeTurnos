# configuration-management — delta for c-29-confirmacion-asistencia-escalado

Four new optional variables. All are declared in Pydantic Settings with defaults, so a deployment that sets none of them still starts — and, because the switch defaults to disabled, still cancels nothing.

## ADDED Requirements

### Requirement: Attendance escalation intervals are declared in Settings

The system SHALL declare `ASISTENCIA_ESPERA_HORAS` (default `2`), `ASISTENCIA_GRACIA_HORAS` (default `1`) and `ASISTENCIA_JOB_INTERVAL_MINUTOS` (default `5`) in Pydantic Settings as optional integers, and SHALL NOT read any of these values from a constant in application code.

#### Scenario: Startup without the escalation variables

- **WHEN** the backend starts with none of the escalation variables present
- **THEN** the application starts successfully and each setting holds its documented default

#### Scenario: Values are overridable from the environment

- **WHEN** the backend starts with `ASISTENCIA_ESPERA_HORAS` set to a different value
- **THEN** the settings object exposes that value

#### Scenario: An invalid value fails at startup

- **WHEN** the backend starts with `ASISTENCIA_ESPERA_HORAS` set to a non-integer
- **THEN** the application raises a validation error during startup naming that variable

### Requirement: The attendance escalation has an environment-backed switch

The system SHALL declare `ASISTENCIA_ESCALADO_HABILITADO` in Pydantic Settings as an optional boolean defaulting to `false`, so that the escalation is inert until it is deliberately enabled and can be disabled again without a code change.

#### Scenario: Startup without the switch

- **WHEN** the backend starts without `ASISTENCIA_ESCALADO_HABILITADO` present
- **THEN** the application starts successfully and the setting is `false`

#### Scenario: The switch is readable by the job

- **WHEN** `ASISTENCIA_ESCALADO_HABILITADO` is set to `true`
- **THEN** the settings object exposes `true` and the escalation job acts on it

### Requirement: The new variables are documented where the existing ones are

The system SHALL document the four new variables, with their defaults and their units, in the same places the existing optional variables are documented, so an operator can discover them without reading the source.

#### Scenario: The variables are discoverable

- **WHEN** an operator reads the project's environment documentation and the compose definition
- **THEN** the four new variables appear there with their defaults, alongside `RECORDATORIO_HORAS_ANTES` and `COMPLETADO_JOB_INTERVAL_MINUTOS`
