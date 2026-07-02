"""Tests para el modelo TurnoDestinatario y la constraint UNIQUE(turno_id, canal).

TDD estricto: este archivo se escribe ANTES de que exista el modelo.
Los tests describen el comportamiento esperado (RED → GREEN → TRIANGULATE).
"""
import pytest
from datetime import date, time, datetime, timezone
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError

from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from tests.conftest import make_profesional_persisted


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_profesional(db_session):
    return await make_profesional_persisted(db_session)


async def _seed_turno(db_session, profesional_id: int) -> Turno:
    turno = Turno(
        fecha=date(2026, 8, 15),
        hora_inicio=time(9, 0),
        hora_fin=time(9, 30),
        estado="DISPONIBLE",
        profesional_id=profesional_id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)
    return turno


# ---------------------------------------------------------------------------
# Task 1.1 RED: TurnoDestinatario persiste y es recuperable vía turno.destinatarios
# ---------------------------------------------------------------------------

class TestTurnoDestinatarioModel:

    @pytest.mark.asyncio
    async def test_crear_destinatario_telegram_persiste(self, db_session):
        """Task 1.1 GREEN: crear TurnoDestinatario(turno_id, canal='TELEGRAM', destinatario='123')
        persiste y es recuperable vía turno.destinatarios."""
        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, p.id)

        dest = TurnoDestinatario(
            turno_id=turno.id,
            canal="TELEGRAM",
            destinatario="123456",
        )
        db_session.add(dest)
        await db_session.commit()
        await db_session.refresh(dest)

        assert dest.id is not None
        assert dest.turno_id == turno.id
        assert dest.canal == "TELEGRAM"
        assert dest.destinatario == "123456"

        # Task 1.1: recuperable vía turno.destinatarios (lazy="selectin")
        await db_session.refresh(turno, attribute_names=["destinatarios"])
        assert len(turno.destinatarios) == 1
        assert turno.destinatarios[0].canal == "TELEGRAM"
        assert turno.destinatarios[0].destinatario == "123456"

    # Task 1.3 TRIANGULATE: canal EMAIL también es válido
    @pytest.mark.asyncio
    async def test_crear_destinatario_email_persiste(self, db_session):
        """Task 1.3 TRIANGULATE: canal EMAIL es válido."""
        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, p.id)

        dest = TurnoDestinatario(
            turno_id=turno.id,
            canal="EMAIL",
            destinatario="abuela@example.com",
        )
        db_session.add(dest)
        await db_session.commit()
        await db_session.refresh(dest)

        assert dest.canal == "EMAIL"
        assert dest.destinatario == "abuela@example.com"

    # Task 1.3 TRIANGULATE: canal inválido rechazado por la DB
    @pytest.mark.asyncio
    async def test_canal_invalido_rechazado_por_db(self, db_session):
        """Task 1.3 TRIANGULATE: canal no definido en ENUM es rechazado."""
        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, p.id)

        dest = TurnoDestinatario(
            turno_id=turno.id,
            canal="SMS",  # no existe en el ENUM
            destinatario="555-1234",
        )
        db_session.add(dest)
        with pytest.raises(Exception):  # IntegrityError o DataError de PG
            await db_session.flush()
        await db_session.rollback()

    # Task 1.4 RED/GREEN: UNIQUE(turno_id, canal) rechaza duplicados
    @pytest.mark.asyncio
    async def test_unique_turno_canal_rechaza_duplicado(self, db_session):
        """Task 1.4: dos filas con el mismo (turno_id, 'TELEGRAM') violan la constraint."""
        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, p.id)

        dest1 = TurnoDestinatario(turno_id=turno.id, canal="TELEGRAM", destinatario="AAA")
        db_session.add(dest1)
        await db_session.commit()

        dest2 = TurnoDestinatario(turno_id=turno.id, canal="TELEGRAM", destinatario="BBB")
        db_session.add(dest2)
        with pytest.raises((IntegrityError, Exception)):
            await db_session.flush()
        await db_session.rollback()

    # Task 1.3 TRIANGULATE: dos canales distintos coexisten en el mismo turno
    @pytest.mark.asyncio
    async def test_dos_canales_distintos_coexisten(self, db_session):
        """Task 1.3 TRIANGULATE: TELEGRAM + EMAIL en el mismo turno son válidos."""
        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, p.id)

        dest_tg = TurnoDestinatario(turno_id=turno.id, canal="TELEGRAM", destinatario="12345")
        dest_em = TurnoDestinatario(turno_id=turno.id, canal="EMAIL", destinatario="test@x.com")
        db_session.add(dest_tg)
        db_session.add(dest_em)
        await db_session.commit()

        await db_session.refresh(turno, attribute_names=["destinatarios"])
        assert len(turno.destinatarios) == 2
        canales = {d.canal for d in turno.destinatarios}
        assert canales == {"TELEGRAM", "EMAIL"}

    # Task 1.5 RED/GREEN: CASCADE — borrar Turno elimina sus destinatarios
    @pytest.mark.asyncio
    async def test_cascade_borrar_turno_elimina_destinatarios(self, db_session):
        """Task 1.5: al borrar el Turno, sus TurnoDestinatario se eliminan en cascada."""
        p = await _seed_profesional(db_session)
        turno = await _seed_turno(db_session, p.id)

        dest = TurnoDestinatario(turno_id=turno.id, canal="TELEGRAM", destinatario="99999")
        db_session.add(dest)
        await db_session.commit()
        dest_id = dest.id
        turno_id = turno.id

        await db_session.delete(turno)
        await db_session.commit()

        # El destinatario ya no debe existir
        result = await db_session.execute(
            select(TurnoDestinatario).where(TurnoDestinatario.id == dest_id)
        )
        assert result.scalar_one_or_none() is None
