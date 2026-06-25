## MODIFIED Requirements

### Requirement: Webhook endpoint receives and validates Telegram updates
The system SHALL expose a `POST /webhooks/telegram` endpoint that receives Telegram Bot API updates and validates their authenticity **ruteando al profesional correspondiente**.

#### Scenario: Valid update with secret token de profesional
- **WHEN** Telegram sends an `Update` JSON payload to `POST /webhooks/telegram` with a valid `X-Telegram-Bot-Api-Secret-Token` header que coincida con `telegram_secret_token` de un profesional activo
- **THEN** the system acepta el update
- **AND** identifica al profesional asociado
- **AND** pasa el update al conversational router con el `profesional_id`

#### Scenario: Invalid secret token
- **WHEN** a request arrives at `POST /webhooks/telegram` with an `X-Telegram-Bot-Api-Secret-Token` that does not match any profesional
- **THEN** the system returns HTTP 403 and discards the payload

#### Scenario: Missing secret token
- **WHEN** a request arrives at `POST /webhooks/telegram` without `X-Telegram-Bot-Api-Secret-Token`
- **THEN** the system returns HTTP 403 and discards the payload

#### Scenario: Malformed update payload
- **WHEN** a request arrives at `POST /webhooks/telegram` with a body that cannot be parsed as a Telegram `Update` object
- **THEN** the system returns HTTP 400 and discards the payload

### Requirement: Webhook endpoint is non-blocking and returns immediately
The system SHALL respond to the webhook request immediately without waiting for the conversational processing to complete, después de validar el secret token y identificar al profesional.

#### Scenario: Fast acknowledgment on valid update
- **WHEN** a valid update is received para un profesional identificado
- **THEN** the system returns HTTP 200 before executing the conversational action
- **AND** el procesamiento continúa en background con el `profesional_id` correcto
