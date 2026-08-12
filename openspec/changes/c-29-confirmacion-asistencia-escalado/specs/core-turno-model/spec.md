# core-turno-model — delta for c-29-confirmacion-asistencia-escalado

Adds the three timestamps that carry the attendance-escalation walk. None of them is a state: `turno.estado` and `turno_estado_enum` are untouched, and nothing the professional sees changes.

## ADDED Requirements

### Requirement: Turno records when the patient confirmed attendance

The system SHALL store on `Turno` a nullable timestamp `asistencia_confirmada_en` holding the instant the patient answered `confirmar` to the reminder. `NULL` SHALL mean "the patient has not answered". The column SHALL NOT be part of `turno_estado_enum` and SHALL NOT change how `estado` is computed, queried or displayed.

#### Scenario: A turno starts with no confirmation recorded

- **WHEN** a `Turno` is created
- **THEN** `asistencia_confirmada_en` is `NULL`

#### Scenario: The column is a timestamp, not a flag

- **WHEN** the patient's confirmation is recorded
- **THEN** `asistencia_confirmada_en` holds the instant of the answer, so an elapsed window can be computed from it

#### Scenario: The state machine is unaffected

- **WHEN** `asistencia_confirmada_en` is written on a `CONFIRMADO` turno
- **THEN** `estado` remains `CONFIRMADO` and `turno_estado_enum` gains no value

### Requirement: Turno records when the first reminder was sent

The system SHALL store on `Turno` a nullable timestamp `recordatorio_enviado_en` holding the instant the first attendance reminder left the system, alongside the existing boolean `recordatorio_enviado`, which SHALL keep its current type and meaning. The timestamp SHALL be written in the same transaction that sets the boolean.

#### Scenario: Sending the first reminder stamps the instant

- **WHEN** the reminder job marks a turno as reminded
- **THEN** `recordatorio_enviado` is `TRUE` and `recordatorio_enviado_en` holds the instant of that send

#### Scenario: The existing boolean keeps its contract

- **WHEN** the reminder job selects candidates
- **THEN** it filters on `recordatorio_enviado = FALSE` exactly as before, and its behaviour is unchanged by the new column

#### Scenario: Turnos reminded before the column existed carry no instant

- **GIVEN** a turno whose reminder was sent before this change was deployed
- **WHEN** its row is read
- **THEN** `recordatorio_enviado` is `TRUE` and `recordatorio_enviado_en` is `NULL`

### Requirement: Turno records when the final warning was sent

The system SHALL store on `Turno` a nullable timestamp `segundo_aviso_enviado_en` holding the instant the final warning left the system. `NULL` SHALL mean "no final warning has been sent".

#### Scenario: A turno starts with no final warning recorded

- **WHEN** a `Turno` is created
- **THEN** `segundo_aviso_enviado_en` is `NULL`

#### Scenario: The stamp is written once

- **GIVEN** a turno whose `segundo_aviso_enviado_en` is already set
- **WHEN** the escalation runs again
- **THEN** the existing value is preserved and no second warning is sent

### Requirement: Attendance timestamps are stored on the UTC clock

The system SHALL persist `asistencia_confirmada_en`, `recordatorio_enviado_en` and `segundo_aviso_enviado_en` as naive UTC, consistent with `creado_en` and `reserva_temporal.expiracion`, and SHALL NOT store them in local time. Any comparison between one of these timestamps and an agenda column (`fecha`, `hora_inicio`, `hora_fin`) SHALL convert the timestamp to local time first.

#### Scenario: Durations are computed without conversion

- **WHEN** the elapsed time since `recordatorio_enviado_en` is computed
- **THEN** it is compared against the current instant on the UTC clock, with no timezone conversion applied

#### Scenario: Comparison against the appointment converts first

- **WHEN** one of these timestamps is compared against the turno's start time built from `fecha` and `hora_inicio`
- **THEN** the timestamp is converted to local time before the comparison
