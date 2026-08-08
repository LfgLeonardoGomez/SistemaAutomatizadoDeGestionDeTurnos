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
    buscar_paciente_por_dni,
)
from tests.conftest import make_profesional_persisted


class TestPacienteService:
    """Tests unitarios para paciente_service — Task 2.5."""

    @pytest.mark.asyncio
    async def test_crear_o_obtener_paciente_nuevo(self, db_session, profesional):
        """Scenario: Paciente nuevo → se crea."""
        data = PacienteCreate(nombre="Juan", apellido="Pérez", dni="12345678", telefono="1")
        result = await crear_o_obtener_paciente(db_session, profesional.id, data)
        await db_session.commit()
        assert result.nombre == "Juan"
        assert result.apellido == "Pérez"
        assert result.dni == "12345678"
        assert result.telefono == "1"
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_crear_o_obtener_paciente_existente(self, db_session, profesional):
        """Scenario: DNI ya existe para este profesional → retorna existente sin duplicar."""
        data = PacienteCreate(nombre="Juan", apellido="Pérez", dni="12345678", telefono="1")
        first = await crear_o_obtener_paciente(db_session, profesional.id, data)
        await db_session.commit()

        data2 = PacienteCreate(nombre="Otro", apellido="Nombre", dni="12345678", telefono="2")
        second = await crear_o_obtener_paciente(db_session, profesional.id, data2)

        assert first.id == second.id
        assert second.nombre == "Juan"  # Datos originales

    @pytest.mark.asyncio
    async def test_obtener_paciente_con_historial_existente(self, db_session, profesional):
        """Scenario: Paciente con turnos."""
        paciente = Paciente(
            nombre="Ana", apellido="García", dni="33333333", telefono="4",
            profesional_id=profesional.id,
        )
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

        result = await obtener_paciente_con_historial(db_session, profesional.id, paciente.id)
        assert result is not None
        assert result.id == paciente.id
        assert result.nombre == "Ana"
        assert len(result.turnos) == 1
        assert result.turnos[0].estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_obtener_paciente_con_historial_no_existe(self, db_session, profesional):
        """Scenario: Paciente no encontrado."""
        result = await obtener_paciente_con_historial(db_session, profesional.id, 9999)
        assert result is None

    @pytest.mark.asyncio
    async def test_listar_turnos_por_paciente_con_turnos(self, db_session, profesional):
        """Scenario: Paciente con múltiples turnos."""
        paciente = Paciente(
            nombre="Luis", apellido="Lopez", dni="44444444", telefono="5",
            profesional_id=profesional.id,
        )
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

        turnos = await listar_turnos_por_paciente(db_session, profesional.id, paciente.id)
        assert len(turnos) == 2
        assert turnos[0].estado == "CONFIRMADO"
        assert turnos[1].estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_listar_turnos_por_paciente_sin_turnos(self, db_session, profesional):
        """Scenario: Paciente sin turnos → lista vacía."""
        paciente = Paciente(
            nombre="Pepe", apellido="Argento", dni="55555555", telefono="6",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        turnos = await listar_turnos_por_paciente(db_session, profesional.id, paciente.id)
        assert turnos == []

    @pytest.mark.asyncio
    async def test_crear_o_obtener_paciente_integrity_error_no_destruye_outer_tx(self, db_session, profesional):
        """Scenario: IntegrityError en crear_o_obtener_paciente no deja la sesión en estado inválido."""
        data = PacienteCreate(nombre="Juan", apellido="Perez", dni="12345678", telefono="1")
        first = await crear_o_obtener_paciente(db_session, profesional.id, data)
        await db_session.commit()

        data2 = PacienteCreate(nombre="Otro", apellido="Nombre", dni="12345678", telefono="2")
        second = await crear_o_obtener_paciente(db_session, profesional.id, data2)
        assert first.id == second.id

        # La sesión debe seguir siendo usable: podemos crear otro objeto y commitear
        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            estado="DISPONIBLE",
        )
        db_session.add(turno)
        await db_session.commit()
        assert turno.id is not None


class TestBuscarPacientePorDni:
    """Tests unitarios para ``buscar_paciente_por_dni`` — c-27 grupo 2 (RED)."""

    @pytest.mark.asyncio
    async def test_buscar_paciente_por_dni_existente(self, db_session, profesional):
        """Scenario: DNI belongs to an existing patient of the professional."""
        paciente = Paciente(
            nombre="Juan", apellido="Pérez", dni="30111222", telefono="1122334455",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        result = await buscar_paciente_por_dni(db_session, profesional.id, "30111222")

        assert result is not None
        assert result.id == paciente.id
        assert result.nombre == "Juan"
        assert result.apellido == "Pérez"
        assert result.dni == "30111222"
        assert result.telefono == "1122334455"

    @pytest.mark.asyncio
    async def test_buscar_paciente_por_dni_no_registrado(self, db_session, profesional):
        """Scenario: DNI is not registered → None (router maps to 404)."""
        result = await buscar_paciente_por_dni(db_session, profesional.id, "99999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_buscar_paciente_por_dni_aislamiento_entre_profesionales(self, db_session, profesional):
        """Scenario: same DNI under two professionals → each lookup returns only its own patient."""
        otro = await make_profesional_persisted(db_session, email="otro-dni@local.dev")

        propio = Paciente(
            nombre="Propio", apellido="A", dni="30111222", telefono="1",
            profesional_id=profesional.id,
        )
        ajeno = Paciente(
            nombre="Ajeno", apellido="B", dni="30111222", telefono="2",
            profesional_id=otro.id,
        )
        db_session.add(propio)
        db_session.add(ajeno)
        await db_session.commit()

        result_propio = await buscar_paciente_por_dni(db_session, profesional.id, "30111222")
        result_otro = await buscar_paciente_por_dni(db_session, otro.id, "30111222")

        assert result_propio.nombre == "Propio"
        assert result_otro.nombre == "Ajeno"
        assert result_propio.id != result_otro.id

    @pytest.mark.asyncio
    async def test_buscar_paciente_por_dni_existe_solo_bajo_otro_profesional(self, db_session, profesional):
        """Scenario: DNI exists only under professional A → professional B gets None."""
        otro = await make_profesional_persisted(db_session, email="otro-dni-2@local.dev")

        paciente = Paciente(
            nombre="DeOtro", apellido="Prof", dni="40555666", telefono="3",
            profesional_id=otro.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        result = await buscar_paciente_por_dni(db_session, profesional.id, "40555666")
        assert result is None
