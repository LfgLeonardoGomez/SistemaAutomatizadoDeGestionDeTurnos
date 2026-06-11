import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models for autogenerate support
from app.models.base import Base

# Ensure all models are imported so they register with Base.metadata
from app.models import paciente, profesional, turno, reserva_temporal, lista_de_espera

target_metadata = Base.metadata


def get_database_url() -> str:
    """Return a sync PostgreSQL URL from the DATABASE_URL env var.

    Alembic runs migrations synchronously, so any +asyncpg driver
    must be stripped to a standard postgresql:// URL.
    """
    raw_url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    if raw_url and "+asyncpg" in raw_url:
        return raw_url.replace("+asyncpg", "+psycopg", 1)
    return raw_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_database_url()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
