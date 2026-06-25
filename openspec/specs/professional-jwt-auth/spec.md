# Professional JWT Authentication

## Purpose

Authenticate professionals using JWT (JSON Web Token) Bearer tokens. Provides registration, login, and a reusable dependency for protecting endpoints.

## Requirements

### Requirement: Profesional can log in
The system SHALL authenticate a professional by verifying email and bcrypt password hash, and return a JWT access token.

#### Scenario: Successful login
- **WHEN** a client sends a POST request to `/auth/login` with a valid email and password
- **THEN** the system verifies the bcrypt hash
- **AND** returns a 200 response containing a JWT access token with claims `sub`, `email`, and `exp`

#### Scenario: Login with invalid password
- **WHEN** a client sends a POST request to `/auth/login` with a valid email but wrong password
- **THEN** the system returns a 401 Unauthorized response

#### Scenario: Login with non-existent email
- **WHEN** a client sends a POST request to `/auth/login` with an email not registered
- **THEN** the system returns a 401 Unauthorized response

### Requirement: System validates JWT on protected endpoints
The system SHALL provide a reusable dependency `get_current_profesional` that validates Bearer JWT tokens and loads the active professional from the database.

#### Scenario: Valid token for active professional
- **WHEN** a request includes a valid Bearer JWT in the Authorization header
- **THEN** `get_current_profesional` decodes the token, extracts `sub` as professional_id
- **AND** queries the database for a professional with `is_active=True`
- **AND** returns the Profesional instance to the endpoint

#### Scenario: Expired or malformed token
- **WHEN** a request includes an expired or malformed JWT
- **THEN** `get_current_profesional` raises a 401 Unauthorized HTTPException

#### Scenario: Token for inactive or deleted professional
- **WHEN** a request includes a valid JWT but the professional does not exist or `is_active=False`
- **THEN** `get_current_profesional` raises a 401 Unauthorized HTTPException

### Requirement: System never exposes password hash in responses
The system SHALL ensure that no response model includes the `password_hash` field.

#### Scenario: Any auth response
- **WHEN** any auth endpoint returns a response
- **THEN** the response body does not contain `password_hash`
