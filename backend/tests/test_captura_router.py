"""Tests for the capture endpoints consumed by the n8n Telegram flow (C-27).

``GET /turnos/captura-pendiente`` answers the only question the orquestador
needs before routing a free-text message: does this chat owe me an answer?
``PATCH /turnos/{turno_id}/captura`` stores each answer as it arrives.

Both authenticate with X-API-Key, since n8n has no JWT.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from fastapi import status

from app.models.profesional import Profesional
from app.models.reserva_temporal import ReservaTemporal
from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.services.auth_service import set_profesional_api_key
from app.services.turno_service import _utcnow_naive
from tests.conftest import make_profesional_persisted

CHAT_ID = "5150361036"


async def _seed_activa_con_api_key(db_session, **overrides) -> Profesional:
    overrides.setdefault("email", f"captura-{uuid.uuid4().hex[:8]}@local.dev")
    p = await make_profesional_persisted(db_session, **overrides)
    await set_profesional_api_key(db_session, p)
    await db_session.refresh(p)
    return p


async def _seed_reserva(
    db_session,
    profesional_id: int,
    *,
    chat_id: str = CHAT_ID,
    minutos_para_expirar: int = 10,
    datos_captura: dict | None = None,
    hora_inicio: time = time(9, 0),
) -> Turno:
    turno = Turno(
        fecha=date.today() + timedelta(days=1),
        hora_inicio=hora_inicio,
        hora_fin=time(hora_inicio.hour + 1, 0),
        estado="RESERVADO_TEMPORAL",
        profesional_id=profesional_id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)

    db_session.add(
        ReservaTemporal(
            turno_id=turno.id,
            expiracion=_utcnow_naive() + timedelta(minutes=minutos_para_expirar),
            datos_captura=datos_captura or {},
        )
    )
    db_session.add(
        TurnoDestinatario(turno_id=turno.id, canal="TELEGRAM", destinatario=chat_id)
    )
    await db_session.commit()
    await db_session.refresh(turno)
    return turno


class TestGetCapturaPendiente:
    @pytest.mark.asyncio
    async def test_con_reserva_viva_devuelve_200_con_turno_y_paso(
        self, client, db_session
    ):
        prof = await _seed_activa_con_api_key(db_session)
        turno = await _seed_reserva(db_session, prof.id)

        response = client.get(
            "/turnos/captura-pendiente",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["turno_id"] == turno.id
        assert body["paso"] == "dni"
        assert body["datos"] == {}

    @pytest.mark.asyncio
    async def test_devuelve_el_paso_derivado_de_los_datos_ya_capturados(
        self, client, db_session
    ):
        prof = await _seed_activa_con_api_key(db_session)
        await _seed_reserva(
            db_session, prof.id, datos_captura={"dni": "35539792"}
        )

        response = client.get(
            "/turnos/captura-pendiente",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["paso"] == "nombre"

    @pytest.mark.asyncio
    async def test_sin_captura_pendiente_devuelve_404(self, client, db_session):
        """The orquestador reads this 404 as 'not an answer, treat the text
        normally' — it is an expected outcome, not an error."""
        prof = await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/captura-pendiente",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_reserva_expirada_devuelve_404(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        await _seed_reserva(db_session, prof.id, minutos_para_expirar=-1)

        response = client.get(
            "/turnos/captura-pendiente",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_sin_telegram_chat_id_devuelve_422(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/captura-pendiente",
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_aislamiento_entre_profesionales(self, client, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)
        turno_a = await _seed_reserva(
            db_session, prof_a.id, datos_captura={"dni": "11111111"}
        )
        await _seed_reserva(
            db_session, prof_b.id, datos_captura={"dni": "22222222"}
        )

        response = client.get(
            "/turnos/captura-pendiente",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof_a.api_key},
        )

        assert response.json()["turno_id"] == turno_a.id
        assert response.json()["datos"] == {"dni": "11111111"}

    @pytest.mark.asyncio
    async def test_sin_credenciales_devuelve_401(self, client, db_session):
        await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/captura-pendiente", params={"telegram_chat_id": CHAT_ID}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPatchCaptura:
    @pytest.mark.asyncio
    async def test_guarda_el_dni_y_devuelve_el_paso_siguiente(
        self, client, db_session
    ):
        prof = await _seed_activa_con_api_key(db_session)
        turno = await _seed_reserva(db_session, prof.id)

        response = client.patch(
            f"/turnos/{turno.id}/captura",
            json={"datos": {"dni": "35539792"}},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["turno_id"] == turno.id
        assert body["paso"] == "nombre"
        assert body["datos"] == {"dni": "35539792"}

    @pytest.mark.asyncio
    async def test_la_respuesta_persiste_para_el_proximo_mensaje(
        self, client, db_session
    ):
        """The regression guard for the bug that motivated this change: the
        answer must still be there on the NEXT request, not just in the
        response body of the one that wrote it."""
        prof = await _seed_activa_con_api_key(db_session)
        turno = await _seed_reserva(db_session, prof.id)

        client.patch(
            f"/turnos/{turno.id}/captura",
            json={"datos": {"dni": "35539792"}},
            headers={"X-API-Key": prof.api_key},
        )
        response = client.get(
            "/turnos/captura-pendiente",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.json()["datos"] == {"dni": "35539792"}
        assert response.json()["paso"] == "nombre"

    @pytest.mark.asyncio
    async def test_mergea_con_lo_ya_capturado(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        turno = await _seed_reserva(
            db_session,
            prof.id,
            datos_captura={"dni": "35539792", "nombre": "Leonardo", "apellido": "Gomez"},
        )

        response = client.patch(
            f"/turnos/{turno.id}/captura",
            json={"datos": {"telefono": "3624123456"}},
            headers={"X-API-Key": prof.api_key},
        )

        body = response.json()
        assert body["datos"]["dni"] == "35539792"
        assert body["datos"]["telefono"] == "3624123456"
        assert body["paso"] == "confirmar"

    @pytest.mark.asyncio
    async def test_turno_de_otro_profesional_devuelve_404(self, client, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)
        turno_a = await _seed_reserva(db_session, prof_a.id)

        response = client.patch(
            f"/turnos/{turno_a.id}/captura",
            json={"datos": {"dni": "35539792"}},
            headers={"X-API-Key": prof_b.api_key},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_reserva_expirada_devuelve_404(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        turno = await _seed_reserva(db_session, prof.id, minutos_para_expirar=-1)

        response = client.patch(
            f"/turnos/{turno.id}/captura",
            json={"datos": {"dni": "35539792"}},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_sin_credenciales_devuelve_401(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        turno = await _seed_reserva(db_session, prof.id)

        response = client.patch(
            f"/turnos/{turno.id}/captura", json={"datos": {"dni": "35539792"}}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
