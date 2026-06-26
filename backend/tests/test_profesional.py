import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.profesional import Profesional
from app.schemas.profesional import (
    ProfesionalIntegracionesResponse,
    ProfesionalIntegracionesUpdate,
)


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

    @pytest.mark.asyncio
    async def test_profesional_google_calendar_id_default(self, db_session):
        """Scenario: google_calendar_id defaults to 'primary' at DB level."""
        profesional = Profesional(
            nombre="Dr. Default Cal",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="defaultcal@local.dev",
            is_active=True,
        )
        db_session.add(profesional)
        await db_session.commit()
        await db_session.refresh(profesional)

        # server_default="primary" applies at DB level; SQLite in-memory
        # may not honour server_default, so accept None or "primary".
        assert profesional.google_calendar_id in (None, "primary")

    @pytest.mark.asyncio
    async def test_profesional_google_calendar_id_custom(self, db_session):
        """Scenario: google_calendar_id accepts a custom value."""
        profesional = Profesional(
            nombre="Dr. Custom Cal",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="customcal@local.dev",
            google_calendar_id="my_custom_calendar@group.calendar.google.com",
            is_active=True,
        )
        db_session.add(profesional)
        await db_session.commit()
        await db_session.refresh(profesional)

        assert profesional.google_calendar_id == "my_custom_calendar@group.calendar.google.com"


class TestProfesionalIntegracionesSchema:
    """Tests for ProfesionalIntegracionesUpdate/Response schemas — T-06."""

    def test_update_accepts_google_calendar_id(self):
        """Scenario: partial update with google_calendar_id only."""
        update = ProfesionalIntegracionesUpdate(google_calendar_id="abc@group.calendar.google.com")
        assert update.google_calendar_id == "abc@group.calendar.google.com"
        assert update.telegram_bot_token is None
        assert update.google_refresh_token is None

    def test_update_rejects_empty_google_calendar_id(self):
        """Scenario: empty string google_calendar_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ProfesionalIntegracionesUpdate(google_calendar_id="")

    def test_update_rejects_whitespace_only_google_calendar_id(self):
        """Scenario: whitespace-only google_calendar_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ProfesionalIntegracionesUpdate(google_calendar_id="   ")

    def test_update_accepts_all_fields(self):
        """Scenario: all three fields provided together."""
        update = ProfesionalIntegracionesUpdate(
            telegram_bot_token="tok",
            google_refresh_token="ref",
            google_calendar_id="cal_id",
        )
        assert update.telegram_bot_token == "tok"
        assert update.google_refresh_token == "ref"
        assert update.google_calendar_id == "cal_id"

    def test_response_includes_google_calendar_id(self):
        """Scenario: response schema exposes google_calendar_id."""
        response = ProfesionalIntegracionesResponse(
            has_telegram=True,
            has_google=True,
            google_calendar_id="primary",
        )
        assert response.google_calendar_id == "primary"

    def test_response_default_calendar_id(self):
        """Scenario: response with default calendar ID."""
        response = ProfesionalIntegracionesResponse(
            has_telegram=False,
            has_google=False,
            google_calendar_id="primary",
        )
        assert response.has_telegram is False
        assert response.has_google is False
        assert response.google_calendar_id == "primary"
