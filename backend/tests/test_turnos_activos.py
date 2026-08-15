"""Tests for ``GET /turnos/activos`` — the turnos a Telegram chat can manage.

The bot needs to list a patient's cancelable appointments before offering a
"cancel" action. Only CONFIRMADO turnos qualify (that is the only state
``turno_service.cancelar_turno`` accepts — see its docstring), and only
turnos still ahead of "now" in the professional's local time (see
``app.tiempo`` for why local-time helpers, not ``datetime.now()``/
``date.today()``, are mandatory for comparisons against ``fecha``/
``hora_inicio``).

The chat is resolved to its turnos through ``TurnoDestinatario``
(canal='TELEGRAM'), the same table ``turno_service.reservar_turno`` already
writes — see ``captura_service.obtener_captura_pendiente`` for the query
pattern this endpoint follows.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from fastapi import status

from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.services.auth_service import set_profesional_api_key
from app.services.captura_service import obtener_turnos_activos
from app.tiempo import ahora_local, hoy_local
from tests.conftest import make_profesional_persisted

CHAT_ID = "5150361036"


async def _seed_activa_con_api_key(db_session, **overrides) -> Profesional:
    overrides.setdefault("email", f"activos-{uuid.uuid4().hex[:8]}@local.dev")
    p = await make_profesional_persisted(db_session, **overrides)
    await set_profesional_api_key(db_session, p)
    await db_session.refresh(p)
    return p


async def _seed_turno(
    db_session,
    profesional_id: int,
    *,
    fecha: date,
    hora_inicio: time,
    hora_fin: time,
    estado: str = "CONFIRMADO",
    chat_id: str | None = CHAT_ID,
) -> Turno:
    turno = Turno(
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        estado=estado,
        profesional_id=profesional_id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)

    if chat_id is not None:
        db_session.add(
            TurnoDestinatario(turno_id=turno.id, canal="TELEGRAM", destinatario=chat_id)
        )
        await db_session.commit()
        await db_session.refresh(turno)
    return turno


class TestObtenerTurnosActivosService:
    """Tests directos del service, sin pasar por HTTP."""

    @pytest.mark.asyncio
    async def test_turno_confirmado_futuro_aparece(self, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        turno = await _seed_turno(
            db_session, prof.id, fecha=mañana, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof.id, telegram_chat_id=CHAT_ID
        )

        assert [t.id for t in resultado] == [turno.id]

    @pytest.mark.asyncio
    async def test_turno_pasado_no_aparece(self, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        ayer = hoy_local() - timedelta(days=1)
        await _seed_turno(
            db_session, prof.id, fecha=ayer, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof.id, telegram_chat_id=CHAT_ID
        )

        assert resultado == []

    @pytest.mark.asyncio
    async def test_turno_cancelado_no_aparece(self, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        await _seed_turno(
            db_session,
            prof.id,
            fecha=mañana,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            estado="CANCELADO",
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof.id, telegram_chat_id=CHAT_ID
        )

        assert resultado == []

    @pytest.mark.asyncio
    async def test_turno_de_otro_profesional_no_aparece(self, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        await _seed_turno(
            db_session, prof_b.id, fecha=mañana, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof_a.id, telegram_chat_id=CHAT_ID
        )

        assert resultado == []

    @pytest.mark.asyncio
    async def test_chat_sin_turnos_devuelve_lista_vacia(self, db_session):
        prof = await _seed_activa_con_api_key(db_session)

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof.id, telegram_chat_id=CHAT_ID
        )

        assert resultado == []

    @pytest.mark.asyncio
    async def test_dos_profesionales_mismo_chat_id_ven_solo_lo_suyo(self, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        turno_a = await _seed_turno(
            db_session, prof_a.id, fecha=mañana, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )
        await _seed_turno(
            db_session, prof_b.id, fecha=mañana, hora_inicio=time(11, 0), hora_fin=time(12, 0)
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof_a.id, telegram_chat_id=CHAT_ID
        )

        assert [t.id for t in resultado] == [turno_a.id]

    @pytest.mark.asyncio
    async def test_orden_ascendente_por_fecha_y_hora(self, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        pasado_mañana = hoy_local() + timedelta(days=2)

        turno_tarde = await _seed_turno(
            db_session, prof.id, fecha=mañana, hora_inicio=time(20, 0), hora_fin=time(21, 0)
        )
        turno_temprano = await _seed_turno(
            db_session, prof.id, fecha=mañana, hora_inicio=time(8, 0), hora_fin=time(9, 0)
        )
        turno_dia_siguiente = await _seed_turno(
            db_session, prof.id, fecha=pasado_mañana, hora_inicio=time(7, 0), hora_fin=time(8, 0)
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof.id, telegram_chat_id=CHAT_ID
        )

        assert [t.id for t in resultado] == [
            turno_temprano.id,
            turno_tarde.id,
            turno_dia_siguiente.id,
        ]

    @pytest.mark.asyncio
    async def test_turno_hoy_mas_tarde_que_ahora_aparece(self, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        ahora = ahora_local()
        una_hora_despues = (ahora + timedelta(hours=1)).time()
        turno = await _seed_turno(
            db_session,
            prof.id,
            fecha=ahora.date(),
            hora_inicio=una_hora_despues,
            hora_fin=time(23, 59),
        )

        resultado = await obtener_turnos_activos(
            db_session, profesional_id=prof.id, telegram_chat_id=CHAT_ID
        )

        assert [t.id for t in resultado] == [turno.id]


class TestGetTurnosActivosRouter:
    """Tests de integración HTTP con X-API-Key, igual que el resto de /turnos/*."""

    @pytest.mark.asyncio
    async def test_devuelve_200_con_turno_confirmado_futuro(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        turno = await _seed_turno(
            db_session, prof.id, fecha=mañana, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )

        response = client.get(
            "/turnos/activos",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == turno.id
        assert body[0]["estado"] == "CONFIRMADO"
        assert body[0]["fecha"] == mañana.isoformat()
        assert body[0]["hora_inicio"] == "09:00:00"
        assert body[0]["hora_fin"] == "10:00:00"

    @pytest.mark.asyncio
    async def test_devuelve_200_con_lista_vacia_sin_turnos(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/activos",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_sin_telegram_chat_id_devuelve_422(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/activos",
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_sin_credenciales_devuelve_401(self, client, db_session):
        await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/activos", params={"telegram_chat_id": CHAT_ID}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_ruta_activos_no_se_confunde_con_turno_id(self, client, db_session):
        """Pin de regresión: '/turnos/activos' debe declararse ANTES que
        cualquier ruta '/{turno_id}/...' — si no, FastAPI podría intentar
        parsear 'activos' como el path param de una ruta GET con ese shape.
        Este test pega directo al endpoint real: si el routing se rompiera
        (p. ej. alguien agrega un GET '/{turno_id}' por encima), este 200
        se convertiría en un 404/422 y lo detectaría."""
        prof = await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/activos",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_aislamiento_entre_profesionales_via_http(self, client, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        await _seed_turno(
            db_session, prof_b.id, fecha=mañana, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )

        response = client.get(
            "/turnos/activos",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof_a.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestPacienteEnLaLista:
    """Un chat puede tener turnos de pacientes DISTINTOS.

    El schema nacía asumiendo un chat = un paciente ("el bot solo necesita lo
    que va a mostrarle al paciente para elegir cuál turno cancelar"). Esa
    suposición se rompe en el caso que el propio dominio contempla: una madre
    que reserva para ella y para su hijo desde el mismo Telegram. Sin el nombre,
    la lista muestra dos turnos indistinguibles y el paciente no puede saber
    cuál está por cancelar o reprogramar.

    No expone datos nuevos: son los pacientes que ese mismo chat registró.
    """

    @pytest.mark.asyncio
    async def test_dos_pacientes_del_mismo_chat_se_distinguen(self, client, db_session):
        from app.models.paciente import Paciente

        prof = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)

        pacientes = []
        for nombre, apellido, dni in (
            ("leonardo", "gomez", "35539792"),
            ("nahir", "jurado", "35662276"),
        ):
            p = Paciente(
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                telefono="2612094262",
                profesional_id=prof.id,
            )
            db_session.add(p)
            pacientes.append(p)
        await db_session.commit()

        for p, hora in zip(pacientes, (time(9, 0), time(16, 30))):
            turno = await _seed_turno(
                db_session,
                prof.id,
                fecha=mañana,
                hora_inicio=hora,
                hora_fin=time(hora.hour + 1, hora.minute),
            )
            turno.paciente_id = p.id
            await db_session.commit()

        response = client.get(
            "/turnos/activos",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2

        nombres = {
            (t["paciente"]["nombre"], t["paciente"]["apellido"]) for t in body
        }
        assert nombres == {("leonardo", "gomez"), ("nahir", "jurado")}

    @pytest.mark.asyncio
    async def test_turno_sin_paciente_no_rompe_la_lista(self, client, db_session):
        """Triangula: un turno sin paciente asignado sigue listándose.

        Un CONFIRMADO sin ``paciente_id`` no debería existir, pero la columna es
        nullable y la lista es lo único que le queda al paciente para salir de
        un estado raro. Devolver 500 acá lo dejaría sin ninguna salida.
        """
        prof = await _seed_activa_con_api_key(db_session)
        mañana = hoy_local() + timedelta(days=1)
        await _seed_turno(
            db_session, prof.id, fecha=mañana, hora_inicio=time(9, 0), hora_fin=time(10, 0)
        )

        response = client.get(
            "/turnos/activos",
            params={"telegram_chat_id": CHAT_ID},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 1
        assert body[0]["paciente"] is None
