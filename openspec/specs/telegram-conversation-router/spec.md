## ADDED Requirements

### Requirement: Conversational router parses text and callback queries
The system SHALL parse incoming `message` text and `callback_query` data from Telegram updates and route them to the correct business action.

#### Scenario: Text message routing to show availability
- **WHEN** the user sends the text "Quiero un turno" or "/start"
- **THEN** the system invokes the action to display available dates

#### Scenario: Callback query routing for date selection
- **WHEN** the user presses an inline button with `callback_data` matching the pattern `fecha:YYYY-MM-DD`
- **THEN** the system invokes the action to display available hours for that date

#### Scenario: Callback query routing for time selection
- **WHEN** the user presses an inline button with `callback_data` matching the pattern `hora:HH:MM`
- **THEN** the system invokes the action to create a temporary reservation

#### Scenario: Unrecognized text in idle state
- **WHEN** the user sends text that does not match any known command and the conversation state is `idle`
- **THEN** the system replies with a help menu listing available commands

### Requirement: Conversation state is maintained per chat
The system SHALL maintain a conversation state for each `chat_id` in an in-memory dictionary.

#### Scenario: State transitions during reservation flow
- **WHEN** the user completes a step in the reservation flow
- **THEN** the system updates the conversation state to reflect the next expected input

#### Scenario: State reset on cancel
- **WHEN** the user presses the "Cancelar" button or sends "Cancelar"
- **THEN** the system resets the conversation state to `idle` and frees any temporary reservation

### Requirement: Router handles cancel and reschedule commands
The system SHALL route "Cancelar" and "Reprogramar" text or callback queries to the appropriate business actions.

#### Scenario: Cancel command routes to cancel action
- **WHEN** the user sends "Cancelar" or presses a cancel inline button
- **THEN** the system routes to the cancel action and clears the conversation state

#### Scenario: Reschedule command routes to reschedule action
- **WHEN** the user sends "Reprogramar" or presses a reschedule inline button
- **THEN** the system routes to the reschedule action, reusing the availability flow

### Requirement: Router handles reminder inline buttons as placeholder
The system SHALL parse and route inline button presses from reminder messages to the correct actions.

#### Scenario: Confirm reminder button
- **WHEN** the user presses a "Confirmar" button on a reminder message with `callback_data` `reminder:confirmar:<turno_id>`
- **THEN** the system routes to the confirmation action

#### Scenario: Cancel reminder button
- **WHEN** the user presses a "Cancelar" button on a reminder message with `callback_data` `reminder:cancelar:<turno_id>`
- **THEN** the system routes to the cancel action

#### Scenario: Reschedule reminder button
- **WHEN** the user presses a "Reprogramar" button on a reminder message with `callback_data` `reminder:reprogramar:<turno_id>`
- **THEN** the system routes to the reschedule action
