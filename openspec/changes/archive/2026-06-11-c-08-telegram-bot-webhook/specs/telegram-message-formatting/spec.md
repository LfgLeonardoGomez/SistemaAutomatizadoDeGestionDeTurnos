## ADDED Requirements

### Requirement: Messages are formatted with valid Markdown
The system SHALL format all outgoing Telegram messages using Telegram MarkdownV2 parse mode, ensuring valid syntax.

#### Scenario: Availability list formatted with Markdown
- **WHEN** the system sends a list of available dates or hours
- **THEN** the message uses bold, bullet points, and properly escaped MarkdownV2 characters

#### Scenario: Error message formatted with Markdown
- **WHEN** the system sends an error message to the user
- **THEN** the message is formatted with MarkdownV2 and includes escaped special characters

### Requirement: InlineKeyboardMarkup is built for interactive selection
The system SHALL construct `InlineKeyboardMarkup` with buttons for date selection, time selection, confirmation, and cancellation.

#### Scenario: Date selection keyboard
- **WHEN** the system presents available dates
- **THEN** each date is represented as an inline button with `callback_data` in the format `fecha:YYYY-MM-DD`

#### Scenario: Time selection keyboard
- **WHEN** the system presents available hours for a selected date
- **THEN** each hour is represented as an inline button with `callback_data` in the format `hora:HH:MM`

#### Scenario: Confirmation keyboard
- **WHEN** the system asks the user to confirm patient data
- **THEN** the keyboard includes "Confirmar" and "Cancelar" buttons with `callback_data` `confirmar_datos` and `cancelar_accion`

### Requirement: Messages are split if they exceed 4096 characters
The system SHALL split any outgoing message that exceeds 4096 characters into multiple consecutive messages.

#### Scenario: Long availability list
- **WHEN** the availability list exceeds 4096 characters
- **THEN** the system sends the message as two or more parts, each under 4096 characters

#### Scenario: Short message remains intact
- **WHEN** the message is 4096 characters or fewer
- **THEN** the system sends a single message
