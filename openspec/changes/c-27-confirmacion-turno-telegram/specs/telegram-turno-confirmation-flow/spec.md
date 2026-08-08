# Telegram Turno Confirmation Flow Specification

## Purpose

Carry a turno from `RESERVADO_TEMPORAL` to `CONFIRMADO` over Telegram by collecting the patient identity that `PUT /turnos/{id}/confirmar` requires, asking only for what is not already on record.

Today the flow stops after `POST /turnos`, so the reservation expires after `reserva_temporal_minutos` and the slot silently returns to the pool. No turno has ever reached `CONFIRMADO`.

**Non-goals**: sending email (no mail sender exists in the backend); resolving the professional per request (the bot still authenticates with a single static credential); altering the required fields of `ConfirmarTurnoRequest`; changing the duration of the reservation window.

## ADDED Requirements

### Requirement: Identity capture begins with the DNI

After a slot is reserved, the system MUST ask for the patient's DNI before asking for anything else, and MUST use it to determine which further questions are necessary.

#### Scenario: DNI is requested once the slot is reserved

- **WHEN** `POST /turnos` returns a turno in `RESERVADO_TEMPORAL`
- **THEN** the bot asks the user for the patient's DNI and asks for no other field yet

#### Scenario: A malformed DNI is rejected without losing the reservation

- **WHEN** the user replies with a value that is not a plausible DNI
- **THEN** the bot says so and asks again, keeping the reserved `turno_id` so the reservation is not abandoned

### Requirement: A known patient is confirmed without further questions

When the DNI already belongs to a patient of the professional, the system MUST confirm the turno using the stored data and MUST NOT ask the user to retype it.

#### Scenario: Returning patient

- **WHEN** the DNI lookup resolves to an existing patient
- **THEN** the bot calls `PUT /turnos/{id}/confirmar` with that patient's `nombre`, `apellido`, `dni` and `telefono`, and asks the user nothing further

#### Scenario: Returning patient sees the confirmation

- **WHEN** the confirmation for a returning patient succeeds
- **THEN** the bot reports the turno as confirmed, including the patient name, the date and the time

### Requirement: A new patient is asked only for the missing fields

When the DNI resolves to no patient, the system MUST collect the remaining required fields and MUST group them so that the exchange stays within three questions in total.

#### Scenario: New patient supplies name and surname

- **WHEN** the DNI lookup returns no patient
- **THEN** the bot asks for name and surname in a single question

#### Scenario: New patient supplies contact details

- **WHEN** name and surname have been captured for a new patient
- **THEN** the bot asks for the phone number and, optionally, an email in a single question

#### Scenario: New patient is confirmed

- **WHEN** all required fields have been captured for a new patient
- **THEN** the bot calls `PUT /turnos/{id}/confirmar` with the captured data and reports the confirmed turno

### Requirement: The turno reaches CONFIRMADO and the slot is held

The system MUST drive the turno to `CONFIRMADO` through `PUT /turnos/{id}/confirmar`, so the reservation is consumed rather than released.

#### Scenario: Confirmation persists the state transition

- **WHEN** confirmation succeeds for a reserved turno
- **THEN** the turno's state is `CONFIRMADO`, it carries a `paciente_id`, and its `ReservaTemporal` row no longer exists

#### Scenario: The slot is no longer offered

- **WHEN** a turno has been confirmed for a given date and time
- **THEN** that slot is absent from a subsequent availability query for the same date

### Requirement: An expired reservation is reported, not swallowed

The reservation window can close while the user is still answering. The system MUST detect that and tell the user, rather than failing silently or presenting the turno as confirmed.

#### Scenario: Reservation expires mid-conversation

- **WHEN** `PUT /turnos/{id}/confirmar` responds `409` because the reservation expired
- **THEN** the bot tells the user the reservation expired and invites them to start the booking again

#### Scenario: Confirmation is rejected for a business reason

- **WHEN** confirmation is rejected because the patient already holds an active turno
- **THEN** the bot reports that reason to the user instead of a generic failure

### Requirement: A recognised command interrupts a pending capture

A user who abandons a booking mid-question MUST NOT be trapped by it. When a recognised command arrives while the system is waiting for an answer, the system MUST execute the command and discard the pending capture.

#### Scenario: A command wins over a pending question

- **WHEN** the user issues `/cancelar`, `/reprogramar` or starts a new booking while a capture question is pending
- **THEN** the command is executed and the pending capture is discarded, so the next message is no longer read as an answer

#### Scenario: Ordinary routing is unaffected when nothing is pending

- **WHEN** no capture is pending
- **THEN** messages are routed exactly as they were before this change, including the time, slot-number and date inputs

### Requirement: An abandoned capture stops claiming later messages

A capture that is never answered MUST stop being treated as pending once the reservation window has closed, so an unrelated message sent later is not consumed as an answer.

#### Scenario: A later message is not read as an answer

- **WHEN** the user stops replying and the reservation window closes
- **THEN** a subsequent unrelated message is not treated as an answer to the abandoned question

### Requirement: Notification recipients are registered on confirmation

The system MUST register the Telegram chat as a notification recipient on every confirmation, and MUST register an email recipient when an email was supplied.

#### Scenario: Telegram recipient is always registered

- **WHEN** a turno is confirmed through this flow
- **THEN** the confirmation payload carries the `telegram_chat_id`, and the turno gains a recipient on channel `TELEGRAM`

#### Scenario: Email is stored when supplied

- **WHEN** the user supplied an email for a new patient
- **THEN** the confirmation payload carries it and the turno gains a recipient on channel `EMAIL` in addition to `TELEGRAM`

#### Scenario: Email delivery is not promised

- **WHEN** the bot confirms a turno for which an email was supplied
- **THEN** the message announces the reminder on Telegram only, and does not state that a reminder will be sent by email
