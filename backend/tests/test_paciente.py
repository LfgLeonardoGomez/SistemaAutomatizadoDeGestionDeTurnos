import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase

from app.models.base import Base
from app.models.paciente import Paciente


class TestPacienteModel:
    """Tests for Paciente model — Task 1.2."""

    @pytest.mark.asyncio
    async def test_paciente_creation(self, db_session):
        """Scenario: Registro exitoso de paciente."""
        paciente = Paciente(
            nombre="Juan",
            apellido="Pérez",
            dni="12345678",
            telefono="+54 9 11 1234-5678",
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

    @pytest.mark.asyncio
    async def test_paciente_unique_dni(self, db_session):
        """Scenario: DNI duplicado bloqueado — 4.2."""
        p1 = Paciente(nombre="A", apellido="B", dni="11111111", telefono="1")
        db_session.add(p1)
        await db_session.commit()

        p2 = Paciente(nombre="C", apellido="D", dni="11111111", telefono="2")
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_paciente_not_null_fields(self, db_session):
        """Scenario: Datos mínimos faltantes."""
        paciente = Paciente(nombre=None, apellido="X", dni="22222222", telefono="3")
        db_session.add(paciente)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_paciente_query_by_dni(self, db_session):
        """Scenario: Triangulate — query paciente by DNI."""
        paciente = Paciente(nombre="Ana", apellido="García", dni="33333333", telefono="4")
        db_session.add(paciente)
        await db_session.commit()

        result = await db_session.execute(select(Paciente).where(Paciente.dni == "33333333"))
        db_paciente = result.scalar_one()
        assert db_paciente.nombre == "Ana"
