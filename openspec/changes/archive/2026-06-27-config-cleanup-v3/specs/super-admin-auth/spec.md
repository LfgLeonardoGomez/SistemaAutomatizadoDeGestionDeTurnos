## MODIFIED Requirements

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
