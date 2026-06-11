import pytest
from datetime import date
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.lista_de_espera import ListaDeEspera
from app.models.paciente import Paciente


class TestListaDeEsperaModel:
    """Tests for ListaDeEspera model — Task 1.6."""

    @pytest.mark.asyncio
    async def test_lista_de_espera_creation(self, db_session):
        """Scenario: Registro en lista de espera."""
        paciente = Paciente(
            nombre="Maria", apellido="Gomez", dni="55555555", telefono="6"
        )
        db_session.add(paciente)
        await db_session.flush()

        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 6, 15),
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)

        assert registro.id is not None
        assert registro.paciente_id == paciente.id
        assert registro.fecha_solicitada == date(2026, 6, 15)
        assert registro.notificado is False
        assert registro.creado_en is not None

    @pytest.mark.asyncio
    async def test_lista_de_espera_notificado_default(self, db_session):
        """Scenario: notificado default FALSE — 4.10."""
        paciente = Paciente(
            nombre="Pedro", apellido="Sanz", dni="66666666", telefono="7"
        )
        db_session.add(paciente)
        await db_session.flush()

        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 6, 16),
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)
        assert registro.notificado is False

    @pytest.mark.asyncio
    async def test_lista_de_espera_sin_paciente(self, db_session):
        """Scenario: Registro sin paciente."""
        registro = ListaDeEspera(
            paciente_id=None,
            fecha_solicitada=date(2026, 6, 15),
        )
        db_session.add(registro)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_lista_de_espera_multiple_por_paciente(self, db_session):
        """Scenario: Múltiples registros por paciente."""
        paciente = Paciente(
            nombre="Luis", apellido="Ruiz", dni="77777777", telefono="8"
        )
        db_session.add(paciente)
        await db_session.flush()

        for i in range(2):
            registro = ListaDeEspera(
                paciente_id=paciente.id,
                fecha_solicitada=date(2026, 6, 15 + i),
            )
            db_session.add(registro)
        await db_session.commit()

        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.paciente_id == paciente.id)
        )
        registros = result.scalars().all()
        assert len(registros) == 2
