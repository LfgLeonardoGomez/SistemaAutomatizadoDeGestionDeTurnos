"""Tests de integración del router de recordatorios (C-24).

Cubre ``POST /api/v1/recordatorios/run`` con auth ``X-API-Key``:
- 401 sin header / 401 con key inválida
- 200 con header válido + payload (con y sin candidatos)
- 422 con fecha inválida
- 200 con fecha pasada sin candidatos
- El turno candidato queda con ``recordatorio_enviado=True`` tras el commit.
"""
import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, AsyncMock

from sqlalchemy import select

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.services.auth_service import set_profesional_api_key
from tests.conftest import make_profesional


async def _seed_profesional_con_api_key(db_session, **overrides) -> Profesional:
    """Crea un Profesional persistido con api_key asignada."""
    p = make_profesional(**overrides)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    await set_profesional_api_key(db_session, p)
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


def _mañana_iso() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


class TestRecordatoriosRouterAuth:
    """Auth con X-API-Key."""

    def test_sin_api_key_retorna_401_o_403_o_422(self, client):
        """Sin X-API-Key el endpoint rechaza la request.

        FastAPI con ``Header(alias="X-API-Key")`` sin default suele
        devolver 422 (Pydantic validation del header faltante), pero
        aceptamos 401/403 también — lo importante es que NO es 200.
        """
        response = client.post(f"/api/v1/recordatorios/run?fecha={_mañana_iso()}")
        assert response.status_code in (401, 403, 422)

    def test_api_key_invalida_retorna_401(self, client):
        response = client.post(
            f"/api/v1/recordatorios/run?fecha={_mañana_iso()}",
            headers={"X-API-Key": "this-key-does-not-exist"},
        )
        assert response.status_code == 401


class TestRecordatoriosRouterHappyPath:
    """Auth válida + casos del endpoint."""

    @pytest.mark.asyncio
    async def test_con_api_key_valida_y_sin_turnos_retorna_200_vacio(
        self, client, db_session
    ):
        prof = await _seed_profesional_con_api_key(
            db_session, telegram_bot_token="bot_test"
        )
        response = client.post(
            f"/api/v1/recordatorios/run?fecha={_mañana_iso()}",
            headers={"X-API-Key": prof.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fecha"] == _mañana_iso()
        assert data["total_candidatos"] == 0
        assert data["total_enviados"] == 0
        assert data["total_fallidos"] == 0
        assert data["errores"] == []

    @pytest.mark.asyncio
    async def test_con_api_key_valida_y_un_turno_se_envia_y_marca_flag(
        self, client, db_session
    ):
        """Crea un turno candidato, dispara el endpoint, verifica el flag persiste."""
        prof = await _seed_profesional_con_api_key(
            db_session, telegram_bot_token="bot_test"
        )
        paciente = await _seed_paciente(db_session, prof.id, dni="12345678")
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

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ):
            response = client.post(
                f"/api/v1/recordatorios/run?fecha={_mañana_iso()}",
                headers={"X-API-Key": prof.api_key},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_candidatos"] == 1
        assert data["total_enviados"] == 1
        assert data["total_fallidos"] == 0
        assert data["errores"] == []

        # Re-leer el turno desde db_session (comparte DB con el TestClient).
        # Refrescamos la instancia para que ``recordatorio_enviado`` no
        # quede con el valor cacheado de antes del commit del handler.
        await db_session.refresh(turno)
        assert turno.recordatorio_enviado is True

    @pytest.mark.asyncio
    async def test_fecha_invalida_retorna_422(self, client, db_session):
        """``?fecha=foo`` → 422 (Pydantic valida el formato date)."""
        prof = await _seed_profesional_con_api_key(
            db_session, telegram_bot_token="bot_test"
        )
        response = client.post(
            "/api/v1/recordatorios/run?fecha=foo",
            headers={"X-API-Key": prof.api_key},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_fecha_pasada_lejana_sin_candidatos_retorna_200(
        self, client, db_session
    ):
        """Una fecha en el pasado lejano no tiene candidatos → 200 con ceros."""
        prof = await _seed_profesional_con_api_key(
            db_session, telegram_bot_token="bot_test"
        )
        response = client.post(
            "/api/v1/recordatorios/run?fecha=2020-01-01",
            headers={"X-API-Key": prof.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fecha"] == "2020-01-01"
        assert data["total_candidatos"] == 0
        assert data["total_enviados"] == 0
        assert data["total_fallidos"] == 0

    @pytest.mark.asyncio
    async def test_sin_parametro_fecha_usa_manana_por_default(
        self, client, db_session
    ):
        """Sin query param ``fecha``, el endpoint usa mañana por default → 200."""
        prof = await _seed_profesional_con_api_key(
            db_session, telegram_bot_token="bot_test"
        )
        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ):
            response = client.post(
                "/api/v1/recordatorios/run",
                headers={"X-API-Key": prof.api_key},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["fecha"] == _mañana_iso()

    @pytest.mark.asyncio
    async def test_api_key_de_un_profesional_procesa_a_otros_activos(
        self, client, db_session
    ):
        """La api_key del caller es solo auth — el endpoint itera TODOS los activos.

        C-24 Decisión 8: el caller autentica con su api_key pero el
        endpoint dispara el batch sobre todos los profesionales activos
        (``is_active=True``). Verificamos que un segundo profesional
        activo con su propio turno también se procesa en el mismo run.
        """
        caller = await _seed_profesional_con_api_key(
            db_session,
            nombre="Dr. Caller",
            dias_atencion=["Lunes"],
            telegram_bot_token="bot_caller",
        )
        other = await _seed_profesional_con_api_key(
            db_session,
            nombre="Dr. Other",
            dias_atencion=["Martes"],
            telegram_bot_token="bot_other",
        )
        paciente_caller = await _seed_paciente(db_session, caller.id, dni="11111111")
        paciente_other = await _seed_paciente(db_session, other.id, dni="22222222")

        base_dt = datetime.now() + timedelta(hours=2)
        turno_caller = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=caller.id,
            paciente_id=paciente_caller.id,
            recordatorio_enviado=False,
        )
        turno_other = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=5)).time(),
            estado="CONFIRMADO",
            profesional_id=other.id,
            paciente_id=paciente_other.id,
            recordatorio_enviado=False,
        )
        db_session.add_all([turno_caller, turno_other])
        await db_session.commit()
        await _add_destinatario_telegram(db_session, turno_caller.id, "chat-caller")
        await _add_destinatario_telegram(db_session, turno_other.id, "chat-other")

        with patch(
            "app.services.recordatorio_service.enviar_recordatorio_telegram",
            new=AsyncMock(return_value=True),
        ):
            # Autenticar con la api_key del CALLER
            response = client.post(
                f"/api/v1/recordatorios/run?fecha={_mañana_iso()}",
                headers={"X-API-Key": caller.api_key},
            )

        assert response.status_code == 200
        data = response.json()
        # Ambos turnos se procesan, no solo el del caller
        assert data["total_candidatos"] == 2
        assert data["total_enviados"] == 2
        assert data["total_fallidos"] == 0
        assert data["errores"] == []
