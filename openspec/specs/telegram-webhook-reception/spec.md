## ADDED Requirements

### Requirement: Webhook endpoint receives and validates Telegram updates
The system SHALL expose a `POST /webhooks/telegram` endpoint that receives Telegram Bot API updates and validates their authenticity.

#### Scenario: Valid update with secret token
- **WHEN** Telegram sends an `Update` JSON payload to `POST /webhooks/telegram` with a valid `X-Telegram-Bot-Api-Secret-Token` header
- **THEN** the system accepts the update and passes it to the conversational router

#### Scenario: Invalid secret token
- **WHEN** a request arrives at `POST /webhooks/telegram` with an invalid or missing `X-Telegram-Bot-Api-Secret-Token` header
- **THEN** the system returns HTTP 403 and discards the payload

#### Scenario: Malformed update payload
- **WHEN** a request arrives at `POST /webhooks/telegram` with a body that cannot be parsed as a Telegram `Update` object
- **THEN** the system returns HTTP 400 and discards the payload

### Requirement: Webhook endpoint is non-blocking and returns immediately
The system SHALL respond to the webhook request immediately without waiting for the conversational processing to complete.

#### Scenario: Fast acknowledgment on valid update
- **WHEN** a valid update is received
- **THEN** the system returns HTTP 200 before executing the conversational action
