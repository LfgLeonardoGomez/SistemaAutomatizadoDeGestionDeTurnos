"""Tests para el helper upsert_destinatario — C-23 TAREA 5.

C-23 TAREA 5: el helper centraliza el upsert de un ``TurnoDestinatario``
por ``(turno_id, canal)``. Patrón A: NO commitea; el caller (servicio de
reserva/confirmación) lo hace. Esto evita duplicar la lógica de upsert en
cada punto de creación de destinatario y respeta la UNIQUE(turno_id, canal)
de la DB.
"""
import pytest
from datetime import date, time

from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.services.destinatario_service import upsert_destinatario
from tests.conftest import make_profesional_persisted


async def _seed_turno(db_session):
    p = await make_profesional_persisted(db_session)
    turno = Turno(
        fecha=date(2026, 8, 15),
        hora_inicio=time(9, 0),
        hora_fin=time(9, 30),
        estado="DISPONIBLE",
        profesional_id=p.id,
    )
    db_session.add(turno)
    await db_session.commit()
    await db_session.refresh(turno)
    return turno


class TestUpsertDestinatario:
    """Tests para upsert_destinatario (TAREA 5.1 RED, 5.2 GREEN, 5.3 TRIANGULATE)."""

    @pytest.mark.asyncio
    async def test_upsert_crea_destinatario_nuevo(self, db_session):
        """TAREA 5.1 GREEN: upsert_destinatario con (turno_id, 'TELEGRAM', 'A') crea
        la fila cuando no existe un destinatario previo para ese canal."""
        turno = await _seed_turno(db_session)

        result = await upsert_destinatario(
            db_session, turno_id=turno.id, canal="TELEGRAM", destinatario="555001"
        )
        await db_session.commit()

        assert result.id is not None
        assert result.turno_id == turno.id
        assert result.canal == "TELEGRAM"
        assert result.destinatario == "555001"

    @pytest.mark.asyncio
    async def test_upsert_actualiza_destinatario_existente_mismo_canal(self, db_session):
        """TAREA 5.1 GREEN: segunda llamada con 'B' mismo canal ACTUALIZA (no duplica).

        C-23 (TAREA 5.2): la UNIQUE(turno_id, canal) garantiza a lo sumo un
        destinatario por canal. El helper hace SELECT + UPDATE si existe,
        si no INSERT — nunca duplica.
        """
        turno = await _seed_turno(db_session)

        first = await upsert_destinatario(
            db_session, turno_id=turno.id, canal="TELEGRAM", destinatario="chat_A"
        )
        await db_session.commit()
        first_id = first.id

        second = await upsert_destinatario(
            db_session, turno_id=turno.id, canal="TELEGRAM", destinatario="chat_B"
        )
        await db_session.commit()

        # Misma fila (mismo id), solo cambió destinatario
        assert second.id == first_id
        assert second.destinatario == "chat_B"

        # Verificamos que NO haya duplicados en la DB
        from sqlalchemy import select
        rows = (await db_session.execute(
            select(TurnoDestinatario).where(TurnoDestinatario.turno_id == turno.id)
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].destinatario == "chat_B"

    @pytest.mark.asyncio
    async def test_upsert_dos_canales_distintos_coexisten(self, db_session):
        """TAREA 5.3 TRIANGULATE: dos canales distintos (TELEGRAM + EMAIL) en el
        mismo turno son válidos y conviven (no se sobrescriben entre sí)."""
        turno = await _seed_turno(db_session)

        tg = await upsert_destinatario(
            db_session, turno_id=turno.id, canal="TELEGRAM", destinatario="12345"
        )
        em = await upsert_destinatario(
            db_session, turno_id=turno.id, canal="EMAIL", destinatario="user@example.com"
        )
        await db_session.commit()

        assert tg.id != em.id
        assert tg.canal == "TELEGRAM"
        assert em.canal == "EMAIL"

        from sqlalchemy import select
        rows = (await db_session.execute(
            select(TurnoDestinatario).where(TurnoDestinatario.turno_id == turno.id)
        )).scalars().all()
        canales = {r.canal for r in rows}
        assert canales == {"TELEGRAM", "EMAIL"}

    @pytest.mark.asyncio
    async def test_upsert_no_commitea_patron_a(self, db_session, engine):
        """TAREA 5.2 GREEN: el helper NO hace commit. El caller controla el commit.

        Si el caller no hace commit, la fila nueva no es visible en otra sesión.
        Verificamos creando un destinatario, abriendo una SEGUNDA sesión contra
        el mismo engine, y comprobando que NO está (rollback implícito por
        no-commit + isolation de la sesión).
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.models import TurnoDestinatario as TD

        turno = await _seed_turno(db_session)
        await upsert_destinatario(
            db_session, turno_id=turno.id, canal="TELEGRAM", destinatario="x"
        )
        # Sin commit: la fila está en la transacción de db_session pero no es
        # visible a una sesión nueva.
        async with AsyncSession(engine, expire_on_commit=False) as other:
            rows = (await other.execute(
                select(TD).where(TD.turno_id == turno.id)
            )).scalars().all()
            assert rows == [], (
                "El helper hizo commit implícito — Patrón A violado. "
                "El caller debe controlar el commit."
            )
