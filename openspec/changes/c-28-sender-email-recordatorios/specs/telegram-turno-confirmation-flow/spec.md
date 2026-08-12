# telegram-turno-confirmation-flow — Delta (C-28)

> Depends on C-27 being archived: the requirement modified below is introduced by
> `openspec/changes/c-27-confirmacion-turno-telegram/specs/telegram-turno-confirmation-flow/spec.md`
> and does not exist in `openspec/specs/` until that change is archived.

## MODIFIED Requirements

### Requirement: Notification recipients are registered on confirmation

The system MUST register the Telegram chat as a notification recipient on every confirmation, and MUST register an email recipient when an email was supplied. The confirmation message MUST describe the reminder truthfully: it MUST name every channel that will actually carry the reminder, and MUST NOT announce a channel that has no recipient.

#### Scenario: Telegram recipient is always registered

- **WHEN** a turno is confirmed through this flow
- **THEN** the confirmation payload carries the `telegram_chat_id`, and the turno gains a recipient on channel `TELEGRAM`

#### Scenario: Email is stored when supplied

- **WHEN** the user supplied an email for a new patient
- **THEN** the confirmation payload carries it and the turno gains a recipient on channel `EMAIL` in addition to `TELEGRAM`

#### Scenario: Email delivery is announced when an email was supplied

- **WHEN** the bot confirms a turno for which an email was supplied
- **THEN** the message states that the reminder will arrive by Telegram and by email
- **AND** it does not describe email as unavailable

#### Scenario: Only Telegram is announced when no email was supplied

- **WHEN** the bot confirms a turno for which no email was supplied
- **THEN** the message announces the reminder on Telegram only, without offering or implying an email reminder

## ADDED Requirements

### Requirement: The patient chooses which channel carries the reminder

When a turno has more than one notification recipient, the system MUST let the patient choose which of them receives the reminder, and MUST offer that choice on the confirmation message rather than as an additional question inside the reservation window. The choice MUST be expressed through buttons whose payload identifies the turno, so that no conversational state is needed to interpret the answer.

#### Scenario: The choice is offered when an email exists

- **WHEN** a turno is confirmed and it has both a `TELEGRAM` and an `EMAIL` recipient
- **THEN** the confirmation message carries buttons offering Telegram only, email only, or both

#### Scenario: The choice is not offered when it cannot be honoured

- **WHEN** a turno is confirmed with no `EMAIL` recipient
- **THEN** no channel buttons are shown, because the only available channel is already in use

#### Scenario: The choice takes effect

- **WHEN** the patient presses the button for email only
- **THEN** the turno's `EMAIL` recipient is marked for notification and its `TELEGRAM` recipient is not
- **AND** the bot confirms the choice to the patient

#### Scenario: Pressing the same choice twice changes nothing

- **WHEN** the patient presses the same channel button a second time
- **THEN** the resulting notification marks are identical to those after the first press

#### Scenario: No choice means every recipient is used

- **WHEN** the patient never presses any channel button
- **THEN** the reminder is delivered to every recipient the turno has

#### Scenario: Muting Telegram does not remove the turno from the bot

- **WHEN** the patient chooses email only
- **THEN** the turno still appears in the chat's list of manageable turnos and can still be cancelled or rescheduled from Telegram

### Requirement: The channel choice is applied through a dedicated endpoint

The system MUST expose an endpoint that sets which of a turno's recipients are marked for notification, accepting the professional's API key as well as a JWT, declaring its response type, and refusing a request that would leave the turno with no notification channel.

#### Scenario: Setting both channels

- **WHEN** the endpoint is called for a confirmed turno with both channels listed
- **THEN** both recipients are marked for notification and the resulting recipient set is returned

#### Scenario: An empty selection is rejected

- **WHEN** the endpoint is called with no channel listed
- **THEN** the request is rejected as invalid and no recipient is modified

#### Scenario: The endpoint is reachable by the n8n credential

- **WHEN** the endpoint is called with a valid `X-API-Key` and no JWT
- **THEN** the request is accepted and scoped to that professional's turnos

#### Scenario: Another professional's turno is not reachable

- **WHEN** the endpoint is called for a turno belonging to a different professional
- **THEN** the request is rejected and no recipient is modified

#### Scenario: A turno that will never be reminded is refused

- **WHEN** the endpoint is called for a turno that is not `CONFIRMADO`
- **THEN** the request is rejected and no recipient is modified
