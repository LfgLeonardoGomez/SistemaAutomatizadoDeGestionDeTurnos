import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.profesional import Profesional
from app.models.super_admin import SuperAdmin
from app.seed import seed_profesional, seed_super_admin
from app.services.auth_service import verify_password


class TestSeedProfesional:
    """Tests for seed idempotency — Task 3.1/3.3."""

    @pytest.mark.asyncio
    async def test_seed_creates_profesional_when_empty(self, db_session):
        """Scenario: Seed crea profesional si no existe — 3.1."""
        result = await db_session.execute(select(func.count()).select_from(Profesional))
        count_before = result.scalar_one()
        assert count_before == 0

        settings = Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            secret_key="dummy",
            seed_default_password="changeme",
        )
        await seed_profesional(db_session, settings)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(Profesional))
        count_after = result.scalar_one()
        assert count_after == 1

        result = await db_session.execute(select(Profesional))
        profesional = result.scalar_one()
        assert profesional.nombre == "Dr. Por Defecto"
        assert profesional.especialidad == "Odontología general"
        assert profesional.duracion_turno == 30
        assert profesional.horario_inicio == "08:00"
        assert profesional.horario_fin == "18:00"
        assert profesional.dias_atencion == [
            "Lunes", "Martes", "Miércoles", "Jueves", "Viernes"
        ]
        assert profesional.email == "admin@local.dev"
        assert profesional.password_hash is not None
        assert profesional.password_hash.startswith("$2b$")
        assert profesional.is_active is True

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, db_session):
        """Scenario: Seed no duplica registros — 3.3."""
        settings = Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            secret_key="dummy",
            seed_default_password="changeme",
        )
        await seed_profesional(db_session, settings)
        await db_session.commit()

        await seed_profesional(db_session, settings)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(Profesional))
        count = result.scalar_one()
        assert count == 1


class TestSeedSuperAdmin:
    """Tests for super-admin bootstrap (config-cleanup-v3, task 4.1-4.2)."""

    def _settings(self, email: str = "admin@local.dev", password: str = "secret123") -> Settings:
        return Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            secret_key="testsecret",
            super_admin_email=email,
            super_admin_password=password,
        )

    @pytest.mark.asyncio
    async def test_seed_creates_super_admin_with_hashed_password(self, db_session):
        """Spec: seed creates one admin with hashed password.

        Scenario: SUPER_ADMIN_EMAIL + SUPER_ADMIN_PASSWORD set -> exactly
        one SuperAdmin exists, password_hash is a valid bcrypt hash of the
        plain-text password.
        """
        settings = self._settings(password="super-secret-123")
        await seed_super_admin(db_session, settings)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(SuperAdmin))
        assert result.scalar_one() == 1

        result = await db_session.execute(select(SuperAdmin))
        admin = result.scalar_one()
        assert admin.email == "admin@local.dev"
        assert admin.password_hash.startswith("$2b$"), (
            "password_hash MUST be a bcrypt hash, not the raw plain-text password. "
            "The seed must call pwd_context.hash() / hash_password() internally."
        )
        # The stored hash must verify against the original plain-text password.
        assert verify_password("super-secret-123", admin.password_hash)

    @pytest.mark.asyncio
    async def test_seed_super_admin_is_idempotent(self, db_session):
        """Edge case: running the seed twice does NOT create a second admin."""
        settings = self._settings()
        await seed_super_admin(db_session, settings)
        await db_session.commit()
        await seed_super_admin(db_session, settings)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(SuperAdmin))
        assert result.scalar_one() == 1

    @pytest.mark.asyncio
    async def test_seed_skips_when_password_empty(self, db_session):
        """Spec: seed skips when password is empty or absent.

        Scenario: SUPER_ADMIN_EMAIL is set but SUPER_ADMIN_PASSWORD is empty
        -> no SuperAdmin is created.
        """
        settings = self._settings(password="")
        await seed_super_admin(db_session, settings)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(SuperAdmin))
        assert result.scalar_one() == 0

    @pytest.mark.asyncio
    async def test_seed_skips_when_email_empty(self, db_session):
        """Edge case: SUPER_ADMIN_EMAIL empty -> no SuperAdmin is created."""
        settings = self._settings(email="", password="irrelevant")
        await seed_super_admin(db_session, settings)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(SuperAdmin))
        assert result.scalar_one() == 0
