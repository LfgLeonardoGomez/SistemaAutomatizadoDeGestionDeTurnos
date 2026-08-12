# Turno Attendance Confirmation Specification

## Purpose

Record that the patient answered the attendance reminder, so that the answer has consequences: a patient who confirmed is thanked, is never chased with a second warning, and is never auto-cancelled.

Before this change the answer went nowhere. `confirmar_asistencia_turno` validated ownership and state and returned the turno unchanged, so a patient who confirmed was indistinguishable from one who ignored the message — which is exactly the distinction the escalation depends on.

**Non-goals**: changing `turno.estado` or anything the professional sees; introducing a new state; redesigning the `cancelar` / `reprogramar` sub-flows, which the patient may answer instead and which already work.

## ADDED Requirements

### Requirement: Confirming attendance records the answer without changing the state

The system SHALL record the patient's `confirmar` answer by writing the current instant into `asistencia_confirmada_en`, and SHALL leave `turno.estado` as `CONFIRMADO`. The professional's view of the turno SHALL NOT change.

#### Scenario: The answer is sealed

- **WHEN** the patient confirms attendance for a `CONFIRMADO` turno
- **THEN** `asistencia_confirmada_en` holds the instant of the answer

#### Scenario: The state is untouched

- **WHEN** the patient confirms attendance
- **THEN** `estado` is still `CONFIRMADO` after the answer, exactly as it was before

#### Scenario: The answer survives the request that wrote it

- **WHEN** the confirmation is committed and the turno is read back in a later session
- **THEN** `asistencia_confirmada_en` is still set, because the escalation job runs much later and in a different session

### Requirement: Confirming attendance is idempotent and keeps the first answer

Telegram redelivers updates and the patient can tap the button more than once. The system SHALL preserve the **first** recorded instant and SHALL NOT overwrite it on subsequent confirmations, because overwriting would push the escalation window forward on every tap.

#### Scenario: A second tap changes nothing

- **GIVEN** a turno whose attendance has already been confirmed
- **WHEN** the patient confirms again
- **THEN** `asistencia_confirmada_en` still holds the instant of the first answer

#### Scenario: A repeated confirmation is not an error

- **WHEN** the patient confirms an already-confirmed turno
- **THEN** the operation succeeds and the patient is thanked, rather than being shown a failure

### Requirement: Confirming attendance keeps its ownership and state guards

The system SHALL reject an attendance confirmation for a turno that does not exist, that belongs to another professional, or that is not in `CONFIRMADO`, and SHALL leave `asistencia_confirmada_en` untouched in every rejected case.

#### Scenario: Unknown turno

- **WHEN** attendance is confirmed for a turno id that does not exist
- **THEN** the request is rejected with `404` and nothing is written

#### Scenario: Turno of another professional

- **WHEN** professional B confirms attendance for a turno belonging to professional A
- **THEN** the request is rejected with `404`, disclosing nothing about A's turno

#### Scenario: Turno that is not confirmed

- **WHEN** attendance is confirmed for a turno that is `CANCELADO`, `COMPLETADO` or `RESERVADO_TEMPORAL`
- **THEN** the request is rejected with `409` and `asistencia_confirmada_en` remains `NULL`

### Requirement: The confirmation reaches the patient as a message, never as silence

The Telegram flow SHALL call the attendance-confirmation endpoint before replying to the patient, and SHALL turn every outcome — success, unknown turno, turno no longer valid, and any other failure — into a message addressed to the patient.

#### Scenario: A successful confirmation is acknowledged

- **WHEN** the endpoint returns success for the patient's tap
- **THEN** the bot thanks the patient

#### Scenario: A rejected confirmation is explained

- **WHEN** the endpoint answers `404` or `409`
- **THEN** the bot tells the patient why, instead of leaving the tap unanswered

#### Scenario: A transport failure does not abort the reply

- **WHEN** the endpoint answers with an unexpected status
- **THEN** the bot still replies, asking the patient to try again later

### Requirement: A confirmed turno is excluded from escalation

A turno whose `asistencia_confirmada_en` is not `NULL` SHALL NOT receive a second notice and SHALL NOT be auto-cancelled, regardless of how much time has elapsed since the reminder. This is the reason the column exists.

#### Scenario: A confirming patient is never chased

- **GIVEN** a turno whose attendance was confirmed
- **WHEN** the escalation runs after the wait interval has elapsed
- **THEN** no second notice is sent for that turno

#### Scenario: A confirming patient is never auto-cancelled

- **GIVEN** a turno whose attendance was confirmed
- **WHEN** the escalation runs after the full escalation window has elapsed
- **THEN** the turno is still `CONFIRMADO` and its slot is still held

#### Scenario: Confirming after the final warning stops the escalation

- **GIVEN** a turno that has already received the final warning
- **WHEN** the patient confirms before the grace window closes
- **THEN** the turno is not cancelled
