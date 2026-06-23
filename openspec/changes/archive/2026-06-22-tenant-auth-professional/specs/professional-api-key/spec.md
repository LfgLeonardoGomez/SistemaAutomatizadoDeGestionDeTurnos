## ADDED Requirements

### Requirement: Profesional can generate an API key
The system SHALL allow an authenticated professional to generate a secure random API key for machine-to-machine integrations.

#### Scenario: Successful API key generation
- **WHEN** an authenticated professional sends a POST request to `/auth/api-key`
- **THEN** the system generates a new random API key (e.g., `secrets.token_urlsafe(32)`)
- **AND** stores it in `Profesional.api_key`
- **AND** returns the plaintext key in the response body exactly once

#### Scenario: Regeneration overwrites previous key
- **WHEN** a professional already has an API key and generates a new one
- **THEN** the old key is invalidated (overwritten in the database)
- **AND** only the new key works for subsequent requests

### Requirement: System validates API key on integration endpoints
The system SHALL provide a reusable dependency `get_profesional_by_api_key` that validates an API key passed via HTTP header and loads the active professional.

#### Scenario: Valid API key
- **WHEN** a request includes a valid `X-API-Key` header (or configured header name)
- **THEN** `get_profesional_by_api_key` finds the professional by that key and `is_active=True`
- **AND** returns the Profesional instance

#### Scenario: Invalid or missing API key
- **WHEN** a request includes an invalid or missing API key
- **THEN** `get_profesional_by_api_key` raises a 401 Unauthorized HTTPException

#### Scenario: API key belongs to inactive professional
- **WHEN** a request includes a valid API key but the professional has `is_active=False`
- **THEN** `get_profesional_by_api_key` raises a 401 Unauthorized HTTPException

### Requirement: API key is not retrievable after generation
The system SHALL not include the API key in any read response after its initial generation.

#### Scenario: Reading professional data
- **WHEN** any endpoint returns professional data (e.g., `/profesional/configuracion`)
- **THEN** the response does not contain the `api_key` field
