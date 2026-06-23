import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.profesional import Profesional


class TestProfesionalModel:
    """Tests for Profesional model — Task 1.3."""

    @pytest.mark.asyncio
    async def test_profesional_creation(self, db_session):
        """Scenario: Crear profesional con datos básicos."""
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología general",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            email="dr.test@local.dev",
            password_hash="$2b$12$dummyhash",
            is_active=True,
        )
        db_session.add(profesional)
        await db_session.commit()
        await db_session.refresh(profesional)

        assert profesional.id is not None
        assert profesional.nombre == "Dr. Test"
        assert profesional.especialidad == "Odontología general"
        assert profesional.duracion_turno == 30
        assert profesional.horario_inicio == "08:00"
        assert profesional.horario_fin == "18:00"
        assert profesional.dias_atencion == ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        assert profesional.creado_en is not None
        assert profesional.email == "dr.test@local.dev"
        assert profesional.password_hash == "$2b$12$dummyhash"
        assert profesional.is_active is True

    @pytest.mark.asyncio
    async def test_profesional_query_by_nombre(self, db_session):
        """Scenario: Triangulate — query profesional by nombre."""
        profesional = Profesional(
            nombre="Dr. García",
            especialidad="Cardiología",
            duracion_turno=45,
            horario_inicio="09:00",
            horario_fin="17:00",
            dias_atencion=["Lunes", "Miércoles"],
            email="dr.garcia@local.dev",
            password_hash="$2b$12$dummyhash",
            is_active=True,
        )
        db_session.add(profesional)
        await db_session.commit()

        result = await db_session.execute(
            select(Profesional).where(Profesional.nombre == "Dr. García")
        )
        db_profesional = result.scalar_one()
        assert db_profesional.duracion_turno == 45

    @pytest.mark.asyncio
    async def test_profesional_email_unique(self, db_session):
        """Scenario: Email único por profesional."""
        p1 = Profesional(
            nombre="Dr. A",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="same@local.dev",
            password_hash="hash1",
            is_active=True,
        )
        db_session.add(p1)
        await db_session.commit()

        p2 = Profesional(
            nombre="Dr. B",
            especialidad="Y",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="same@local.dev",
            password_hash="hash2",
            is_active=True,
        )
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_profesional_api_key_unique(self, db_session):
        """Scenario: API key única por profesional."""
        p1 = Profesional(
            nombre="Dr. A",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="a@local.dev",
            password_hash="hash1",
            api_key="key-123",
            is_active=True,
        )
        db_session.add(p1)
        await db_session.commit()

        p2 = Profesional(
            nombre="Dr. B",
            especialidad="Y",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="b@local.dev",
            password_hash="hash2",
            api_key="key-123",
            is_active=True,
        )
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_profesional_new_columns_nullable(self, db_session):
        """Scenario: Nuevas columnas aceptan nulos salvo is_active."""
        profesional = Profesional(
            nombre="Dr. Minimal",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.commit()
        await db_session.refresh(profesional)

        assert profesional.email is None
        assert profesional.password_hash is None
        assert profesional.api_key is None
        assert profesional.google_refresh_token is None
        assert profesional.telegram_bot_token is None
        assert profesional.telegram_secret_token is None
        assert profesional.is_active is True  # default

    @pytest.mark.asyncio
    async def test_profesional_is_active_false(self, db_session):
        """Scenario: Profesional inactivo."""
        profesional = Profesional(
            nombre="Dr. Inactivo",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            is_active=False,
        )
        db_session.add(profesional)
        await db_session.commit()
        await db_session.refresh(profesional)

        assert profesional.is_active is False
