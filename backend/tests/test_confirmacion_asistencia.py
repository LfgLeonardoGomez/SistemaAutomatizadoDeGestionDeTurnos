"""Tests for recording that the patient answered the reminder (C-29, slice 1).

The reminder asks "¿Confirmás tu asistencia?". Until now the answer went
nowhere: ``confirmar_asistencia_turno`` validated ownership and state and
returned the turno unchanged, so a patient who confirmed was
indistinguishable from one who ignored the message.

That distinction is the whole point. The escalation job — resend with a
warning, then cancel and free the slot — must not chase someone who already
answered. This slice records the answer; the job itself is the rest of C-29.

What is deliberately NOT changed: ``turno.estado``. The turno was CONFIRMADO
before the patient answered and stays CONFIRMADO after. Nothing the
professional sees changes, which is the behaviour the product owner asked
for. The confirmation is a fact ABOUT the turno, not a state OF it.
"""

import pytest
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import TurnoNoEncontradoError, TurnoYaCanceladoError
from app.models.turno import Turno
from app.services.turno_service import confirmar_asistencia_turno, _utcnow_naive
from tests.conftest import make_profesional


async def _seed_profesional(db_session: AsyncSession):
    p = make_profesional()
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_turno(
    db_session: AsyncSession,
    profesional_id: int,
    *,
    estado: str = "CONFIRMADO",
    hora_inicio: time = time(9, 0),
) -> Turno:
    turno = Turno(
        fecha=date.today() + timedelta(days=1),
        hora_inicio=hora_inicio,
        hora_fin=time(hora_inicio.hour + 1, 0),
        estado=estado,
        profesional_id=profesional_id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)
    return turno


class TestConfirmarAsistenciaRegistraLaRespuesta:
    @pytest.mark.asyncio
    async def test_sin_confirmar_el_campo_arranca_en_none(self, db_session):
        """``NULL`` es "no respondió" — no hace falta un flag aparte."""
        prof = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, prof.id)

        assert turno.asistencia_confirmada_en is None

    @pytest.mark.asyncio
    async def test_confirmar_sella_el_momento(self, db_session):
        prof = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, prof.id)
        antes = _utcnow_naive()

        resultado = await confirmar_asistencia_turno(
            db_session, profesional_id=prof.id, turno_id=turno.id
        )
        await db_session.commit()

        assert resultado.asistencia_confirmada_en is not None
        assert antes <= resultado.asistencia_confirmada_en <= _utcnow_naive()

    @pytest.mark.asyncio
    async def test_el_estado_no_cambia(self, db_session):
        """Requisito explícito del producto: el profesional no ve nada nuevo."""
        prof = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, prof.id)

        resultado = await confirmar_asistencia_turno(
            db_session, profesional_id=prof.id, turno_id=turno.id
        )
        await db_session.commit()

        assert resultado.estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_persiste_para_el_job_de_escalado(self, db_session):
        """La marca tiene que sobrevivir a la request que la escribió: el job
        de escalado corre mucho después, en otra sesión."""
        prof = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, prof.id)

        await confirmar_asistencia_turno(
            db_session, profesional_id=prof.id, turno_id=turno.id
        )
        await db_session.commit()
        db_session.expunge_all()

        releido = (
            await db_session.execute(select(Turno).where(Turno.id == turno.id))
        ).scalar_one()
        assert releido.asistencia_confirmada_en is not None

    @pytest.mark.asyncio
    async def test_es_idempotente_y_conserva_la_primera_marca(self, db_session):
        """Telegram reentrega updates y el paciente puede tocar el botón dos
        veces. La respuesta que importa es la PRIMERA: pisarla con la segunda
        correría la ventana del escalado hacia adelante."""
        prof = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, prof.id)

        primero = await confirmar_asistencia_turno(
            db_session, profesional_id=prof.id, turno_id=turno.id
        )
        await db_session.commit()
        marca_original = primero.asistencia_confirmada_en

        segundo = await confirmar_asistencia_turno(
            db_session, profesional_id=prof.id, turno_id=turno.id
        )
        await db_session.commit()

        assert segundo.asistencia_confirmada_en == marca_original


class TestConfirmarAsistenciaSiguePreservandoSusGuardas:
    """La marca nueva no debe aflojar las validaciones que ya existían."""

    @pytest.mark.asyncio
    async def test_turno_cancelado_falla_y_no_deja_marca(self, db_session):
        prof = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, prof.id, estado="CANCELADO")
        # El id se captura ANTES de expulsar el objeto: después queda
        # detached y leerle un atributo intentaría refrescarlo.
        turno_id = turno.id

        with pytest.raises(TurnoYaCanceladoError):
            await confirmar_asistencia_turno(
                db_session, profesional_id=prof.id, turno_id=turno_id
            )
        await db_session.rollback()
        # El rollback deja el objeto expirado en el identity map; sin
        # expulsarlo, la re-consulta refresca ese mismo objeto y dispara IO
        # fuera del contexto async (MissingGreenlet). Se relee limpio.
        db_session.expunge_all()

        releido = (
            await db_session.execute(select(Turno).where(Turno.id == turno_id))
        ).scalar_one()
        assert releido.asistencia_confirmada_en is None

    @pytest.mark.asyncio
    async def test_turno_inexistente_falla(self, db_session):
        prof = await _seed_profesional(db_session)

        with pytest.raises(TurnoNoEncontradoError):
            await confirmar_asistencia_turno(
                db_session, profesional_id=prof.id, turno_id=999999
            )

    @pytest.mark.asyncio
    async def test_turno_de_otro_profesional_no_se_puede_confirmar(self, db_session):
        prof_a = await _seed_profesional(db_session)
        prof_b = await _seed_profesional(db_session)
        turno_a = await _seed_turno(db_session, prof_a.id)

        with pytest.raises(TurnoNoEncontradoError):
            await confirmar_asistencia_turno(
                db_session, profesional_id=prof_b.id, turno_id=turno_a.id
            )
