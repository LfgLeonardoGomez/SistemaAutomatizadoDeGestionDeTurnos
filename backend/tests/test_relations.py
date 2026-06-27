import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.models.lista_de_espera import ListaDeEspera
from tests.conftest import make_profesional


class TestModelRelations:
    """Tests for bidirectional relationships and referential integrity."""

    @pytest.mark.asyncio
    async def test_profesional_turnos_relation(self, db_session):
        """Scenario: Profesional con 3 turnos — 4.8."""
        profesional = make_profesional(
            nombre="Dr. Relación",
            dias_atencion=["Lunes"],
            email="dr.relacion@local.dev",
            password_hash="$2b$12$dummy",
        )
        db_session.add(profesional)
        await db_session.flush()

        for i in range(3):
            turno = Turno(
                fecha=date(2026, 6, 15),
                hora_inicio=time(8 + i, 0),
                hora_fin=time(8 + i, 30),
                profesional_id=profesional.id,
            )
            db_session.add(turno)
        await db_session.commit()

        result = await db_session.execute(
            select(Profesional).where(Profesional.id == profesional.id)
        )
        db_profesional = result.scalar_one()
        assert len(db_profesional.turnos) == 3

    @pytest.mark.asyncio
    async def test_paciente_turnos_relation(self, db_session):
        """Scenario: Paciente con 2 turnos — 4.9."""
        profesional = make_profesional(
            nombre="Dr. PacienteTurnos",
            dias_atencion=["Lunes"],
            email="dr.pt@local.dev",
            password_hash="$2b$12$dummy",
        )
        db_session.add(profesional)
        await db_session.flush()

        paciente = Paciente(
            nombre="Ana", apellido="Rel", dni="88888888", telefono="9",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.flush()

        for i in range(2):
            turno = Turno(
                fecha=date(2026, 6, 15),
                hora_inicio=time(9 + i, 0),
                hora_fin=time(9 + i, 30),
                profesional_id=profesional.id,
                paciente_id=paciente.id,
                estado="CONFIRMADO",
            )
            db_session.add(turno)
        await db_session.commit()

        result = await db_session.execute(
            select(Paciente).where(Paciente.id == paciente.id)
        )
        db_paciente = result.scalar_one()
        assert len(db_paciente.turnos) == 2

    @pytest.mark.asyncio
    async def test_integridad_referencial_profesional(self, db_session):
        """Scenario: Turno con profesional_id inexistente — 4.6."""
        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=99999,
        )
        db_session.add(turno)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_turno_reserva_temporal_relation(self, db_session):
        """Scenario: Reserva temporal se elimina al confirmar turno."""
        profesional = make_profesional(
            nombre="Dr. Cascade",
            dias_atencion=["Lunes"],
            email="dr.cascade@local.dev",
            password_hash="$2b$12$dummy",
        )
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            estado="RESERVADO_TEMPORAL",
        )
        db_session.add(turno)
        await db_session.flush()

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=datetime.now() + timedelta(minutes=10),
        )
        db_session.add(reserva)
        await db_session.commit()

        # Verify relation exists
        result = await db_session.execute(
            select(Turno).where(Turno.id == turno.id)
        )
        db_turno = result.scalar_one()
        assert db_turno.reserva_temporal is not None

        # Delete reserva
        await db_session.delete(db_turno.reserva_temporal)
        await db_session.commit()
        await db_session.refresh(db_turno)
        assert db_turno.reserva_temporal is None

    @pytest.mark.asyncio
    async def test_paciente_lista_de_espera_relation(self, db_session):
        """Scenario: Paciente con registros en lista de espera."""
        profesional = make_profesional(
            nombre="Dr. ListaEspera",
            dias_atencion=["Lunes"],
            email="dr.le@local.dev",
            password_hash="$2b$12$dummy",
        )
        db_session.add(profesional)
        await db_session.flush()

        paciente = Paciente(
            nombre="Luis", apellido="Espera", dni="99999999", telefono="10",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.flush()

        for i in range(2):
            registro = ListaDeEspera(
                paciente_id=paciente.id,
                fecha_solicitada=date(2026, 6, 15 + i),
                profesional_id=profesional.id,
            )
            db_session.add(registro)
        await db_session.commit()

        result = await db_session.execute(
            select(Paciente).where(Paciente.id == paciente.id)
        )
        db_paciente = result.scalar_one()
        assert len(db_paciente.lista_de_espera) == 2
