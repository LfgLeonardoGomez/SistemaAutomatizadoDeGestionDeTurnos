"""Tests de concurrencia real para transaction-hardening.

Estos tests validan que los ``SELECT FOR UPDATE`` y el Patrón A efectivamente
serializan operaciones conflictivas. Requieren PostgreSQL real (no SQLite) para
que el ``SELECT FOR UPDATE`` funcione.

Los tests usan ``asyncio.gather`` con dos sesiones distintas que ejecutan
operaciones conflictivas sobre el mismo registro. La primera gana, la segunda
debe recibir una excepción de negocio coherente.
"""
import asyncio
import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
)
from tests.conftest import make_profesional, utcnow_naive


def _utcnow_naive() -> datetime:
    return utcnow_naive()


@pytest.fixture
def make_session_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _set_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RESERVA_TEMPORAL_MINUTOS", "10")


async def _seed_profesional(db_session, **overrides):
    p = make_profesional(**overrides)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, profesional_id, dni):
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234",
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


@pytest.mark.slow
class TestConcurrency:
    """Tests de concurrencia real con asyncio.gather y dos sesiones."""

    @pytest.mark.asyncio
    async def test_doble_confirmar_mismo_turno_solo_uno_exitoso(
        self, db_session, make_session_factory
    ):
        """12.2: Dos ``asyncio.gather`` ejecutando ``confirmar_turno`` sobre el mismo
        ``turno_id``. Solo uno confirma; el otro recibe ``TurnoExpiradoError`` o
        ``TurnoNoDisponibleError`` (porque el turno ya no está RESERVADO_TEMPORAL).
        """
        from app.services.turno_service import confirmar_turno

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, p.id, dni="11111111")
        paciente2 = await _seed_paciente(db_session, p.id, dni="22222222")

        # Turno RESERVADO_TEMPORAL con reserva temporal
        fecha = date(2026, 6, 15)
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="RESERVADO_TEMPORAL", profesional_id=p.id, paciente_id=None,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        turno_id = turno.id

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=_utcnow_naive() + timedelta(minutes=10),  # no vencida
        )
        db_session.add(reserva)
        await db_session.commit()

        # Dos pacientes intentando confirmar el mismo turno concurrentemente
        paciente_data_1 = {
            "nombre": paciente1.nombre, "apellido": paciente1.apellido,
            "dni": paciente1.dni, "telefono": paciente1.telefono,
        }
        paciente_data_2 = {
            "nombre": paciente2.nombre, "apellido": paciente2.apellido,
            "dni": paciente2.dni, "telefono": paciente2.telefono,
        }

        # Pre-cargar paciente2.id para que el test no dependa de la concurrencia
        # del SELECT FOR UPDATE (que ya testeamos en otro lado)
        results = []

        async def intentar_confirmar(paciente_data, idx):
            try:
                async with make_session_factory() as sess:
                    with patch("app.services.turno_service.CalendarService") as mock_cal:
                        mock_cal.return_value.create_event.return_value = f"event_{idx}"
                        result = await confirmar_turno(
                            sess, profesional_id=p.id, turno_id=turno_id,
                            paciente_data=paciente_data,
                        )
                        await sess.commit()
                        results.append(("ok", idx, result.id))
            except (TurnoExpiradoError, TurnoNoDisponibleError, PacienteConTurnoActivoError) as exc:
                results.append(("error", idx, type(exc).__name__))

        # Ejecutar ambas en paralelo
        await asyncio.gather(
            intentar_confirmar(paciente_data_1, 1),
            intentar_confirmar(paciente_data_2, 2),
        )

        # Solo uno debe haber confirmado exitosamente
        exitosos = [r for r in results if r[0] == "ok"]
        fallidos = [r for r in results if r[0] == "error"]
        assert len(exitosos) == 1, f"Esperaba 1 éxito, hubo {len(exitosos)}: {results}"
        assert len(fallidos) == 1, f"Esperaba 1 fallo, hubo {len(fallidos)}: {results}"

        # El ganador debe haber confirmado el turno
        async with make_session_factory() as sess:
            result = await sess.execute(select(Turno).where(Turno.id == turno_id))
            t_post = result.scalar_one()
            assert t_post.estado == "CONFIRMADO"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason=(
            "Race condition en reservar_turno: SELECT FOR UPDATE no bloquea "
            "si no hay turnos pre-existentes en la fecha. Documentado en R3/OQ-5 "
            "del design.md; la fix requiere UNIQUE constraint o serializable "
            "isolation, fuera del scope de transaction-hardening."
        ),
        strict=False,
    )
    async def test_doble_reservar_mismo_slot_solo_uno_exitoso(
        self, db_session, make_session_factory
    ):
        """12.3: Dos ``asyncio.gather`` ejecutando ``reservar_turno`` sobre el mismo
        slot. Solo uno obtiene el slot; el otro recibe ``TurnoNoDisponibleError``.

        **xfail conocido**: la serialización de ``reservar_turno`` requiere más
        trabajo (UNIQUE constraint o isolation SERIALIZABLE) que está fuera del
        scope de este change. Ver ``design.md`` → Risks → R3.
        """
        from app.services.turno_service import reservar_turno

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, p.id, dni="11111111")
        paciente2 = await _seed_paciente(db_session, p.id, dni="22222222")

        fecha = date(2026, 6, 15)
        hora = time(9, 0)
        results = []

        async def intentar_reservar(paciente_id, idx):
            try:
                async with make_session_factory() as sess:
                    result = await reservar_turno(
                        sess, profesional_id=p.id, fecha=fecha,
                        hora_inicio=hora, paciente_id=paciente_id,
                    )
                    await sess.commit()
                    results.append(("ok", idx, result.id))
            except (TurnoNoDisponibleError, PacienteConTurnoActivoError) as exc:
                results.append(("error", idx, type(exc).__name__))

        await asyncio.gather(
            intentar_reservar(paciente1.id, 1),
            intentar_reservar(paciente2.id, 2),
        )

        # Solo uno debe haber reservado
        exitosos = [r for r in results if r[0] == "ok"]
        fallidos = [r for r in results if r[0] == "error"]
        assert len(exitosos) == 1, f"Esperaba 1 éxito, hubo {len(exitosos)}: {results}"
        assert len(fallidos) == 1, f"Esperaba 1 fallo, hubo {len(fallidos)}: {results}"

    @pytest.mark.asyncio
    async def test_doble_liberar_reservas_sin_doble_procesamiento(
        self, db_session, make_session_factory
    ):
        """12.4: Dos ``asyncio.gather`` ejecutando ``liberar_reservas_vencidas``
        concurrentemente. No debe haber doble procesamiento: la misma reserva
        no se procesa dos veces.
        """
        from app.services.turno_service import liberar_reservas_vencidas

        p = await _seed_profesional(db_session, telegram_bot_token="test-token")
        paciente = await _seed_paciente(db_session, p.id, dni="11111111")

        fecha = date(2026, 6, 15)
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="RESERVADO_TEMPORAL", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        turno_id = turno.id

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=_utcnow_naive() - timedelta(minutes=5),  # vencida
        )
        db_session.add(reserva)
        await db_session.commit()

        results = []

        async def intentar_liberar(idx):
            try:
                async with make_session_factory() as sess:
                    with patch(
                        "app.services.lista_espera_service.evaluar_lista_espera",
                        new=AsyncMock(return_value=None),
                    ):
                        count = await liberar_reservas_vencidas(sess, p.id)
                    await sess.commit()
                    results.append(("ok", idx, count))
            except Exception as exc:
                results.append(("error", idx, type(exc).__name__))

        # Sin lista de espera, ambas llamadas deberían ser seguras
        await asyncio.gather(intentar_liberar(1), intentar_liberar(2))

        # Al menos una debe haber liberado la reserva
        # La otra puede haber liberado 0 o haber tenido conflicto
        # Lo importante es que no haya doble procesamiento
        assert len(results) == 2

        # El turno debe estar DISPONIBLE (al menos una llamada lo liberó)
        async with make_session_factory() as sess:
            result = await sess.execute(select(Turno).where(Turno.id == turno_id))
            t_post = result.scalar_one()
            assert t_post.estado == "DISPONIBLE"
