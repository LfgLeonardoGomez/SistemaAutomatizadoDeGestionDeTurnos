## ADDED Requirements

### Requirement: Professional can view today's confirmed appointments via Telegram
The system SHALL respond to the `/turnos_hoy` command by listing all `CONFIRMADO` appointments for the current day, including start time and patient name.

#### Scenario: Professional requests today's appointments
- **WHEN** the professional sends `/turnos_hoy`
- **THEN** the system replies with a MarkdownV2 formatted list of confirmed appointments for today
- **AND** each line shows the start time and patient full name

#### Scenario: No confirmed appointments today
- **WHEN** the professional sends `/turnos_hoy` and there are no `CONFIRMADO` appointments for the current day
- **THEN** the system replies with a message indicating there are no appointments today

#### Scenario: Long appointment list exceeds Telegram message limit
- **WHEN** the professional sends `/turnos_hoy` and the formatted message exceeds 4096 characters
- **THEN** the system splits the message into multiple chunks under 4096 characters
- **AND** sends each chunk sequentially

### Requirement: Professional can view basic metrics via Telegram
The system SHALL respond to the `/metricas` command with a summary of basic agenda metrics.

#### Scenario: Professional requests metrics
- **WHEN** the professional sends `/metricas`
- **THEN** the system replies with:
  - Total confirmed appointments for today
  - Confirmation rate over the last 30 days (confirmed / total created)
  - Cancellation/no-show rate over the last 30 days (cancelled / total created)

#### Scenario: No historical data for metrics
- **WHEN** the professional sends `/metricas` and there is no turno data
- **THEN** the system replies with zero values for all metrics

### Requirement: Professional can configure agenda via Telegram wizard
The system SHALL guide the professional through a step-by-step conversational wizard when `/configurar` is sent, allowing modification of `horario_inicio`, `horario_fin`, `dias_atencion`, and `duracion_turno`.

#### Scenario: Initiate configuration wizard
- **WHEN** the professional sends `/configurar`
- **THEN** the system prompts for the new start time (e.g., "Ingresá el horario de inicio en formato HH:MM")
- **AND** sets the conversation state to `config_esperando_hora_inicio`

#### Scenario: Enter start time
- **WHEN** the professional enters a valid time in HH:MM format while in state `config_esperando_hora_inicio`
- **THEN** the system stores the value and prompts for the end time
- **AND** transitions state to `config_esperando_hora_fin`

#### Scenario: Invalid start time
- **WHEN** the professional enters an invalid time while in state `config_esperando_hora_inicio`
- **THEN** the system replies with an error message and repeats the prompt

#### Scenario: Enter end time
- **WHEN** the professional enters a valid end time in HH:MM format while in state `config_esperando_hora_fin`
- **THEN** the system validates that end time is after start time
- **AND** if valid, prompts for working days using inline toggle buttons
- **AND** transitions state to `config_esperando_dias`

#### Scenario: End time before start time
- **WHEN** the professional enters an end time that is not after the start time
- **THEN** the system replies with an error message and repeats the end time prompt

#### Scenario: Select working days via inline buttons
- **WHEN** the professional is in state `config_esperando_dias`
- **THEN** the system displays 7 inline buttons (one per weekday) and a "Confirmar días" button
- **AND** pressing a weekday toggles its selection
- **AND** pressing "Confirmar días" stores the selected days and prompts for duration
- **AND** transitions state to `config_esperando_duracion`

#### Scenario: Enter duration
- **WHEN** the professional enters a positive integer (minutes) while in state `config_esperando_duracion`
- **THEN** the system stores the duration and displays a summary of all changes
- **AND** transitions state to `config_confirmar`

#### Scenario: Confirm configuration changes
- **WHEN** the professional confirms the summary while in state `config_confirmar`
- **THEN** the system calls the existing `PUT /profesional/configuracion` logic to persist changes
- **AND** replies with a success message
- **AND** resets conversation state to `idle`

#### Scenario: Cancel configuration at any step
- **WHEN** the professional presses a "Cancelar" inline button or sends "Cancelar" at any step of the wizard
- **THEN** the system discards any pending configuration changes
- **AND** resets conversation state to `idle`
- **AND** replies with a cancellation message

### Requirement: Telegram message formatting respects limits
The system SHALL format all professional dashboard messages using MarkdownV2 and respect Telegram's 4096 character limit per message.

#### Scenario: Metrics message formatting
- **WHEN** the system generates the `/metricas` response
- **THEN** the message uses MarkdownV2 for bold labels and escaped values
- **AND** the total length does not exceed 4096 characters

#### Scenario: Turnos hoy message formatting
- **WHEN** the system generates the `/turnos_hoy` response
- **THEN** the message uses MarkdownV2 for headers and escaped patient names
- **AND** the total length does not exceed 4096 characters
