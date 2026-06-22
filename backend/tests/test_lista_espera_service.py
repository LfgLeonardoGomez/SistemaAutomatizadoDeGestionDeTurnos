import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.lista_de_espera import ListaDeEspera
from app.config import Settings


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")


@pytest.fixture
def test_settings():
    return Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        telegram_bot_token="test",
        google_calendar_credentials='{"type": "service_account"}',
        google_calendar_id="primary",
        lista_espera_minutos=5,
    )


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


async def _seed_paciente(db_session: AsyncSession, dni: str = "12345678", nombre: str = "Juan", telefono: str = "555-1234") -> Paciente:
    paciente = Paciente(
        nombre=nombre, apellido="Perez", dni=dni, telefono=telefono
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


async def _seed_turno(
    db_session: AsyncSession,
    profesional_id: int,
    fecha: date = date(2026, 6, 15),
    hora_inicio: time = time(9, 0),
    estado: str = "CONFIRMADO",
    paciente_id: Optional[int] = None,
) -> Turno:
    inicio_min = hora_inicio.hour * 60 + hora_inicio.minute
    fin_min = inicio_min + 30
    hora_fin = time(fin_min // 60, fin_min % 60)
    turno = Turno(
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        estado=estado,
        profesional_id=profesional_id,
        paciente_id=paciente_id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)
    return turno


async def _seed_lista_espera(
    db_session: AsyncSession,
    paciente_id: int,
    fecha_solicitada: date = date(2026, 6, 15),
    telegram_chat_id: Optional[str] = "12345",
) -> ListaDeEspera:
    registro = ListaDeEspera(
        paciente_id=paciente_id,
        fecha_solicitada=fecha_solicitada,
        telegram_chat_id=telegram_chat_id,
    )
    db_session.add(registro)
    await db_session.commit()
    await db_session.refresh(registro)
    return registro


# ---------------------------------------------------------------------------
# 3.1 registrar_en_lista_espera
# ---------------------------------------------------------------------------

class TestRegistrarEnListaEspera:
    @pytest.mark.asyncio
    async def test_registrar_en_lista_espera_exitoso(self, db_session, test_settings):
        from app.services.lista_espera_service import registrar_en_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        fecha = date(2026, 6, 15)

        registro = await registrar_en_lista_espera(
            db_session, paciente_id=paciente.id, fecha_solicitada=fecha, telegram_chat_id="12345"
        )

        assert registro.id is not None
        assert registro.paciente_id == paciente.id
        assert registro.fecha_solicitada == fecha
        assert registro.notificado is False
        assert registro.turno_ofrecido_id is None
        assert registro.notificado_en is None
        assert registro.telegram_chat_id == "12345"

    @pytest.mark.asyncio
    async def test_registrar_en_lista_espera_paciente_inexistente(self, db_session, test_settings):
        from app.services.lista_espera_service import registrar_en_lista_espera
        from app.exceptions import TurnoNoEncontradoError

        with pytest.raises(TurnoNoEncontradoError):
            await registrar_en_lista_espera(
                db_session, paciente_id=99999, fecha_solicitada=date(2026, 6, 15), telegram_chat_id="12345"
            )


# ---------------------------------------------------------------------------
# 3.1 eliminar_de_lista_espera
# ---------------------------------------------------------------------------

class TestEliminarDeListaEspera:
    @pytest.mark.asyncio
    async def test_eliminar_de_lista_espera_exitoso(self, db_session, test_settings):
        from app.services.lista_espera_service import eliminar_de_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)

        await eliminar_de_lista_espera(db_session, lista_espera_id=registro.id)

        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_eliminar_de_lista_espera_inexistente(self, db_session, test_settings):
        from app.services.lista_espera_service import eliminar_de_lista_espera
        from app.exceptions import TurnoNoEncontradoError

        with pytest.raises(TurnoNoEncontradoError):
            await eliminar_de_lista_espera(db_session, lista_espera_id=99999)


# ---------------------------------------------------------------------------
# 3.1 obtener_siguiente_paciente_fifo
# ---------------------------------------------------------------------------

class TestObtenerSiguientePacienteFifo:
    @pytest.mark.asyncio
    async def test_obtener_siguiente_paciente_fifo_orden_correcto(self, db_session, test_settings):
        from app.services.lista_espera_service import obtener_siguiente_paciente_fifo

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, dni="11111111")
        paciente2 = await _seed_paciente(db_session, dni="22222222")
        fecha = date(2026, 6, 15)

        registro1 = await _seed_lista_espera(db_session, paciente_id=paciente1.id, fecha_solicitada=fecha)
        registro2 = await _seed_lista_espera(db_session, paciente_id=paciente2.id, fecha_solicitada=fecha)

        siguiente = await obtener_siguiente_paciente_fifo(db_session, fecha=fecha)
        assert siguiente is not None
        assert siguiente.id == registro1.id

    @pytest.mark.asyncio
    async def test_obtener_siguiente_paciente_fifo_ignora_notificados(self, db_session, test_settings):
        from app.services.lista_espera_service import obtener_siguiente_paciente_fifo

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, dni="11111111")
        paciente2 = await _seed_paciente(db_session, dni="22222222")
        fecha = date(2026, 6, 15)

        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro1 = await _seed_lista_espera(db_session, paciente_id=paciente1.id, fecha_solicitada=fecha)
        registro1.notificado = True
        registro1.turno_ofrecido_id = turno.id
        await db_session.commit()

        registro2 = await _seed_lista_espera(db_session, paciente_id=paciente2.id, fecha_solicitada=fecha)

        siguiente = await obtener_siguiente_paciente_fifo(db_session, fecha=fecha)
        assert siguiente is not None
        assert siguiente.id == registro2.id

    @pytest.mark.asyncio
    async def test_obtener_siguiente_paciente_fifo_sin_registros(self, db_session, test_settings):
        from app.services.lista_espera_service import obtener_siguiente_paciente_fifo

        fecha = date(2026, 6, 15)
        siguiente = await obtener_siguiente_paciente_fifo(db_session, fecha=fecha)
        assert siguiente is None


# ---------------------------------------------------------------------------
# 3.1 notificar_y_marcar
# ---------------------------------------------------------------------------

class TestNotificarYMarcar:
    @pytest.mark.asyncio
    async def test_notificar_y_marcar_actualiza_db(self, db_session, test_settings):
        from app.services.lista_espera_service import notificar_y_marcar

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)

        with patch("app.services.lista_espera_service.enviar_notificacion_lista_espera", new=AsyncMock()) as mock_enviar:
            await notificar_y_marcar(
                db_session, lista_espera_id=registro.id, turno_id=turno.id, chat_id="12345"
            )

        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        actualizado = result.scalar_one()
        assert actualizado.notificado is True
        assert actualizado.turno_ofrecido_id == turno.id
        assert actualizado.notificado_en is not None
        mock_enviar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notificar_y_marcar_falla_telegram_no_marca(self, db_session, test_settings):
        from app.services.lista_espera_service import notificar_y_marcar

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)

        with patch("app.services.lista_espera_service.enviar_notificacion_lista_espera", new=AsyncMock(side_effect=Exception("Telegram down"))) as mock_enviar:
            await notificar_y_marcar(
                db_session, lista_espera_id=registro.id, turno_id=turno.id, chat_id="12345"
            )

        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        actualizado = result.scalar_one()
        assert actualizado.notificado is False
        assert actualizado.turno_ofrecido_id is None
        assert actualizado.notificado_en is None
        mock_enviar.assert_awaited_once()


# ---------------------------------------------------------------------------
# 3.1 aceptar_turno_lista_espera
# ---------------------------------------------------------------------------

class TestAceptarTurnoListaEspera:
    @pytest.mark.asyncio
    async def test_aceptar_turno_lista_espera_exitoso(self, db_session, test_settings):
        from app.services.lista_espera_service import aceptar_turno_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)
        registro.turno_ofrecido_id = turno.id
        registro.notificado = True
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            confirmado = await aceptar_turno_lista_espera(
                db_session, lista_espera_id=registro.id
            )

        assert confirmado.estado == "CONFIRMADO"
        assert confirmado.paciente_id == paciente.id
        assert confirmado.fecha == turno.fecha
        assert confirmado.hora_inicio == turno.hora_inicio

        # Registro eliminado
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_aceptar_turno_lista_espera_inexistente(self, db_session, test_settings):
        from app.services.lista_espera_service import aceptar_turno_lista_espera
        from app.exceptions import TurnoNoEncontradoError

        with pytest.raises(TurnoNoEncontradoError):
            await aceptar_turno_lista_espera(db_session, lista_espera_id=99999)


# ---------------------------------------------------------------------------
# 3.1 rechazar_turno_lista_espera
# ---------------------------------------------------------------------------

class TestRechazarTurnoListaEspera:
    @pytest.mark.asyncio
    async def test_rechazar_turno_lista_espera_resetea_y_reevalua(self, db_session, test_settings):
        from app.services.lista_espera_service import rechazar_turno_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)
        registro.turno_ofrecido_id = turno.id
        registro.notificado = True
        registro.notificado_en = datetime.now()
        await db_session.commit()

        with patch("app.services.lista_espera_service.evaluar_lista_espera", new=AsyncMock()) as mock_evaluar:
            await rechazar_turno_lista_espera(
                db_session, lista_espera_id=registro.id, turno_id=turno.id
            )

        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        actualizado = result.scalar_one()
        assert actualizado.notificado is False
        assert actualizado.turno_ofrecido_id is None
        assert actualizado.notificado_en is None
        mock_evaluar.assert_awaited_once_with(db_session, fecha=turno.fecha, turno_id=turno.id)

    @pytest.mark.asyncio
    async def test_rechazar_turno_lista_espera_inexistente(self, db_session, test_settings):
        from app.services.lista_espera_service import rechazar_turno_lista_espera
        from app.exceptions import TurnoNoEncontradoError

        with pytest.raises(TurnoNoEncontradoError):
            await rechazar_turno_lista_espera(db_session, lista_espera_id=99999, turno_id=1)


# ---------------------------------------------------------------------------
# 3.1 procesar_timeouts
# ---------------------------------------------------------------------------

class TestProcesarTimeouts:
    @pytest.mark.asyncio
    async def test_procesar_timeouts_resetea_vencidos(self, db_session, test_settings):
        from app.services.lista_espera_service import procesar_timeouts_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)
        registro.turno_ofrecido_id = turno.id
        registro.notificado = True
        registro.notificado_en = datetime.now() - timedelta(minutes=10)
        await db_session.commit()

        with patch("app.services.lista_espera_service.evaluar_lista_espera", new=AsyncMock()) as mock_evaluar:
            procesados = await procesar_timeouts_lista_espera(
                db_session, minutos_timeout=test_settings.lista_espera_minutos
            )

        assert procesados == 1
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        actualizado = result.scalar_one()
        assert actualizado.notificado is False
        assert actualizado.turno_ofrecido_id is None
        assert actualizado.notificado_en is None
        mock_evaluar.assert_awaited_once_with(db_session, fecha=turno.fecha, turno_id=turno.id)

    @pytest.mark.asyncio
    async def test_procesar_timeouts_no_actua_sobre_recientes(self, db_session, test_settings):
        from app.services.lista_espera_service import procesar_timeouts_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id)
        registro.turno_ofrecido_id = turno.id
        registro.notificado = True
        registro.notificado_en = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        with patch("app.services.lista_espera_service.evaluar_lista_espera", new=AsyncMock()) as mock_evaluar:
            procesados = await procesar_timeouts_lista_espera(
                db_session, minutos_timeout=test_settings.lista_espera_minutos
            )

        assert procesados == 0
        mock_evaluar.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_procesar_timeouts_sin_registros(self, db_session, test_settings):
        from app.services.lista_espera_service import procesar_timeouts_lista_espera

        procesados = await procesar_timeouts_lista_espera(
            db_session, minutos_timeout=test_settings.lista_espera_minutos
        )
        assert procesados == 0


# ---------------------------------------------------------------------------
# 4.1 evaluar_lista_espera (hook)
# ---------------------------------------------------------------------------

class TestEvaluarListaEspera:
    @pytest.mark.asyncio
    async def test_evaluar_lista_espera_notifica_siguiente(self, db_session, test_settings):
        from app.services.lista_espera_service import evaluar_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")
        registro = await _seed_lista_espera(db_session, paciente_id=paciente.id, fecha_solicitada=turno.fecha)

        with patch("app.services.lista_espera_service.notificar_y_marcar", new=AsyncMock()) as mock_notificar:
            await evaluar_lista_espera(db_session, fecha=turno.fecha)

        mock_notificar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_evaluar_lista_espera_sin_pacientes_no_notifica(self, db_session, test_settings):
        from app.services.lista_espera_service import evaluar_lista_espera

        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, profesional_id=p.id, estado="CANCELADO")

        with patch("app.services.lista_espera_service.notificar_y_marcar", new=AsyncMock()) as mock_notificar:
            await evaluar_lista_espera(db_session, fecha=turno.fecha)

        mock_notificar.assert_not_awaited()
