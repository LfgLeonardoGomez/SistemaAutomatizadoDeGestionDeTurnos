"""Tests del servicio de recordatorios (C-24).

Cubre ``run_recordatorios_para_todos``: itera profesionales activos,
llama a ``obtener_turnos_para_recordar`` + ``enviar_recordatorio_telegram``
+ ``marcar_recordatorio_enviado`` con Patrón A (commit por profesional)
y try/except por profesional.
"""
import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, AsyncMock

from sqlalchemy import select

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.schemas.recordatorio import RecordatorioRunResponse
from app.services.recordatorio_service import run_recordatorios_para_todos
from tests.conftest import make_profesional


async def _seed_profesional(db_session, **overrides) -> Profesional:
    p = make_profesional(**overrides)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, profesional_id: int, dni: str = "12345678") -> Paciente:
    paciente = Paciente(
        nombre="Juan",
        apellido="Perez",
        dni=dni,
        telefono="555-1234",
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


async def _add_destinatario_telegram(db_session, turno_id: int, chat_id: str) -> TurnoDestinatario:
    dest = TurnoDestinatario(
        turno_id=turno_id,
        canal="TELEGRAM",
        destinatario=chat_id,
    )
    db_session.add(dest)
    await db_session.commit()
    await db_session.refresh(dest)
    return dest


def _mañana() -> date:
    return date.today() + timedelta(days=1)


class TestRunRecordatoriosParaTodosVacio:
    """Sin profesionales activos, la respuesta es vacía."""

    @pytest.mark.asyncio
    async def test_sin_profesionales_retorna_todo_cero(self, db_session):
        resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())
        assert isinstance(resp, RecordatorioRunResponse)
        assert resp.total_candidatos == 0
        assert resp.total_enviados == 0
        assert resp.total_fallidos == 0
        assert resp.errores == []

    @pytest.mark.asyncio
    async def test_solo_profesionales_inactivos_no_iteran(self, db_session):
        await _seed_profesional(db_session, is_active=False, telegram_bot_token="x")
        resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())
        assert resp.total_candidatos == 0
        assert resp.errores == []


class TestRunRecordatoriosParaTodosExito:
    """Casos happy path: 1 profesional + 1 turno, envío OK."""

    @pytest.mark.asyncio
    async def test_un_profesional_un_turno_con_destinatario_envia_y_marca(self, db_session):
        prof = await _seed_profesional(db_session, telegram_bot_token="bot_test")
        paciente = await _seed_paciente(db_session, prof.id, dni="11111111")

        base_dt = datetime.now() + timedelta(hours=2)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        await _add_destinatario_telegram(db_session, turno.id, "chat-1")
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ) as mock_enviar, patch(
            "app.services.recordatorio_service.marcar_recordatorio_enviado",
            new=AsyncMock(),
        ) as mock_marcar:
            resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())

        assert resp.fecha == _mañana()
        assert resp.total_candidatos == 1
        assert resp.total_enviados == 1
        assert resp.total_fallidos == 0
        assert resp.errores == []
        assert mock_enviar.await_count == 1
        assert mock_marcar.await_count == 1

    @pytest.mark.asyncio
    async def test_turno_sin_destinatario_telegram_se_marca_como_enviado(self, db_session):
        """Sin destinatario TELEGRAM: enviar_recordatorio_telegram retorna True (warning),
        se marca como enviado, NO se registra error."""
        prof = await _seed_profesional(db_session, telegram_bot_token="bot_test")
        paciente = await _seed_paciente(db_session, prof.id, dni="22222222")

        base_dt = datetime.now() + timedelta(hours=2)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        # NO se agrega destinatario TELEGRAM
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.recordatorio_service.marcar_recordatorio_enviado",
            new=AsyncMock(),
        ) as mock_marcar:
            resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())

        assert resp.total_candidatos == 1
        assert resp.total_enviados == 1
        assert resp.total_fallidos == 0
        assert resp.errores == []
        assert mock_marcar.await_count == 1


class TestRunRecordatoriosParaTodosFalloEnvio:
    """Casos donde enviar_recordatorio_telegram retorna False."""

    @pytest.mark.asyncio
    async def test_envio_falla_no_marca_y_reporta_error(self, db_session):
        prof = await _seed_profesional(db_session, telegram_bot_token="bot_test")
        paciente = await _seed_paciente(db_session, prof.id, dni="33333333")

        base_dt = datetime.now() + timedelta(hours=2)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        await _add_destinatario_telegram(db_session, turno.id, "chat-x")
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.services.recordatorio_service.marcar_recordatorio_enviado",
            new=AsyncMock(),
        ) as mock_marcar:
            resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())

        assert resp.total_candidatos == 1
        assert resp.total_enviados == 0
        assert resp.total_fallidos == 1
        assert len(resp.errores) == 1
        assert resp.errores[0].profesional_id == prof.id
        assert resp.errores[0].turno_id == turno.id
        assert "fall" in resp.errores[0].mensaje.lower() or "envi" in resp.errores[0].mensaje.lower()
        # NO se marca recordatorio_enviado cuando el envío falla
        assert mock_marcar.await_count == 0


class TestRunRecordatoriosParaTodosProfesionalSinBotToken:
    """Profesional sin telegram_bot_token se saltea con warning."""

    @pytest.mark.asyncio
    async def test_profesional_sin_telegram_bot_token_se_saltea(self, db_session):
        prof = await _seed_profesional(db_session, telegram_bot_token=None)
        paciente = await _seed_paciente(db_session, prof.id, dni="44444444")

        base_dt = datetime.now() + timedelta(hours=2)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        await _add_destinatario_telegram(db_session, turno.id, "chat-y")
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ) as mock_enviar:
            resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())

        # El profesional se saltea: no se procesa ningún turno
        assert resp.total_candidatos == 0
        assert resp.total_enviados == 0
        assert resp.total_fallidos == 0
        assert resp.errores == []
        assert mock_enviar.await_count == 0


class TestRunRecordatoriosParaTodosMultiProfesional:
    """Múltiples profesionales: el batch continúa si uno falla."""

    @pytest.mark.asyncio
    async def test_dos_profesionales_primero_falla_segundo_ok(self, db_session):
        prof_a = await _seed_profesional(
            db_session,
            nombre="Dr. A",
            dias_atencion=["Lunes"],
            telegram_bot_token="bot_a",
        )
        prof_b = await _seed_profesional(
            db_session,
            nombre="Dr. B",
            dias_atencion=["Martes"],
            telegram_bot_token="bot_b",
        )

        paciente_a = await _seed_paciente(db_session, prof_a.id, dni="55555555")
        paciente_b = await _seed_paciente(db_session, prof_b.id, dni="66666666")

        base_dt = datetime.now() + timedelta(hours=2)
        turno_a = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof_a.id,
            paciente_id=paciente_a.id,
            recordatorio_enviado=False,
        )
        turno_b = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof_b.id,
            paciente_id=paciente_b.id,
            recordatorio_enviado=False,
        )
        db_session.add_all([turno_a, turno_b])
        await db_session.commit()
        await db_session.refresh(turno_a)
        await db_session.refresh(turno_b)
        await _add_destinatario_telegram(db_session, turno_a.id, "chat-a")
        await _add_destinatario_telegram(db_session, turno_b.id, "chat-b")
        await db_session.refresh(turno_a, attribute_names=["destinatarios"])
        await db_session.refresh(turno_b, attribute_names=["destinatarios"])

        async def _enviar_side_effect(turno, bot_token):
            if bot_token == "bot_a":
                return False
            return True

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            side_effect=_enviar_side_effect,
        ):
            resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())

        # 2 candidatos: 1 OK (Dr. B), 1 falla (Dr. A)
        assert resp.total_candidatos == 2
        assert resp.total_enviados == 1
        assert resp.total_fallidos == 1
        assert len(resp.errores) == 1
        assert resp.errores[0].profesional_id == prof_a.id
        assert resp.errores[0].turno_id == turno_a.id

    @pytest.mark.asyncio
    async def test_excepcion_en_un_profesional_no_aborta_batch(self, db_session):
        """Si ``enviar_recordatorio_telegram`` lanza excepción, el batch continúa."""
        prof_a = await _seed_profesional(
            db_session,
            nombre="Dr. A",
            dias_atencion=["Lunes"],
            telegram_bot_token="bot_a",
        )
        prof_b = await _seed_profesional(
            db_session,
            nombre="Dr. B",
            dias_atencion=["Martes"],
            telegram_bot_token="bot_b",
        )

        paciente_a = await _seed_paciente(db_session, prof_a.id, dni="77777777")
        paciente_b = await _seed_paciente(db_session, prof_b.id, dni="88888888")

        base_dt = datetime.now() + timedelta(hours=2)
        turno_a = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof_a.id,
            paciente_id=paciente_a.id,
            recordatorio_enviado=False,
        )
        turno_b = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof_b.id,
            paciente_id=paciente_b.id,
            recordatorio_enviado=False,
        )
        db_session.add_all([turno_a, turno_b])
        await db_session.commit()
        await db_session.refresh(turno_a)
        await db_session.refresh(turno_b)
        await _add_destinatario_telegram(db_session, turno_a.id, "chat-a")
        await _add_destinatario_telegram(db_session, turno_b.id, "chat-b")
        await db_session.refresh(turno_a, attribute_names=["destinatarios"])
        await db_session.refresh(turno_b, attribute_names=["destinatarios"])

        async def _enviar_side_effect(turno, bot_token):
            if bot_token == "bot_a":
                raise RuntimeError("Telegram API timeout")
            return True

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            side_effect=_enviar_side_effect,
        ):
            resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())

        # turno_a levanta excepción → no se cuenta como candidato del batch global
        # (try/except exterior aísla el profesional); turno_b se procesa OK.
        assert resp.total_enviados == 1
        assert resp.total_fallidos == 1
        assert len(resp.errores) == 1
        assert resp.errores[0].profesional_id == prof_a.id


class TestRunRecordatoriosParaTodosPersistencia:
    """Patrón A: el service hace commit por profesional."""

    @pytest.mark.asyncio
    async def test_se_hace_commit_despues_de_cada_profesional(self, db_session):
        """Verifica que el flag ``recordatorio_enviado`` persiste en la DB
        cuando el envío fue OK (sin mockear ``marcar_recordatorio_enviado``)."""
        prof = await _seed_profesional(db_session, telegram_bot_token="bot_test")
        paciente = await _seed_paciente(db_session, prof.id, dni="99999999")

        base_dt = datetime.now() + timedelta(hours=2)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=prof.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        await _add_destinatario_telegram(db_session, turno.id, "chat-z")
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ):
            await run_recordatorios_para_todos(db_session, fecha=_mañana())

        # Re-leer el turno en una nueva operación (el db_session está
        # en el mismo loop, así que el commit previo ya es visible)
        result = await db_session.execute(
            select(Turno).where(Turno.id == turno.id)
        )
        turno_db = result.scalar_one()
        assert turno_db.recordatorio_enviado is True


class TestRunRecordatoriosParaTodosSinTurnos:
    """Profesionales activos pero sin turnos en la ventana."""

    @pytest.mark.asyncio
    async def test_sin_turnos_en_ventana_retorna_vacio(self, db_session):
        await _seed_profesional(db_session, telegram_bot_token="bot_x")
        resp = await run_recordatorios_para_todos(db_session, fecha=_mañana())
        assert resp.total_candidatos == 0
        assert resp.total_enviados == 0
        assert resp.errores == []
