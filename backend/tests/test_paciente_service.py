import pytest
from datetime import date, time, datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.schemas.paciente import PacienteCreate, PacienteRead, PacienteConHistorial, TurnoRead
from app.services.paciente_service import (
    crear_o_obtener_paciente,
    obtener_paciente_con_historial,
    listar_turnos_por_paciente,
)


class TestPacienteService:
    """Tests unitarios para paciente_service — Task 2.5."""

    @pytest.mark.asyncio
    async def test_crear_o_obtener_paciente_nuevo(self, db_session):
        """Scenario: Paciente nuevo → se crea."""
        data = PacienteCreate(nombre="Juan", apellido="Pérez", dni="12345678", telefono="1")
        result = await crear_o_obtener_paciente(db_session, data)
        assert result.nombre == "Juan"
        assert result.apellido == "Pérez"
        assert result.dni == "12345678"
        assert result.telefono == "1"
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_crear_o_obtener_paciente_existente(self, db_session):
        """Scenario: DNI ya existe → retorna existente sin duplicar."""
        data = PacienteCreate(nombre="Juan", apellido="Pérez", dni="12345678", telefono="1")
        first = await crear_o_obtener_paciente(db_session, data)

        data2 = PacienteCreate(nombre="Otro", apellido="Nombre", dni="12345678", telefono="2")
        second = await crear_o_obtener_paciente(db_session, data2)

        assert first.id == second.id
        assert second.nombre == "Juan"  # Datos originales

    @pytest.mark.asyncio
    async def test_obtener_paciente_con_historial_existente(self, db_session):
        """Scenario: Paciente con turnos."""
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        paciente = Paciente(nombre="Ana", apellido="García", dni="33333333", telefono="4")
        db_session.add(paciente)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        result = await obtener_paciente_con_historial(db_session, paciente.id)
        assert result is not None
        assert result.id == paciente.id
        assert result.nombre == "Ana"
        assert len(result.turnos) == 1
        assert result.turnos[0].estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_obtener_paciente_con_historial_no_existe(self, db_session):
        """Scenario: Paciente no encontrado."""
        result = await obtener_paciente_con_historial(db_session, 9999)
        assert result is None

    @pytest.mark.asyncio
    async def test_listar_turnos_por_paciente_con_turnos(self, db_session):
        """Scenario: Paciente con múltiples turnos."""
        profesional = Profesional(
            nombre="Dr. Turnos",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        paciente = Paciente(nombre="Luis", apellido="Lopez", dni="44444444", telefono="5")
        db_session.add(paciente)
        await db_session.flush()

        t1 = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        t2 = Turno(
            fecha=date(2026, 6, 16),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        db_session.add(t1)
        db_session.add(t2)
        await db_session.commit()

        turnos = await listar_turnos_por_paciente(db_session, paciente.id)
        assert len(turnos) == 2
        assert turnos[0].estado == "CONFIRMADO"
        assert turnos[1].estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_listar_turnos_por_paciente_sin_turnos(self, db_session):
        """Scenario: Paciente sin turnos → lista vacía."""
        paciente = Paciente(nombre="Pepe", apellido="Argento", dni="55555555", telefono="6")
        db_session.add(paciente)
        await db_session.commit()

        turnos = await listar_turnos_por_paciente(db_session, paciente.id)
        assert turnos == []
