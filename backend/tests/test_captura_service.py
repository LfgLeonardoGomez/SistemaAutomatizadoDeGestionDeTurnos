"""Tests for the conversational capture state persisted on ReservaTemporal.

C-27: the Telegram booking flow asks for the patient's DNI (and, for a new
patient, name and phone) across several messages. Each message is a separate
n8n execution, so the partial answers need a durable home. They live in
``reserva_temporal.datos_captura`` and are reached from the chat id through
the ``TurnoDestinatario`` row that ``reservar_turno`` already writes.
"""

import pytest
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.models.turno_destinatario import TurnoDestinatario
from app.services.captura_service import (
    derivar_paso,
    obtener_captura_pendiente,
    actualizar_datos_captura,
)
from app.services.turno_service import _utcnow_naive
from app.exceptions import CapturaNoEncontradaError
from tests.conftest import make_profesional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_profesional(db_session: AsyncSession):
    p = make_profesional()
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_reserva(
    db_session: AsyncSession,
    profesional_id: int,
    chat_id: str = "5150361036",
    *,
    minutos_para_expirar: int = 10,
    datos_captura: dict | None = None,
    estado: str = "RESERVADO_TEMPORAL",
    con_destinatario: bool = True,
    hora_inicio: time = time(9, 0),
) -> Turno:
    """Create a Turno + ReservaTemporal + TELEGRAM destinatario, the exact
    shape ``reservar_turno`` produces for a Telegram booking."""
    turno = Turno(
        fecha=date.today() + timedelta(days=1),
        hora_inicio=hora_inicio,
        hora_fin=time(hora_inicio.hour, 30) if hora_inicio.minute == 0 else time(hora_inicio.hour + 1, 0),
        estado=estado,
        profesional_id=profesional_id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)

    reserva = ReservaTemporal(
        turno_id=turno.id,
        expiracion=_utcnow_naive() + timedelta(minutes=minutos_para_expirar),
        datos_captura=datos_captura if datos_captura is not None else {},
    )
    db_session.add(reserva)

    if con_destinatario:
        db_session.add(
            TurnoDestinatario(
                turno_id=turno.id, canal="TELEGRAM", destinatario=chat_id
            )
        )
    await db_session.commit()
    await db_session.refresh(turno)
    return turno


# ---------------------------------------------------------------------------
# derivar_paso — pure function, no DB
# ---------------------------------------------------------------------------

class TestDerivarPaso:
    """The step is DERIVED from the captured data, never stored.

    Storing it as its own column would allow a ``paso`` that contradicts
    ``datos`` (say, ``paso='telefono'`` with no dni captured). Deriving it
    makes that state unrepresentable.
    """

    def test_sin_datos_pide_dni(self):
        assert derivar_paso({}) == "dni"

    def test_dni_vacio_pide_dni(self):
        assert derivar_paso({"dni": ""}) == "dni"

    def test_con_dni_sin_nombre_pide_nombre(self):
        assert derivar_paso({"dni": "35539792"}) == "nombre"

    def test_con_dni_y_nombre_sin_apellido_pide_nombre(self):
        # Name and surname are asked together in one message, so a half
        # filled pair must re-ask the pair, not move on.
        assert derivar_paso({"dni": "35539792", "nombre": "Leonardo"}) == "nombre"

    def test_con_nombre_completo_sin_telefono_pide_telefono(self):
        datos = {"dni": "35539792", "nombre": "Leonardo", "apellido": "Gomez"}
        assert derivar_paso(datos) == "telefono"

    def test_con_todos_los_datos_pasa_a_confirmar(self):
        datos = {
            "dni": "35539792",
            "nombre": "Leonardo",
            "apellido": "Gomez",
            "telefono": "3624123456",
        }
        assert derivar_paso(datos) == "confirmar"

    def test_email_es_opcional_y_no_bloquea_confirmar(self):
        datos = {
            "dni": "35539792",
            "nombre": "Leonardo",
            "apellido": "Gomez",
            "telefono": "3624123456",
            "email": "leo@example.com",
        }
        assert derivar_paso(datos) == "confirmar"

    def test_datos_none_se_trata_como_vacio(self):
        assert derivar_paso(None) == "dni"


# ---------------------------------------------------------------------------
# obtener_captura_pendiente
# ---------------------------------------------------------------------------

class TestObtenerCapturaPendiente:
    @pytest.mark.asyncio
    async def test_reserva_viva_devuelve_turno_id_y_paso(self, db_session):
        prof = await _seed_profesional(db_session)
        turno = await _seed_reserva(db_session, prof.id, chat_id="5150361036")

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )

        assert captura is not None
        assert captura.turno_id == turno.id
        assert captura.paso == "dni"
        assert captura.datos == {}

    @pytest.mark.asyncio
    async def test_devuelve_los_datos_ya_capturados(self, db_session):
        prof = await _seed_profesional(db_session)
        await _seed_reserva(
            db_session,
            prof.id,
            chat_id="5150361036",
            datos_captura={"dni": "35539792"},
        )

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )

        assert captura.datos == {"dni": "35539792"}
        assert captura.paso == "nombre"

    @pytest.mark.asyncio
    async def test_sin_reserva_devuelve_none(self, db_session):
        prof = await _seed_profesional(db_session)

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )

        assert captura is None

    @pytest.mark.asyncio
    async def test_reserva_expirada_devuelve_none(self, db_session):
        """An expired reservation is not a pending capture. Without this the
        bot would keep asking for a DNI for a slot it no longer holds."""
        prof = await _seed_profesional(db_session)
        await _seed_reserva(
            db_session, prof.id, chat_id="5150361036", minutos_para_expirar=-1
        )

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )

        assert captura is None

    @pytest.mark.asyncio
    async def test_otro_chat_id_no_ve_la_reserva(self, db_session):
        prof = await _seed_profesional(db_session)
        await _seed_reserva(db_session, prof.id, chat_id="5150361036")

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="9999999999"
        )

        assert captura is None

    @pytest.mark.asyncio
    async def test_aislamiento_entre_profesionales(self, db_session):
        """Two professionals can have a booking in flight with the same chat
        id. Each must only ever see its own."""
        prof_a = await _seed_profesional(db_session)
        prof_b = await _seed_profesional(db_session)
        turno_a = await _seed_reserva(
            db_session, prof_a.id, chat_id="5150361036",
            datos_captura={"dni": "11111111"},
        )
        await _seed_reserva(
            db_session, prof_b.id, chat_id="5150361036",
            datos_captura={"dni": "22222222"},
        )

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof_a.id, telegram_chat_id="5150361036"
        )

        assert captura.turno_id == turno_a.id
        assert captura.datos == {"dni": "11111111"}

    @pytest.mark.asyncio
    async def test_turno_confirmado_ya_no_es_captura_pendiente(self, db_session):
        prof = await _seed_profesional(db_session)
        await _seed_reserva(
            db_session, prof.id, chat_id="5150361036", estado="CONFIRMADO"
        )

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )

        assert captura is None

    @pytest.mark.asyncio
    async def test_reserva_sin_destinatario_telegram_no_es_alcanzable(
        self, db_session
    ):
        """A booking made from the web (no chat id) must not be picked up by
        a Telegram capture lookup."""
        prof = await _seed_profesional(db_session)
        await _seed_reserva(db_session, prof.id, con_destinatario=False)

        captura = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )

        assert captura is None


# ---------------------------------------------------------------------------
# actualizar_datos_captura
# ---------------------------------------------------------------------------

class TestActualizarDatosCaptura:
    @pytest.mark.asyncio
    async def test_guarda_el_dni_y_avanza_el_paso(self, db_session):
        prof = await _seed_profesional(db_session)
        turno = await _seed_reserva(db_session, prof.id)

        captura = await actualizar_datos_captura(
            db_session,
            profesional_id=prof.id,
            turno_id=turno.id,
            nuevos_datos={"dni": "35539792"},
        )
        await db_session.commit()

        assert captura.paso == "nombre"
        assert captura.datos == {"dni": "35539792"}

    @pytest.mark.asyncio
    async def test_mergea_en_vez_de_reemplazar(self, db_session):
        """The phone answer must not wipe the dni captured two messages ago."""
        prof = await _seed_profesional(db_session)
        turno = await _seed_reserva(
            db_session,
            prof.id,
            datos_captura={"dni": "35539792", "nombre": "Leonardo", "apellido": "Gomez"},
        )

        captura = await actualizar_datos_captura(
            db_session,
            profesional_id=prof.id,
            turno_id=turno.id,
            nuevos_datos={"telefono": "3624123456"},
        )
        await db_session.commit()

        assert captura.datos == {
            "dni": "35539792",
            "nombre": "Leonardo",
            "apellido": "Gomez",
            "telefono": "3624123456",
        }
        assert captura.paso == "confirmar"

    @pytest.mark.asyncio
    async def test_persiste_entre_sesiones(self, db_session):
        """The whole point of the change: the answer survives past the call
        that wrote it. This is what staticData failed to do."""
        prof = await _seed_profesional(db_session)
        turno = await _seed_reserva(db_session, prof.id, chat_id="5150361036")

        await actualizar_datos_captura(
            db_session,
            profesional_id=prof.id,
            turno_id=turno.id,
            nuevos_datos={"dni": "35539792"},
        )
        await db_session.commit()
        db_session.expunge_all()

        releido = await obtener_captura_pendiente(
            db_session, profesional_id=prof.id, telegram_chat_id="5150361036"
        )
        assert releido.datos == {"dni": "35539792"}
        assert releido.paso == "nombre"

    @pytest.mark.asyncio
    async def test_turno_de_otro_profesional_no_se_puede_actualizar(
        self, db_session
    ):
        prof_a = await _seed_profesional(db_session)
        prof_b = await _seed_profesional(db_session)
        turno_a = await _seed_reserva(db_session, prof_a.id)

        with pytest.raises(CapturaNoEncontradaError):
            await actualizar_datos_captura(
                db_session,
                profesional_id=prof_b.id,
                turno_id=turno_a.id,
                nuevos_datos={"dni": "35539792"},
            )

    @pytest.mark.asyncio
    async def test_turno_inexistente_falla(self, db_session):
        prof = await _seed_profesional(db_session)

        with pytest.raises(CapturaNoEncontradaError):
            await actualizar_datos_captura(
                db_session,
                profesional_id=prof.id,
                turno_id=999999,
                nuevos_datos={"dni": "35539792"},
            )

    @pytest.mark.asyncio
    async def test_reserva_expirada_falla(self, db_session):
        prof = await _seed_profesional(db_session)
        turno = await _seed_reserva(db_session, prof.id, minutos_para_expirar=-1)

        with pytest.raises(CapturaNoEncontradaError):
            await actualizar_datos_captura(
                db_session,
                profesional_id=prof.id,
                turno_id=turno.id,
                nuevos_datos={"dni": "35539792"},
            )
