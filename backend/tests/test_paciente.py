import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase

from app.models.base import Base
from app.models.paciente import Paciente
from app.models.profesional import Profesional


class TestPacienteModel:
    """Tests for Paciente model — Task 1.2."""

    @pytest_asyncio.fixture
    async def profesional(self, db_session):
        """Fixture local para tests de Paciente."""
        p = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología general",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            email="test@local.dev",
            password_hash="$2b$12$dummy",
            is_active=True,
        )
        db_session.add(p)
        await db_session.commit()
        await db_session.refresh(p)
        return p

    @pytest.mark.asyncio
    async def test_paciente_creation(self, db_session, profesional):
        """Scenario: Registro exitoso de paciente."""
        paciente = Paciente(
            nombre="Juan",
            apellido="Pérez",
            dni="12345678",
            telefono="+54 9 11 1234-5678",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()
        await db_session.refresh(paciente)

        assert paciente.id is not None
        assert paciente.nombre == "Juan"
        assert paciente.apellido == "Pérez"
        assert paciente.dni == "12345678"
        assert paciente.telefono == "+54 9 11 1234-5678"
        assert paciente.creado_en is not None
        assert paciente.profesional_id == profesional.id

    @pytest.mark.asyncio
    async def test_paciente_unique_dni_per_profesional(self, db_session, profesional):
        """Scenario: DNI duplicado bloqueado dentro del mismo profesional — 4.2."""
        p1 = Paciente(
            nombre="A", apellido="B", dni="11111111", telefono="1",
            profesional_id=profesional.id,
        )
        db_session.add(p1)
        await db_session.commit()

        p2 = Paciente(
            nombre="C", apellido="D", dni="11111111", telefono="2",
            profesional_id=profesional.id,
        )
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_paciente_dni_unique_per_profesional_only(self, db_session, profesional):
        """Scenario: DNI duplicado entre profesionales permitido."""
        p1 = Paciente(
            nombre="A", apellido="B", dni="11111111", telefono="1",
            profesional_id=profesional.id,
        )
        db_session.add(p1)
        await db_session.commit()

        otro_profesional = Profesional(
            nombre="Dr. Otro",
            especialidad="X",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="otro@local.dev",
            password_hash="$2b$12$dummy",
            is_active=True,
        )
        db_session.add(otro_profesional)
        await db_session.commit()
        await db_session.refresh(otro_profesional)

        p2 = Paciente(
            nombre="C", apellido="D", dni="11111111", telefono="2",
            profesional_id=otro_profesional.id,
        )
        db_session.add(p2)
        await db_session.commit()
        await db_session.refresh(p2)

        assert p2.id is not None

    @pytest.mark.asyncio
    async def test_paciente_not_null_fields(self, db_session, profesional):
        """Scenario: Datos mínimos faltantes."""
        paciente = Paciente(
            nombre=None, apellido="X", dni="22222222", telefono="3",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_paciente_profesional_id_required(self, db_session):
        """Scenario: Paciente sin profesional."""
        paciente = Paciente(
            nombre="Ana", apellido="García", dni="33333333", telefono="4",
            profesional_id=None,
        )
        db_session.add(paciente)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_paciente_query_by_dni(self, db_session, profesional):
        """Scenario: Triangulate — query paciente by DNI."""
        paciente = Paciente(
            nombre="Ana", apellido="García", dni="33333333", telefono="4",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        result = await db_session.execute(
            select(Paciente).where(Paciente.dni == "33333333")
        )
        db_paciente = result.scalar_one()
        assert db_paciente.nombre == "Ana"
