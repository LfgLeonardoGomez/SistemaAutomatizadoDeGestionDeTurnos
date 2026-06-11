import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.config import Settings
from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
    TurnoYaCanceladoError,
)


@pytest.fixture
def test_settings():
    return Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        telegram_bot_token="test",
        google_calendar_credentials='{"type": "service_account"}',
        google_calendar_id="primary",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_profesional(db_session: AsyncSession) -> Profesional:
    p = Profesional(
        nombre="Dr. Test",
        especialidad="Test",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session: AsyncSession, dni: str = "12345678") -> Paciente:
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234"
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


# ---------------------------------------------------------------------------
# 6.1 reservar_turno exitoso
# ---------------------------------------------------------------------------

class TestReservarTurno:
    @pytest.mark.asyncio
    async def test_reservar_turno_exitoso(self, db_session, test_settings):
        """Scenario: crea Turno en RESERVADO_TEMPORAL y ReservaTemporal."""
        from app.services.turno_service import reservar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        fecha = date(2026, 6, 15)  # Monday

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )

        assert turno.id is not None
        assert turno.estado == "RESERVADO_TEMPORAL"
        assert turno.fecha == fecha
        assert turno.hora_inicio == time(9, 0)
        assert turno.hora_fin == time(9, 30)
        assert turno.paciente_id == paciente.id
        assert turno.profesional_id == p.id

        # ReservaTemporal debe existir
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one_or_none()
        assert reserva is not None
        assert reserva.expiracion > datetime.now()

    @pytest.mark.asyncio
    async def test_reservar_turno_bloqueado_por_turno_activo(self, db_session, test_settings):
        """Scenario: paciente con turno activo → PacienteConTurnoActivoError."""
        from app.services.turno_service import reservar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        fecha = date(2026, 6, 15)

        # Primer turno
        await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )

        # Segundo turno debe fallar
        with pytest.raises(PacienteConTurnoActivoError):
            await reservar_turno(
                db_session, fecha=fecha, hora_inicio=time(10, 0), paciente_id=paciente.id
            )

    @pytest.mark.asyncio
    async def test_reservar_turno_slot_ya_ocupado(self, db_session, test_settings):
        """Scenario: slot ya ocupado por otro turno → TurnoNoDisponibleError."""
        from app.services.turno_service import reservar_turno

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, dni="11111111")
        paciente2 = await _seed_paciente(db_session, dni="22222222")
        fecha = date(2026, 6, 15)

        # Paciente 1 reserva
        await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente1.id,
            settings=test_settings,
        )

        # Paciente 2 intenta el mismo slot
        with pytest.raises(TurnoNoDisponibleError):
            await reservar_turno(
                db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente2.id,
                settings=test_settings,
            )

    @pytest.mark.asyncio
    async def test_reservar_turno_sin_paciente_id(self, db_session, test_settings):
        """Scenario: reserva temporal sin paciente_id (para confirmación posterior)."""
        from app.services.turno_service import reservar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        assert turno.estado == "RESERVADO_TEMPORAL"
        assert turno.paciente_id is None


# ---------------------------------------------------------------------------
# 6.4 confirmar_turno exitoso
# ---------------------------------------------------------------------------

class TestConfirmarTurno:
    @pytest.mark.asyncio
    async def test_confirmar_turno_exitoso(self, db_session, test_settings):
        """Scenario: pasa a CONFIRMADO, elimina ReservaTemporal, crea evento calendar."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        # Reserva temporal sin paciente
        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        # Confirmar con datos de paciente
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert confirmado.estado == "CONFIRMADO"
        assert confirmado.paciente_id is not None

        # ReservaTemporal debe haberse eliminado
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_confirmar_turno_expirado(self, db_session, test_settings):
        """Scenario: ReservaTemporal eliminada previamente → TurnoExpiradoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        # Eliminar ReservaTemporal manualmente para simular expiración
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one()
        await db_session.delete(reserva)
        await db_session.commit()

        with pytest.raises(TurnoExpiradoError):
            await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

    @pytest.mark.asyncio
    async def test_confirmar_turno_doble_turno_activo(self, db_session, test_settings):
        """Scenario: paciente adquiere otro turno en paralelo → PacienteConTurnoActivoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        fecha = date(2026, 6, 15)

        # Turno 1: confirmado
        t1 = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )
        # Simular confirmación previa
        t1.estado = "CONFIRMADO"
        await db_session.commit()

        # Turno 2: reservado temporal
        t2 = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None,
            settings=test_settings,
        )

        # Intentar confirmar t2 con el mismo paciente debe fallar
        with pytest.raises(PacienteConTurnoActivoError):
            await confirmar_turno(
                db_session,
                turno_id=t2.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

    @pytest.mark.asyncio
    async def test_confirmar_turno_calendar_fallback(self, db_session, test_settings):
        """Scenario: calendar falla → turno sigue CONFIRMADO y se loguea error."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.side_effect = RuntimeError("Calendar API down")
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert confirmado.estado == "CONFIRMADO"
        mock_service.create_event.assert_called_once()


# ---------------------------------------------------------------------------
# 6.7 liberar_reservas_vencidas
# ---------------------------------------------------------------------------

class TestLiberarReservasVencidas:
    @pytest.mark.asyncio
    async def test_liberar_reservas_vencidas(self, db_session, test_settings):
        """Scenario: reserva con expiración pasada → turno vuelve a DISPONIBLE."""
        from app.services.turno_service import reservar_turno, liberar_reservas_vencidas

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        # Forzar expiración pasada
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one()
        reserva.expiracion = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        liberados = await liberar_reservas_vencidas(db_session)
        assert liberados >= 1

        # Turno debe estar DISPONIBLE
        result = await db_session.execute(
            select(Turno).where(Turno.id == turno.id)
        )
        turno_actualizado = result.scalar_one()
        assert turno_actualizado.estado == "DISPONIBLE"
        assert turno_actualizado.paciente_id is None

        # ReservaTemporal debe haberse eliminado
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_liberar_reservas_sin_vencidas(self, db_session, test_settings):
        """Scenario: no hay reservas vencidas → 0 liberados."""
        from app.services.turno_service import liberar_reservas_vencidas

        liberados = await liberar_reservas_vencidas(db_session)
        assert liberados == 0


# ---------------------------------------------------------------------------
# 6.8 consultar_disponibilidad
# ---------------------------------------------------------------------------

class TestConsultarDisponibilidad:
    @pytest.mark.asyncio
    async def test_consultar_disponibilidad(self, db_session, test_settings):
        """Scenario: fecha con slots mixtos → solo libres."""
        from app.services.turno_service import reservar_turno, consultar_disponibilidad

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        # Reservar un slot
        await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        slots = await consultar_disponibilidad(db_session, fecha=fecha)
        horarios = [s["hora_inicio"] for s in slots]
        assert "09:00" not in horarios
        assert "08:00" in horarios
        assert "10:00" in horarios

    @pytest.mark.asyncio
    async def test_consultar_disponibilidad_dia_no_laborable(self, db_session, test_settings):
        """Scenario: día no laborable → lista vacía."""
        from app.services.turno_service import consultar_disponibilidad

        p = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Martes"],
        )
        db_session.add(p)
        await db_session.commit()

        fecha = date(2026, 6, 15)  # Monday
        slots = await consultar_disponibilidad(db_session, fecha=fecha)
        assert slots == []


# ---------------------------------------------------------------------------
# 6.3 condición de carrera (simulada)
# ---------------------------------------------------------------------------

class TestRaceCondition:
    @pytest.mark.asyncio
    async def test_doble_reserva_concurrente_mismo_slot(self, db_session, test_settings):
        """Scenario: dos reservas simultáneas sobre mismo slot → solo uno gana."""
        import asyncio
        from app.services.turno_service import reservar_turno

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, dni="11111111")
        paciente2 = await _seed_paciente(db_session, dni="22222222")
        fecha = date(2026, 6, 15)

        async def intentar_reservar(paciente_id: int):
            async_session = db_session.session_factory()  # won't work easily
            # For the test, we use the same db_session but in a real scenario
            # we would use separate sessions.
            try:
                return await reservar_turno(
                    db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente_id,
                    settings=test_settings,
                )
            except Exception as exc:
                return exc

        # In SQLite, concurrent writes on the same session are serialized,
        # so one will succeed and the second will get an exception.
        # We simulate two calls sequentially to show the logic path.
        t1 = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente1.id,
            settings=test_settings,
        )
        assert t1.estado == "RESERVADO_TEMPORAL"

        with pytest.raises(TurnoNoDisponibleError):
            await reservar_turno(
                db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente2.id,
                settings=test_settings,
            )


# ---------------------------------------------------------------------------
# 7.1 cancelar_turno
# ---------------------------------------------------------------------------

class TestReprogramarTurno:
    @pytest.mark.asyncio
    async def test_reprogramar_turno_exitoso(self, db_session, test_settings):
        """Scenario: cancela viejo, crea nuevo CONFIRMADO, calendar sync."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)
        nueva_fecha = date(2026, 6, 16)

        # Crear y confirmar turno viejo
        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_old"
        await db_session.commit()

        # Reprogramar al slot 10:00 del día siguiente
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_new"
            mock_calendar_cls.return_value = mock_service

            nuevo = await reprogramar_turno(
                db_session,
                turno_id=confirmado.id,
                nueva_fecha=nueva_fecha,
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

        assert nuevo.estado == "CONFIRMADO"
        assert nuevo.fecha == nueva_fecha
        assert nuevo.hora_inicio == time(10, 0)
        assert nuevo.paciente_id == confirmado.paciente_id

        # Verificar que el viejo está CANCELADO
        result = await db_session.execute(select(Turno).where(Turno.id == confirmado.id))
        viejo = result.scalar_one()
        assert viejo.estado == "CANCELADO"

        mock_service.delete_event.assert_called_once_with("event_old")
        mock_service.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_reprogramar_turno_no_existe(self, db_session):
        """Scenario: turno inexistente → TurnoNoEncontradoError."""
        from app.services.turno_service import reprogramar_turno

        with pytest.raises(TurnoNoEncontradoError):
            await reprogramar_turno(
                db_session, turno_id=99999, nueva_fecha=date(2026, 6, 16), nueva_hora_inicio=time(10, 0)
            )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_ya_cancelado(self, db_session, test_settings):
        """Scenario: turno ya CANCELADO → TurnoYaCanceladoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno, reprogramar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_123"
        await db_session.commit()
        await cancelar_turno(db_session, turno_id=confirmado.id)

        with pytest.raises(TurnoYaCanceladoError):
            await reprogramar_turno(
                db_session,
                turno_id=confirmado.id,
                nueva_fecha=date(2026, 6, 16),
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_slot_no_disponible(self, db_session, test_settings):
        """Scenario: slot ocupado → TurnoNoDisponibleError, viejo queda CANCELADO."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        # Ocupar el slot 10:00
        t_ocupado = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_ocupado"
            mock_calendar_cls.return_value = mock_service
            await confirmar_turno(
                db_session,
                turno_id=t_ocupado.id,
                paciente_data={"nombre": "Ana", "apellido": "Garcia", "dni": "87654321", "telefono": "555-9999"},
            )
        t_ocupado.google_event_id = "event_ocupado"
        await db_session.commit()

        # Crear turno a reprogramar
        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )
        confirmado.google_event_id = "event_old"
        await db_session.commit()

        # Intentar reprogramar al slot 10:00 ocupado
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service

            with pytest.raises(TurnoNoDisponibleError):
                await reprogramar_turno(
                    db_session,
                    turno_id=confirmado.id,
                    nueva_fecha=fecha,
                    nueva_hora_inicio=time(10, 0),
                    settings=test_settings,
                )

        # El turno viejo debe quedar CANCELADO (cancelación ya se hizo)
        result = await db_session.execute(select(Turno).where(Turno.id == confirmado.id))
        viejo = result.scalar_one()
        assert viejo.estado == "CANCELADO"

    @pytest.mark.asyncio
    async def test_reprogramar_turno_paciente_con_otro_activo(self, db_session, test_settings):
        """Scenario: paciente tiene otro turno activo → PacienteConTurnoActivoError (RN-TU-01)."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        fecha = date(2026, 6, 15)

        # Turno 1: confirmado del paciente
        t1 = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_t1"
            mock_calendar_cls.return_value = mock_service
            await confirmar_turno(
                db_session,
                turno_id=t1.id,
                paciente_data={"nombre": paciente.nombre, "apellido": paciente.apellido, "dni": paciente.dni, "telefono": paciente.telefono},
            )
        t1.google_event_id = "event_t1"
        await db_session.commit()

        # Turno 2: confirmado de otro paciente (para reprogramar)
        t2 = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_t2"
            mock_calendar_cls.return_value = mock_service
            confirmado2 = await confirmar_turno(
                db_session,
                turno_id=t2.id,
                paciente_data={"nombre": "Ana", "apellido": "Garcia", "dni": "99999999", "telefono": "555-9999"},
            )
        confirmado2.google_event_id = "event_t2"
        await db_session.commit()

        # Intentar reprogramar t2 al slot 11:00, pero con el paciente que ya tiene t1 activo
        # Esto requiere que pasemos paciente_data del paciente con turno activo
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service

            with pytest.raises(PacienteConTurnoActivoError):
                await reprogramar_turno(
                    db_session,
                    turno_id=confirmado2.id,
                    nueva_fecha=fecha,
                    nueva_hora_inicio=time(11, 0),
                    paciente_data={"nombre": paciente.nombre, "apellido": paciente.apellido, "dni": paciente.dni, "telefono": paciente.telefono},
                    settings=test_settings,
                )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_calendar_create_falla(self, db_session, test_settings):
        """Scenario: calendar create falla → nuevo turno sigue CONFIRMADO, log error."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)
        nueva_fecha = date(2026, 6, 16)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )
        confirmado.google_event_id = "event_old"
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.delete_event.return_value = None
            mock_service.create_event.side_effect = RuntimeError("Calendar API down")
            mock_calendar_cls.return_value = mock_service

            nuevo = await reprogramar_turno(
                db_session,
                turno_id=confirmado.id,
                nueva_fecha=nueva_fecha,
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

        assert nuevo.estado == "CONFIRMADO"
        assert nuevo.fecha == nueva_fecha
        mock_service.delete_event.assert_called_once_with("event_old")
        mock_service.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_reprogramar_turno_reservado_temporal(self, db_session, test_settings):
        """Scenario: turno RESERVADO_TEMPORAL no puede reprogramarse → error."""
        from app.services.turno_service import reservar_turno, reprogramar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with pytest.raises(TurnoYaCanceladoError):
            await reprogramar_turno(
                db_session,
                turno_id=turno.id,
                nueva_fecha=fecha,
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )


class TestCancelarTurno:
    @pytest.mark.asyncio
    async def test_cancelar_turno_exitoso(self, db_session, test_settings):
        """Scenario: turno CONFIRMADO → CANCELADO, calendar event eliminado."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        # Crear y confirmar turno
        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        # Set google_event_id manually (normally set by calendar service in real flow)
        confirmado.google_event_id = "event_123"
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            cancelado = await cancelar_turno(db_session, turno_id=confirmado.id)

        assert cancelado.estado == "CANCELADO"
        mock_service.delete_event.assert_called_once_with("event_123")

    @pytest.mark.asyncio
    async def test_cancelar_turno_no_existe(self, db_session):
        """Scenario: turno inexistente → TurnoNoEncontradoError."""
        from app.services.turno_service import cancelar_turno

        with pytest.raises(TurnoNoEncontradoError):
            await cancelar_turno(db_session, turno_id=99999)

    @pytest.mark.asyncio
    async def test_cancelar_turno_ya_cancelado(self, db_session, test_settings):
        """Scenario: turno ya CANCELADO → TurnoYaCanceladoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_123"
        await db_session.commit()

        # Primera cancelación exitosa
        await cancelar_turno(db_session, turno_id=confirmado.id)

        # Segunda cancelación debe fallar
        with pytest.raises(TurnoYaCanceladoError):
            await cancelar_turno(db_session, turno_id=confirmado.id)

    @pytest.mark.asyncio
    async def test_cancelar_turno_calendar_falla(self, db_session, test_settings):
        """Scenario: calendar delete falla → turno sigue CANCELADO, log error."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_123"
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.delete_event.side_effect = RuntimeError("Calendar API down")
            mock_calendar_cls.return_value = mock_service

            cancelado = await cancelar_turno(db_session, turno_id=confirmado.id)

        assert cancelado.estado == "CANCELADO"
        mock_service.delete_event.assert_called_once_with("event_123")

    @pytest.mark.asyncio
    async def test_cancelar_turno_reservado_temporal(self, db_session, test_settings):
        """Scenario: turno RESERVADO_TEMPORAL no puede cancelarse → error."""
        from app.services.turno_service import reservar_turno, cancelar_turno

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with pytest.raises(TurnoYaCanceladoError):
            await cancelar_turno(db_session, turno_id=turno.id)
