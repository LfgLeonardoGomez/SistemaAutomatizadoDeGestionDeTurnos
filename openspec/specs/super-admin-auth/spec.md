# Super-admin Authentication

## Purpose

Authenticate SaaS operators (`SuperAdmin`) separately from `Profesional` users using email/password and a role-bearing JWT.
## Requirements
### Requirement: SuperAdmin data model
The system SHALL store super-admins in a dedicated `super_admin` table, isolated from `profesional`.

#### Scenario: Table structure
- **GIVEN** the database migration runs
- **THEN** a `super_admin` table exists with columns `id` (PK), `email` (unique), `password_hash`, and `creado_en`
- **AND** no column references `profesional_id`

#### Scenario: Unique email constraint
- **GIVEN** a SuperAdmin with email `admin@example.com` exists
- **WHEN** another SuperAdmin with the same email is inserted
- **THEN** the database raises a unique constraint violation

### Requirement: Super-admin login issues a JWT
The system SHALL expose `POST /admin/auth/login` that returns a JWT for valid credentials.

#### Scenario: Successful login
- **GIVEN** a SuperAdmin exists with a bcrypt password hash
- **WHEN** a client sends the correct email and password
- **THEN** the system returns `200 OK` with `access_token` and `token_type: bearer`

#### Scenario: Invalid credentials
- **GIVEN** a SuperAdmin exists
- **WHEN** a client sends an incorrect password or unknown email
- **THEN** the system returns `401 Unauthorized` with no token

### Requirement: Super-admin JWT contains a role claim
The system SHALL encode `role: "super_admin"` in super-admin access tokens.

#### Scenario: Token payload
- **GIVEN** a successful super-admin login
- **WHEN** the token is decoded
- **THEN** it contains `sub` (super_admin id), `email`, `role: "super_admin"`, `iat`, and `exp`

### Requirement: require_super_admin dependency rejects non-admin tokens
The system SHALL provide `require_super_admin` that validates Bearer tokens and rejects professional or missing tokens.

#### Scenario: Valid super-admin token
- **GIVEN** a request with a valid super-admin JWT
- **WHEN** `require_super_admin` runs
- **THEN** it returns the SuperAdmin record

#### Scenario: Professional JWT rejected
- **GIVEN** a request with a valid `Profesional` JWT
- **WHEN** `require_super_admin` runs
- **THEN** it returns `403 Forbidden`

#### Scenario: Missing or invalid token
- **GIVEN** a request without a token or with an expired/malformed token
- **WHEN** `require_super_admin` runs
- **THEN** it returns `401 Unauthorized`

### Requirement: Super-admin password hashing
The system SHALL hash super-admin passwords with bcrypt using the same `CryptContext` used for professionals.

#### Scenario: Hash verification
- **GIVEN** a stored bcrypt hash
- **WHEN** the correct plain password is verified
- **THEN** verification succeeds; incorrect passwords fail

### Requirement: Bootstrap super-admin from environment
The system SHALL create an initial SuperAdmin from `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` during migration/seed. The system SHALL hash the plain-text password with bcrypt before persisting it.

#### Scenario: Seed creates one admin with hashed password
- **GIVEN** the environment variables `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` are set
- **WHEN** the migration or seed runs
- **THEN** exactly one SuperAdmin exists with the configured email
- **AND** the stored `password_hash` is a valid bcrypt hash of the configured password

#### Scenario: Seed skips when password is empty
- **GIVEN** `SUPER_ADMIN_EMAIL` is set but `SUPER_ADMIN_PASSWORD` is empty or absent
- **WHEN** the migration or seed runs
- **THEN** no SuperAdmin is created

#### Scenario: Login succeeds with seeded plaintext password
- **GIVEN** a SuperAdmin was seeded from `SUPER_ADMIN_PASSWORD=secret123`
- **WHEN** the client sends `POST /admin/auth/login` with the same email and password
- **THEN** the system returns `200 OK` with an `access_token`

