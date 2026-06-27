import pytest
from datetime import datetime, timedelta, date, time
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.reserva_temporal import ReservaTemporal
from app.models.turno import Turno
from tests.conftest import make_profesional


class TestReservaTemporalModel:
    """Tests for ReservaTemporal model — Task 1.5."""

    @pytest.mark.asyncio
    async def test_reserva_temporal_creation(self, db_session):
        """Scenario: Reserva exitosa."""
        profesional = make_profesional(nombre="Dr. Reserva", dias_atencion=["Lunes"])
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
        )
        db_session.add(turno)
        await db_session.flush()

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=datetime.now() + timedelta(minutes=10),
        )
        db_session.add(reserva)
        await db_session.commit()
        await db_session.refresh(reserva)

        assert reserva.id is not None
        assert reserva.turno_id == turno.id
        assert reserva.expiracion is not None

    @pytest.mark.asyncio
    async def test_reserva_temporal_unique_turno(self, db_session):
        """Scenario: Reserva duplicada bloqueada — 4.5."""
        profesional = make_profesional(nombre="Dr. Unique", dias_atencion=["Lunes"])
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
        )
        db_session.add(turno)
        await db_session.flush()

        reserva1 = ReservaTemporal(
            turno_id=turno.id,
            expiracion=datetime.now() + timedelta(minutes=10),
        )
        db_session.add(reserva1)
        await db_session.commit()

        reserva2 = ReservaTemporal(
            turno_id=turno.id,
            expiracion=datetime.now() + timedelta(minutes=15),
        )
        db_session.add(reserva2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_reserva_temporal_expiracion_futura(self, db_session):
        """Scenario: Expiración futura."""
        profesional = make_profesional(nombre="Dr. Expira", dias_atencion=["Lunes"])
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(11, 0),
            hora_fin=time(11, 30),
            profesional_id=profesional.id,
        )
        db_session.add(turno)
        await db_session.flush()

        expiracion = datetime.now() + timedelta(minutes=2)
        reserva = ReservaTemporal(turno_id=turno.id, expiracion=expiracion)
        db_session.add(reserva)
        await db_session.commit()
        await db_session.refresh(reserva)
        assert reserva.expiracion == expiracion
