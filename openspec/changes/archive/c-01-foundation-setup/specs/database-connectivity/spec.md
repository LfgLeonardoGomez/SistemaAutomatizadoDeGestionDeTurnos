## ADDED Requirements

### Requirement: Backend connects to PostgreSQL via async SQLAlchemy
The system SHALL be able to establish a connection to PostgreSQL using SQLAlchemy 2.0 async engine (`create_async_engine`). Alembic SHALL be initialized and configured to use the same database.

#### Scenario: Database engine initialization
- **WHEN** the backend application initializes the database engine using `create_async_engine` with the `DATABASE_URL`
- **THEN** the engine SHALL be created without errors
- **AND** the engine SHALL use the `postgresql+asyncpg` dialect when the URL indicates async mode

#### Scenario: Alembic configuration exists
- **WHEN** inspecting the `backend/alembic/` directory
- **THEN** `alembic.ini` SHALL exist and reference the correct database URL or an environment-driven configuration
- **AND** `env.py` SHALL be configured to create a sync SQLAlchemy engine for migrations
- **AND** running `alembic current` from the `backend/` directory SHALL execute without unhandled exceptions
