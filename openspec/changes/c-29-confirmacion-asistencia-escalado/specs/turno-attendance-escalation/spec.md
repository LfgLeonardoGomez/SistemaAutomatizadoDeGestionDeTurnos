# Turno Attendance Escalation Specification

## Purpose

Give the reminder consequences when the patient never answers: wait, warn once more that the turno will be cancelled, and then cancel it and return the slot to the pool.

The value of the reminder is not in telling the patient about the turno. It is in **freeing the turno when the patient is not coming**. That half did not exist: ignoring the message cost the patient nothing and cost the professional the hour.

This capability automatically cancels real patients' appointments, so every requirement below that could be written either way is written the way that cancels less.

**Non-goals**: offering the freed slot to the waiting list (deliberately deferred to a separate change); notifying the professional of an automatic cancellation; changing `turno.estado`'s enum; escalating anything other than the attendance reminder.

## ADDED Requirements

### Requirement: The escalation window is configuration, not constants

The system SHALL read the wait before the final warning, the grace period before cancellation, and the job's own interval from environment-backed settings with documented defaults, and SHALL NOT hardcode any of them.

#### Scenario: Defaults apply when nothing is configured

- **WHEN** the backend starts with none of the escalation variables set
- **THEN** it starts successfully using the documented defaults: two hours of wait, one hour of grace, and a five-minute job interval

#### Scenario: A configured value takes effect

- **GIVEN** the wait interval is configured to a different number of hours
- **WHEN** the escalation decides whether a turno is due for its final warning
- **THEN** it uses the configured value, not the default

### Requirement: The escalation never starts when its window does not fit before the turno

The system SHALL NOT escalate a turno unless the **complete** escalation window — the wait plus the grace period, measured from the instant the first reminder was sent — ends at or before the turno's start time. When the window does not fit, the system SHALL send no final warning and SHALL NOT cancel the turno.

This guard SHALL be evaluated against the first reminder's instant, not against the current time, so that its answer cannot change between one run of the job and the next.

#### Scenario: A window that does not fit blocks the whole escalation

- **GIVEN** a turno that starts in less time than the wait plus the grace period, measured from when its reminder was sent
- **WHEN** the escalation runs
- **THEN** no final warning is sent and the turno is not cancelled, no matter how many times the job runs

#### Scenario: A window that fits allows the escalation

- **GIVEN** a turno whose reminder was sent early enough that the wait plus the grace period still ends before the turno starts
- **WHEN** the escalation runs after the wait has elapsed
- **THEN** the final warning is sent

#### Scenario: The guard's answer does not drift between runs

- **GIVEN** a turno that passed the guard and received its final warning
- **WHEN** the escalation runs again later, closer to the turno's start time
- **THEN** the guard still passes and the turno is cancelled, rather than being left warned but never cancelled

#### Scenario: A turno that has already started is never auto-cancelled

- **GIVEN** a turno whose start time has passed
- **WHEN** the escalation runs, for instance after the job was down for several hours
- **THEN** the turno is not cancelled by the escalation

#### Scenario: The guard compares on the same clock

- **WHEN** the guard compares the first reminder's instant against the turno's start time
- **THEN** the reminder's instant is converted to local time first, because the turno's start is stored in local terms

### Requirement: A patient who does not answer receives one final warning

When the configured wait has elapsed since the first reminder and the patient has not answered, the system SHALL send exactly one further message that repeats the reminder and states that the turno will be cancelled if there is no answer within the grace period. The message SHALL offer the same answer options as the first reminder.

#### Scenario: The warning is sent once the wait elapses

- **GIVEN** a turno whose reminder was sent, whose attendance is unconfirmed, and whose window fits
- **WHEN** the wait interval has elapsed
- **THEN** a final warning is sent to the turno's Telegram recipient

#### Scenario: The warning announces the cancellation

- **WHEN** the final warning is sent
- **THEN** its text states that the turno will be cancelled if the patient does not answer within the grace period

#### Scenario: The warning keeps the answer options working

- **WHEN** the final warning is sent
- **THEN** it carries the same confirm, cancel and reschedule options as the first reminder, and answering them has the same effect

#### Scenario: The warning is not sent before the wait elapses

- **GIVEN** a turno whose reminder was sent less than the wait interval ago
- **WHEN** the escalation runs
- **THEN** no final warning is sent

#### Scenario: Sending the warning records its instant

- **WHEN** the final warning is sent successfully
- **THEN** the instant of that send is recorded on the turno

#### Scenario: A failed send is retried rather than recorded

- **WHEN** the final warning fails to send
- **THEN** no instant is recorded and the next run of the escalation attempts the send again

### Requirement: A patient who still does not answer loses the turno

When the grace period has elapsed since the final warning and the patient has still not answered, the system SHALL cancel the turno.

#### Scenario: The turno is cancelled once the grace period elapses

- **GIVEN** a turno that received its final warning and whose attendance is still unconfirmed
- **WHEN** the grace period has elapsed
- **THEN** the turno's state is `CANCELADO`

#### Scenario: The turno is not cancelled before the grace period elapses

- **GIVEN** a turno whose final warning was sent less than the grace period ago
- **WHEN** the escalation runs
- **THEN** the turno is still `CONFIRMADO`

#### Scenario: A turno that never received the final warning is not cancelled

- **GIVEN** a turno with no recorded final warning
- **WHEN** the escalation runs, however long after the first reminder
- **THEN** the turno is not cancelled

#### Scenario: The patient is told the turno was cancelled

- **WHEN** a turno is cancelled by the escalation
- **THEN** the patient's Telegram recipient is sent a message saying the turno was cancelled for lack of an answer, and how to book again

#### Scenario: A failed notification does not undo the cancellation

- **WHEN** the cancellation notice fails to send
- **THEN** the turno stays `CANCELADO` and the failure is logged, because the database is the source of truth

### Requirement: An auto-cancelled slot returns to the pool

The system SHALL make the slot of an auto-cancelled turno available again to any patient, on a first-come basis, and SHALL NOT offer it to the waiting list.

#### Scenario: The slot is offered again

- **WHEN** a turno is cancelled by the escalation
- **THEN** its date and start time appear again in a subsequent availability query for that professional

#### Scenario: The slot can be booked again

- **WHEN** a patient requests the freed slot after the automatic cancellation
- **THEN** the booking succeeds and is not blocked by the cancelled turno

#### Scenario: The waiting list is not consulted

- **WHEN** a turno is cancelled by the escalation
- **THEN** no waiting-list entry is notified or assigned as a result

#### Scenario: The Google Calendar event is removed

- **WHEN** a turno with a Google Calendar event is cancelled by the escalation
- **THEN** the event is deleted on a best-effort basis, and a failure to delete it does not undo the cancellation

#### Scenario: The audit trail survives the cancellation

- **WHEN** a turno is cancelled by the escalation
- **THEN** the row keeps its patient, its recipients, and the recorded instants of the reminder and the final warning, so the reason for the cancellation remains answerable

### Requirement: The escalation is safe to run twice

The system SHALL produce the same outcome whether the escalation runs once or many times over the same turno: no duplicate final warning, and no second cancellation. Each step SHALL require its predecessor to have been recorded and its own record to be absent, and SHALL take a row lock while it decides.

#### Scenario: A second run does not re-warn

- **GIVEN** a turno whose final warning has already been recorded
- **WHEN** the escalation runs again before the grace period elapses
- **THEN** no further warning is sent

#### Scenario: A second run does not re-cancel

- **GIVEN** a turno already cancelled by the escalation
- **WHEN** the escalation runs again
- **THEN** the turno is left untouched and no further notification is sent

#### Scenario: Concurrent runs do not both act

- **WHEN** two runs of the escalation consider the same turno at the same time
- **THEN** they serialise on the turno's row lock, and only the first one acts

#### Scenario: A turno that left CONFIRMADO stops being a candidate

- **GIVEN** a turno whose patient answered `cancelar` or `reprogramar` mid-escalation
- **WHEN** the escalation runs
- **THEN** the turno is not escalated, because every step requires the turno to be `CONFIRMADO`

### Requirement: One failure does not abort the batch

The escalation SHALL process professionals independently and commit per professional, and SHALL contain a failure to the turno or the professional that caused it.

#### Scenario: One patient's failed send does not affect another's

- **WHEN** the final warning fails to send for one turno
- **THEN** the remaining turnos of that professional are still processed

#### Scenario: One professional's failure does not affect another's

- **WHEN** processing one professional raises an unexpected error
- **THEN** the error is logged, that professional's work is rolled back, and the remaining professionals are still processed

#### Scenario: The job never raises

- **WHEN** the escalation job encounters an unexpected error at any level
- **THEN** it logs the error and returns, rather than propagating an exception into the scheduler

### Requirement: The escalation can be switched off without a deployment

The system SHALL expose an environment-backed switch that disables the escalation, SHALL default it to disabled, and SHALL take no action at all while it is off.

#### Scenario: Disabled by default

- **WHEN** the backend starts without the switch set
- **THEN** the escalation job is registered but sends no warning and cancels no turno

#### Scenario: Enabling requires only configuration

- **WHEN** the switch is set and the backend is restarted
- **THEN** the escalation begins acting on candidate turnos, with no code change required

#### Scenario: Disabling stops the escalation immediately

- **GIVEN** the escalation is running
- **WHEN** the switch is unset and the backend is restarted
- **THEN** no further warnings are sent and no further turnos are cancelled

### Requirement: Turnos reminded before this capability existed are never escalated

A turno whose first reminder has no recorded instant SHALL NOT be escalated, because the elapsed window cannot be computed for it.

#### Scenario: An unstamped reminder does not escalate

- **GIVEN** a turno marked as reminded but with no recorded reminder instant
- **WHEN** the escalation runs
- **THEN** no final warning is sent and the turno is not cancelled

#### Scenario: New reminders escalate normally

- **WHEN** a reminder is sent after this capability is deployed
- **THEN** its instant is recorded and the turno becomes a normal escalation candidate
