# Multichannel Reminder Delivery Specification

## Purpose

Deliver a turno reminder over every channel the patient has agreed to, through one fan-out that both reminder engines share, so that adding a channel does not mean adding a call site.

Before this change the backend had exactly one sender, and it did not iterate: it took the first `TELEGRAM` recipient of the turno and ignored the rest. An `EMAIL` recipient was stored and never read.

**Non-goals**: email for notifications other than the turno reminder; action links or buttons inside the email; HTML bodies; bounce handling or an outbound queue.

## ADDED Requirements

### Requirement: Reminders are sent over every eligible recipient of the turno

The system SHALL send the reminder to **all** recipients of the turno that are marked for notification and not already delivered, dispatching each to the sender of its channel. The system SHALL NOT stop at the first recipient, and SHALL NOT restrict delivery to the `TELEGRAM` channel.

#### Scenario: A turno with two channels is delivered on both

- **WHEN** a turno due for a reminder has a `TELEGRAM` recipient and an `EMAIL` recipient, both marked for notification
- **THEN** a Telegram message is sent to the `TELEGRAM` recipient
- **AND** an email is sent to the `EMAIL` recipient

#### Scenario: A turno with only an email recipient is still reminded

- **WHEN** a turno due for a reminder has an `EMAIL` recipient and no `TELEGRAM` recipient
- **THEN** an email is sent
- **AND** no Telegram delivery is attempted

#### Scenario: A muted channel is not delivered

- **WHEN** a turno has a `TELEGRAM` and an `EMAIL` recipient, and the `EMAIL` recipient is not marked for notification
- **THEN** only the Telegram message is sent

#### Scenario: A turno with no eligible recipient is not retried forever

- **WHEN** a turno due for a reminder has no recipient marked for notification on any channel
- **THEN** the system logs a warning naming the turno and reports success, so the turno is marked as reminded and not retried

### Requirement: Each recipient records its own delivery

The system SHALL record the delivery timestamp on the recipient that was delivered, and SHALL skip any recipient that already carries one. The turno SHALL be marked as reminded only when every eligible recipient has been delivered.

#### Scenario: A failing channel does not re-send a succeeding one

- **GIVEN** a turno with a `TELEGRAM` and an `EMAIL` recipient
- **WHEN** the Telegram delivery succeeds and the email delivery fails
- **THEN** the `TELEGRAM` recipient carries a delivery timestamp and the `EMAIL` recipient does not
- **AND** the turno is NOT marked as reminded

#### Scenario: The retry sends only what failed

- **GIVEN** the previous scenario's turno
- **WHEN** the reminder job runs again
- **THEN** the email delivery is attempted again
- **AND** no second Telegram message is sent

#### Scenario: The turno is marked as reminded once every channel is delivered

- **WHEN** every eligible recipient of a turno has been delivered
- **THEN** the turno is marked as reminded and no further delivery is attempted for it

### Requirement: The fan-out reports one retry decision to its callers

The system SHALL expose the fan-out with the same success contract as the existing Telegram sender: a boolean where success means "this turno needs no retry" and failure means "retry on the next run". Both reminder engines — the APScheduler job and the `POST /api/v1/recordatorios/run` endpoint — SHALL obtain their reminder delivery through this fan-out rather than calling a channel sender directly.

#### Scenario: Both engines use the same fan-out

- **WHEN** the reminder is triggered by the scheduler job, or by the recordatorios endpoint
- **THEN** the same fan-out performs the delivery and applies the same channel selection

#### Scenario: A failed delivery leaves the turno retryable

- **WHEN** every attempted delivery for a turno fails
- **THEN** the fan-out reports failure, the turno is NOT marked as reminded, and the reminder is retried on the next run

#### Scenario: A professional without a Telegram bot token still sends email

- **WHEN** a professional has no Telegram bot token and one of their turnos has an `EMAIL` recipient
- **THEN** the email reminder is sent
- **AND** the professional is not skipped as a whole

### Requirement: Email reminders are sent over SMTP without blocking the event loop

The system SHALL send email through an SMTP transport configured by environment variables, and SHALL execute the blocking SMTP call outside the event loop so that the scheduler is not stalled by a slow or unreachable relay. The SMTP call SHALL use an explicit timeout.

#### Scenario: A successful send reports success

- **WHEN** the SMTP relay accepts the message
- **THEN** the email sender reports success and the recipient is stamped as delivered

#### Scenario: A relay failure is retryable

- **WHEN** the SMTP relay refuses the connection, rejects the credentials, or returns an error for the message
- **THEN** the email sender logs the failure with the turno and the host, reports failure, and the recipient is left without a delivery timestamp

#### Scenario: The failure log does not disclose the credentials

- **WHEN** an SMTP failure is logged
- **THEN** the log line contains no SMTP password

### Requirement: An unconfigured SMTP relay is skipped, not retried

When no SMTP host is configured, the system SHALL log a warning, skip the email recipient permanently, and continue delivering the turno's other channels. The system SHALL NOT report an unconfigured relay as a retryable failure.

#### Scenario: No SMTP host configured

- **WHEN** a turno with an `EMAIL` recipient is due for a reminder and no SMTP host is configured
- **THEN** a warning naming the turno is logged
- **AND** the email recipient is stamped as delivered without any delivery attempt
- **AND** the reminder is not retried on that account

#### Scenario: The Telegram channel is unaffected

- **WHEN** the same turno also has a `TELEGRAM` recipient
- **THEN** the Telegram reminder is sent normally and the turno is marked as reminded

### Requirement: The email carries the same facts as the Telegram reminder

The system SHALL build a plain-text email with a subject and a body stating the patient's name, the date, the time of the turno, and the professional. The body SHALL direct the patient to the Telegram bot to cancel or reschedule, since email carries no action buttons.

#### Scenario: Body content

- **WHEN** a reminder email is built for a turno
- **THEN** the body states the patient name, the date, the start time and the professional
- **AND** it tells the patient how to cancel or reschedule

#### Scenario: The email is plain text

- **WHEN** a reminder email is built
- **THEN** it is sent as plain text and carries no Telegram-specific markup

### Requirement: SMTP configuration is environment-driven and optional at startup

The system SHALL read the SMTP host, port, user, password, sender address, TLS mode and timeout from Pydantic Settings, and SHALL start successfully when none of them is set. The system SHALL NOT hardcode any SMTP value and SHALL NOT commit the SMTP password.

#### Scenario: Startup without SMTP variables

- **WHEN** the backend starts with no `SMTP_*` variables present
- **THEN** the application starts successfully and the SMTP host defaults to empty

#### Scenario: The password is not in the repository

- **WHEN** the repository is inspected
- **THEN** `.env.example` documents the `SMTP_*` variable names without any real credential
