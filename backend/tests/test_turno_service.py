import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
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
        secret_key="test-secret",
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


async def _seed_paciente(db_session: AsyncSession, profesional_id: int, dni: str = "12345678") -> Paciente:
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234",
        profesional_id=profesional_id,
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
    async def test_reservar_turno_exitoso(self, db_session, profesional, test_settings):
        """Scenario: crea Turno en RESERVADO_TEMPORAL y ReservaTemporal."""
        from app.services.turno_service import reservar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)  # Monday

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )

        assert turno.id is not None
        assert turno.estado == "RESERVADO_TEMPORAL"
        assert turno.fecha == fecha
        assert turno.hora_inicio == time(9, 0)
        assert turno.hora_fin == time(9, 30)
        assert turno.paciente_id == paciente.id
        assert turno.profesional_id == profesional.id

        # ReservaTemporal debe existir
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one_or_none()
        assert reserva is not None
        assert reserva.expiracion > datetime.now()

    @pytest.mark.asyncio
    async def test_reservar_turno_bloqueado_por_turno_activo(self, db_session, profesional, test_settings):
        """Scenario: paciente con turno activo → PacienteConTurnoActivoError."""
        from app.services.turno_service import reservar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)

        # Primer turno
        await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )

        # Segundo turno debe fallar
        with pytest.raises(PacienteConTurnoActivoError):
            await reservar_turno(
                db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(10, 0), paciente_id=paciente.id,
                settings=test_settings,
            )

    @pytest.mark.asyncio
    async def test_reservar_turno_slot_ya_ocupado(self, db_session, profesional, test_settings):
        """Scenario: slot ya ocupado por otro turno → TurnoNoDisponibleError."""
        from app.services.turno_service import reservar_turno

        paciente1 = await _seed_paciente(db_session, profesional.id, dni="11111111")
        paciente2 = await _seed_paciente(db_session, profesional.id, dni="22222222")
        fecha = date(2026, 6, 15)

        # Paciente 1 reserva
        await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente1.id,
            settings=test_settings,
        )

        # Paciente 2 intenta el mismo slot
        with pytest.raises(TurnoNoDisponibleError):
            await reservar_turno(
                db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente2.id,
                settings=test_settings,
            )

    @pytest.mark.asyncio
    async def test_reservar_turno_sin_paciente_id(self, db_session, profesional, test_settings):
        """Scenario: reserva temporal sin paciente_id (para confirmación posterior)."""
        from app.services.turno_service import reservar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        assert turno.estado == "RESERVADO_TEMPORAL"
        assert turno.paciente_id is None


# ---------------------------------------------------------------------------
# 6.4 confirmar_turno exitoso
# ---------------------------------------------------------------------------

class TestConfirmarTurno:
    @pytest.mark.asyncio
    async def test_confirmar_turno_exitoso(self, db_session, profesional, test_settings):
        """Scenario: pasa a CONFIRMADO, elimina ReservaTemporal, crea evento calendar."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        fecha = date(2026, 6, 15)

        # Reserva temporal sin paciente
        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        # Confirmar con datos de paciente
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
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

        await db_session.commit()

        # ReservaTemporal debe haberse eliminado
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_confirmar_turno_expirado(self, db_session, profesional, test_settings):
        """Scenario: ReservaTemporal eliminada previamente → TurnoExpiradoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
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
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

    @pytest.mark.asyncio
    async def test_confirmar_turno_doble_turno_activo(self, db_session, profesional, test_settings):
        """Scenario: paciente adquiere otro turno en paralelo → PacienteConTurnoActivoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)

        # Turno 1: confirmado
        t1 = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )
        # Simular confirmación previa
        t1.estado = "CONFIRMADO"
        await db_session.commit()

        # Turno 2: reservado temporal
        t2 = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None,
            settings=test_settings,
        )

        # Intentar confirmar t2 con el mismo paciente debe fallar
        with pytest.raises(PacienteConTurnoActivoError):
            await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=t2.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

    @pytest.mark.asyncio
    async def test_confirmar_turno_persiste_google_event_id(self, db_session, profesional, test_settings):
        """Scenario: confirmar_turno persiste google_event_id retornado por CalendarService."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert confirmado.estado == "CONFIRMADO"
        assert confirmado.google_event_id == "event_123"

        await db_session.commit()

        # Verificar en DB
        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.google_event_id == "event_123"

    @pytest.mark.asyncio
    async def test_confirmar_turno_calendar_fallback(self, db_session, profesional, test_settings):
        """Scenario: calendar falla → turno sigue CONFIRMADO y google_event_id es NULL."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.side_effect = RuntimeError("Calendar API down")
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert confirmado.estado == "CONFIRMADO"
        assert confirmado.google_event_id is None
        mock_service.create_event.assert_called_once()

        await db_session.commit()

        # Verificar en DB
        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.google_event_id is None

    @pytest.mark.asyncio
    async def test_confirmar_turno_paciente_existente_sin_turno_activo(self, db_session, profesional, test_settings):
        """Scenario: paciente ya existe y no tiene turno activo → confirmar exitoso sin IntegrityError."""
        from app.services.turno_service import reservar_turno, confirmar_turno
        from app.services.paciente_service import crear_o_obtener_paciente
        from app.schemas.paciente import PacienteCreate

        # Crear paciente existente
        data = PacienteCreate(nombre="Juan", apellido="Perez", dni="12345678", telefono="555-1234")
        paciente = await crear_o_obtener_paciente(db_session, profesional.id, data)
        await db_session.commit()

        fecha = date(2026, 6, 15)
        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert confirmado.estado == "CONFIRMADO"
        assert confirmado.paciente_id == paciente.id

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_confirmar_turno_calendario_falla_sesion_usable(self, db_session, profesional, test_settings):
        """Scenario: CalendarService.create_event falla, la sesión externa puede hacer commit."""
        from app.services.turno_service import reservar_turno, confirmar_turno

        fecha = date(2026, 6, 15)
        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.side_effect = RuntimeError("Calendar API down")
            mock_calendar_cls.return_value = mock_service

            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert confirmado.estado == "CONFIRMADO"
        # El caller debe poder commitear los cambios
        await db_session.commit()
        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        db_turno = result.scalar_one()
        assert db_turno.estado == "CONFIRMADO"
        assert db_turno.google_event_id is None


# ---------------------------------------------------------------------------
# 6.7 liberar_reservas_vencidas
# ---------------------------------------------------------------------------

class TestLiberarReservasVencidas:
    @pytest.mark.asyncio
    async def test_liberar_reservas_vencidas(self, db_session, profesional, test_settings):
        """Scenario: reserva con expiración pasada → turno vuelve a DISPONIBLE."""
        from app.services.turno_service import reservar_turno, liberar_reservas_vencidas

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        # Forzar expiración pasada
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one()
        reserva.expiracion = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        liberados = await liberar_reservas_vencidas(db_session, profesional.id)
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
    async def test_liberar_reservas_sin_vencidas(self, db_session, profesional, test_settings):
        """Scenario: no hay reservas vencidas → 0 liberados."""
        from app.services.turno_service import liberar_reservas_vencidas

        liberados = await liberar_reservas_vencidas(db_session, profesional.id)
        assert liberados == 0

    @pytest.mark.asyncio
    async def test_liberar_reservas_vencidas_no_sobrescribe_estado_confirmado(
        self, db_session, profesional, test_settings
    ):
        """Scenario: turno fue confirmado concurrentemente → no se sobreescribe a DISPONIBLE."""
        from app.services.turno_service import reservar_turno, liberar_reservas_vencidas

        fecha = date(2026, 6, 15)
        turno = await reservar_turno(
            db_session,
            profesional_id=profesional.id,
            fecha=fecha,
            hora_inicio=time(9, 0),
            paciente_id=None,
            settings=test_settings,
        )

        # Forzar expiración de la reserva temporal
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one()
        reserva.expiracion = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        # Simular race condition: el turno fue confirmado antes de que el job corra
        turno.estado = "CONFIRMADO"
        await db_session.commit()

        liberados = await liberar_reservas_vencidas(db_session, profesional.id)
        assert liberados == 1  # La reserva temporal se elimina igual

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_actualizado = result.scalar_one()
        assert turno_actualizado.estado == "CONFIRMADO"


# ---------------------------------------------------------------------------
# 6.8 consultar_disponibilidad
# ---------------------------------------------------------------------------

class TestConsultarDisponibilidad:
    @pytest.mark.asyncio
    async def test_consultar_disponibilidad(self, db_session, profesional, test_settings):
        """Scenario: fecha con slots mixtos → solo libres."""
        from app.services.turno_service import reservar_turno, consultar_disponibilidad

        fecha = date(2026, 6, 15)

        # Reservar un slot
        await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        slots = await consultar_disponibilidad(db_session, profesional.id, fecha=fecha)
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
        slots = await consultar_disponibilidad(db_session, p.id, fecha=fecha)
        assert slots == []


# ---------------------------------------------------------------------------
# 6.3 condición de carrera (simulada)
# ---------------------------------------------------------------------------

class TestRaceCondition:
    @pytest.mark.asyncio
    async def test_doble_reserva_concurrente_mismo_slot(self, db_session, profesional, test_settings):
        """Scenario: dos reservas simultáneas sobre mismo slot → solo uno gana."""
        from app.services.turno_service import reservar_turno

        paciente1 = await _seed_paciente(db_session, profesional.id, dni="11111111")
        paciente2 = await _seed_paciente(db_session, profesional.id, dni="22222222")
        fecha = date(2026, 6, 15)

        # In SQLite, concurrent writes on the same session are serialized,
        # so one will succeed and the second will get an exception.
        # We simulate two calls sequentially to show the logic path.
        t1 = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente1.id,
            settings=test_settings,
        )
        assert t1.estado == "RESERVADO_TEMPORAL"

        with pytest.raises(TurnoNoDisponibleError):
            await reservar_turno(
                db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente2.id,
                settings=test_settings,
            )


# ---------------------------------------------------------------------------
# 7.1 cancelar_turno
# ---------------------------------------------------------------------------

class TestReprogramarTurno:
    @pytest.mark.asyncio
    async def test_reprogramar_turno_exitoso(self, db_session, profesional, test_settings):
        """Scenario: cancela viejo, crea nuevo CONFIRMADO, calendar sync."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        fecha = date(2026, 6, 15)
        nueva_fecha = date(2026, 6, 16)

        # Crear y confirmar turno viejo
        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
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
                profesional_id=profesional.id,
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
    async def test_reprogramar_turno_no_existe(self, db_session, profesional):
        """Scenario: turno inexistente → TurnoNoEncontradoError."""
        from app.services.turno_service import reprogramar_turno

        with pytest.raises(TurnoNoEncontradoError):
            await reprogramar_turno(
                db_session, profesional_id=profesional.id, turno_id=99999, nueva_fecha=date(2026, 6, 16), nueva_hora_inicio=time(10, 0)
            )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_ya_cancelado(self, db_session, profesional, test_settings):
        """Scenario: turno ya CANCELADO → TurnoYaCanceladoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno, reprogramar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_123"
        await db_session.commit()
        await cancelar_turno(db_session, profesional.id, turno_id=confirmado.id)

        with pytest.raises(TurnoYaCanceladoError):
            await reprogramar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=confirmado.id,
                nueva_fecha=date(2026, 6, 16),
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_slot_no_disponible(self, db_session, profesional, test_settings):
        """Scenario: slot ocupado → TurnoNoDisponibleError, viejo queda CANCELADO."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        fecha = date(2026, 6, 15)

        # Ocupar el slot 10:00
        t_ocupado = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_ocupado"
            mock_calendar_cls.return_value = mock_service
            await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=t_ocupado.id,
                paciente_data={"nombre": "Ana", "apellido": "Garcia", "dni": "87654321", "telefono": "555-9999"},
            )
        t_ocupado.google_event_id = "event_ocupado"
        await db_session.commit()

        # Crear turno a reprogramar
        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
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
                    profesional_id=profesional.id,
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
    async def test_reprogramar_turno_paciente_con_otro_activo(self, db_session, profesional, test_settings):
        """Scenario: paciente tiene otro turno activo → PacienteConTurnoActivoError (RN-TU-01)."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)

        # Turno 1: confirmado del paciente
        t1 = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=paciente.id,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_t1"
            mock_calendar_cls.return_value = mock_service
            await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=t1.id,
                paciente_data={"nombre": paciente.nombre, "apellido": paciente.apellido, "dni": paciente.dni, "telefono": paciente.telefono},
            )
        t1.google_event_id = "event_t1"
        await db_session.commit()

        # Turno 2: confirmado de otro paciente (para reprogramar)
        t2 = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_t2"
            mock_calendar_cls.return_value = mock_service
            confirmado2 = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
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
                    profesional_id=profesional.id,
                    turno_id=confirmado2.id,
                    nueva_fecha=fecha,
                    nueva_hora_inicio=time(11, 0),
                    paciente_data={"nombre": paciente.nombre, "apellido": paciente.apellido, "dni": paciente.dni, "telefono": paciente.telefono},
                    settings=test_settings,
                )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_calendar_create_falla(self, db_session, profesional, test_settings):
        """Scenario: calendar create falla → nuevo turno sigue CONFIRMADO, log error."""
        from app.services.turno_service import reservar_turno, confirmar_turno, reprogramar_turno

        fecha = date(2026, 6, 15)
        nueva_fecha = date(2026, 6, 16)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
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
                profesional_id=profesional.id,
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
    async def test_reprogramar_turno_reservado_temporal(self, db_session, profesional, test_settings):
        """Scenario: turno RESERVADO_TEMPORAL no puede reprogramarse → error."""
        from app.services.turno_service import reservar_turno, reprogramar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with pytest.raises(TurnoNoDisponibleError):
            await reprogramar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                nueva_fecha=fecha,
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

    @pytest.mark.asyncio
    async def test_reprogramar_turno_propaga_google_event_id(self, db_session, profesional, test_settings):
        """Scenario: reprogramar lee event_id viejo y persiste event_id nuevo."""
        from app.services.turno_service import reprogramar_turno

        fecha = date(2026, 6, 15)
        nueva_fecha = date(2026, 6, 16)

        # Crear turno confirmado con google_event_id persistido
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=profesional.id, paciente_id=None,
            google_event_id="event_old",
        )
        db_session.add(turno)
        await db_session.commit()

        # Crear paciente y asociarlo
        paciente = await _seed_paciente(db_session, profesional.id)
        turno.paciente_id = paciente.id
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_new"
            mock_calendar_cls.return_value = mock_service

            nuevo = await reprogramar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                nueva_fecha=nueva_fecha,
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

        assert nuevo.estado == "CONFIRMADO"
        assert nuevo.google_event_id == "event_new"
        mock_service.delete_event.assert_called_once_with("event_old")

    @pytest.mark.asyncio
    async def test_reprogramar_turno_sin_google_event_id_no_delete(self, db_session, profesional, test_settings):
        """Scenario: reprogramar turno con google_event_id=NULL no invoca delete_event."""
        from app.services.turno_service import reprogramar_turno

        fecha = date(2026, 6, 15)
        nueva_fecha = date(2026, 6, 16)

        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=profesional.id, paciente_id=None,
            google_event_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        paciente = await _seed_paciente(db_session, profesional.id)
        turno.paciente_id = paciente.id
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_new"
            mock_calendar_cls.return_value = mock_service

            nuevo = await reprogramar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                nueva_fecha=nueva_fecha,
                nueva_hora_inicio=time(10, 0),
                settings=test_settings,
            )

        assert nuevo.estado == "CONFIRMADO"
        mock_service.delete_event.assert_not_called()


class TestCancelarTurno:
    @pytest.mark.asyncio
    async def test_cancelar_turno_exitoso(self, db_session, profesional, test_settings):
        """Scenario: turno CONFIRMADO → CANCELADO, calendar event eliminado."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno

        fecha = date(2026, 6, 15)

        # Crear y confirmar turno
        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        # Set google_event_id manually (normally set by calendar service in real flow)
        confirmado.google_event_id = "event_123"
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            cancelado = await cancelar_turno(db_session, profesional.id, turno_id=confirmado.id)

        assert cancelado.estado == "CANCELADO"
        mock_service.delete_event.assert_called_once_with("event_123")

    @pytest.mark.asyncio
    async def test_cancelar_turno_no_existe(self, db_session, profesional):
        """Scenario: turno inexistente → TurnoNoEncontradoError."""
        from app.services.turno_service import cancelar_turno

        with pytest.raises(TurnoNoEncontradoError):
            await cancelar_turno(db_session, profesional.id, turno_id=99999)

    @pytest.mark.asyncio
    async def test_cancelar_turno_ya_cancelado(self, db_session, profesional, test_settings):
        """Scenario: turno ya CANCELADO → TurnoYaCanceladoError."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_123"
        await db_session.commit()

        # Primera cancelación exitosa
        await cancelar_turno(db_session, profesional.id, turno_id=confirmado.id)

        # Segunda cancelación debe fallar
        with pytest.raises(TurnoYaCanceladoError):
            await cancelar_turno(db_session, profesional.id, turno_id=confirmado.id)

    @pytest.mark.asyncio
    async def test_cancelar_turno_calendar_falla(self, db_session, profesional, test_settings):
        """Scenario: calendar delete falla → turno sigue CANCELADO, log error."""
        from app.services.turno_service import reservar_turno, confirmar_turno, cancelar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await confirmar_turno(
                db_session,
                profesional_id=profesional.id,
                turno_id=turno.id,
                paciente_data={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        confirmado.google_event_id = "event_123"
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.delete_event.side_effect = RuntimeError("Calendar API down")
            mock_calendar_cls.return_value = mock_service

            cancelado = await cancelar_turno(db_session, profesional.id, turno_id=confirmado.id)

        assert cancelado.estado == "CANCELADO"
        mock_service.delete_event.assert_called_once_with("event_123")

    @pytest.mark.asyncio
    async def test_cancelar_turno_reservado_temporal(self, db_session, profesional, test_settings):
        """Scenario: turno RESERVADO_TEMPORAL no puede cancelarse → error."""
        from app.services.turno_service import reservar_turno, cancelar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        with pytest.raises(TurnoYaCanceladoError):
            await cancelar_turno(db_session, profesional.id, turno_id=turno.id)


# ---------------------------------------------------------------------------
# C-13: Transición a COMPLETADO
# ---------------------------------------------------------------------------

class TestMarcarTurnosCompletados:
    @pytest.mark.asyncio
    async def test_marcar_turnos_completados_pasado(self, db_session, profesional, test_settings):
        """Scenario: turno CONFIRMADO pasado se marca COMPLETADO."""
        from app.services.turno_service import marcar_turnos_completados

        paciente = await _seed_paciente(db_session, profesional.id)

        turno = Turno(
            fecha=date(2020, 1, 1),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        actualizados = await marcar_turnos_completados(db_session, profesional.id)
        assert actualizados == 1

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.estado == "COMPLETADO"

    @pytest.mark.asyncio
    async def test_marcar_turnos_completados_futuro(self, db_session, profesional, test_settings):
        """Scenario: turno CONFIRMADO futuro no se modifica."""
        from app.services.turno_service import marcar_turnos_completados

        paciente = await _seed_paciente(db_session, profesional.id)

        turno = Turno(
            fecha=date(2099, 1, 1),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        actualizados = await marcar_turnos_completados(db_session, profesional.id)
        assert actualizados == 0

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_marcar_turnos_completados_cancelado_pasado(self, db_session, profesional, test_settings):
        """Scenario: turno CANCELADO pasado no se modifica."""
        from app.services.turno_service import marcar_turnos_completados

        paciente = await _seed_paciente(db_session, profesional.id)

        turno = Turno(
            fecha=date(2020, 1, 1),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CANCELADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        actualizados = await marcar_turnos_completados(db_session, profesional.id)
        assert actualizados == 0

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.estado == "CANCELADO"

    @pytest.mark.asyncio
    async def test_cancelar_turno_lee_google_event_id_de_db(self, db_session, profesional, test_settings):
        """Scenario: cancelar turno con google_event_id en DB invoca delete_event."""
        from app.services.turno_service import cancelar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)

        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=profesional.id, paciente_id=paciente.id,
            google_event_id="event_456",
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            cancelado = await cancelar_turno(db_session, profesional.id, turno_id=turno.id)

        assert cancelado.estado == "CANCELADO"
        mock_service.delete_event.assert_called_once_with("event_456")

    @pytest.mark.asyncio
    async def test_cancelar_turno_sin_google_event_id_no_llama_delete(self, db_session, profesional, test_settings):
        """Scenario: cancelar turno con google_event_id=NULL no invoca delete_event."""
        from app.services.turno_service import cancelar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)

        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=profesional.id, paciente_id=paciente.id,
            google_event_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            cancelado = await cancelar_turno(db_session, profesional.id, turno_id=turno.id)

        assert cancelado.estado == "CANCELADO"
        mock_service.delete_event.assert_not_called()


# ---------------------------------------------------------------------------
# C-11: Hook post-cancelación y post-expiración
# ---------------------------------------------------------------------------

class TestHookListaEspera:
    @pytest.mark.asyncio
    async def test_cancelar_turno_dispara_evaluar_lista_espera(self, db_session, profesional, test_settings):
        """Scenario: cancelar turno CONFIRMADO dispara evaluar_lista_espera."""
        from app.services.turno_service import cancelar_turno

        paciente = await _seed_paciente(db_session, profesional.id)
        fecha = date(2026, 6, 15)

        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=profesional.id, paciente_id=paciente.id,
            google_event_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            with patch("app.services.lista_espera_service.evaluar_lista_espera", new=AsyncMock()) as mock_evaluar:
                cancelado = await cancelar_turno(db_session, profesional.id, turno_id=turno.id)

        assert cancelado.estado == "CANCELADO"
        mock_evaluar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_liberar_reservas_vencidas_dispara_evaluar_lista_espera(self, db_session, profesional, test_settings):
        """Scenario: liberar reservas vencidas dispara evaluar_lista_espera por turno liberado."""
        from app.services.turno_service import reservar_turno, liberar_reservas_vencidas

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )

        # Forzar expiración pasada
        from app.models.reserva_temporal import ReservaTemporal
        from sqlalchemy import select
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one()
        reserva.expiracion = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        with patch("app.services.lista_espera_service.evaluar_lista_espera", new=AsyncMock()) as mock_evaluar:
            liberados = await liberar_reservas_vencidas(db_session, profesional.id)

        assert liberados >= 1
        mock_evaluar.assert_awaited()


# ---------------------------------------------------------------------------
# C-13: google_event_id persistence
# ---------------------------------------------------------------------------

class TestGoogleEventId:
    @pytest.mark.asyncio
    async def test_turno_model_acepta_google_event_id(self, db_session, profesional, test_settings):
        """Scenario: Turno acepta y persiste google_event_id."""
        from app.services.turno_service import reservar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        turno.google_event_id = "event_abc123"
        await db_session.commit()
        await db_session.refresh(turno)

        assert turno.google_event_id == "event_abc123"

    @pytest.mark.asyncio
    async def test_turno_model_google_event_id_nullable(self, db_session, profesional, test_settings):
        """Scenario: google_event_id puede ser NULL."""
        from app.services.turno_service import reservar_turno

        fecha = date(2026, 6, 15)

        turno = await reservar_turno(
            db_session, profesional_id=profesional.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None,
            settings=test_settings,
        )
        await db_session.commit()
        await db_session.refresh(turno)

        assert turno.google_event_id is None

    def test_alembic_migration_adds_google_event_id(self):
        """Scenario: la migración Alembic agrega la columna google_event_id."""
        import os
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        # Allow running from repo root or backend/
        alembic_ini = "alembic.ini" if os.path.exists("alembic.ini") else "backend/alembic.ini"
        alembic_cfg = Config(alembic_ini)
        script = ScriptDirectory.from_config(alembic_cfg)
        # Verify the migration exists and is reachable from head
        head = script.get_current_head()
        assert head is not None
        # Walk the history to find the migration that adds google_event_id
        found = False
        for rev in script.walk_revisions():
            if rev.path is not None:
                with open(rev.path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "google_event_id" in content and "add_column" in content:
                    found = True
                    break
        assert found, "No migration found that adds google_event_id"
