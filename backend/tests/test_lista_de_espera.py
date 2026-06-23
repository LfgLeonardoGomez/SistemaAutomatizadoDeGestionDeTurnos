import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError

from app.models.lista_de_espera import ListaDeEspera
from app.models.paciente import Paciente
from app.models.profesional import Profesional


class TestListaDeEsperaModel:
    """Tests for ListaDeEspera model — Task 1.6."""

    @pytest_asyncio.fixture
    async def profesional(self, db_session):
        p = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología general",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            email="test@local.dev",
            password_hash="$2b$12$dummy",
            is_active=True,
        )
        db_session.add(p)
        await db_session.commit()
        await db_session.refresh(p)
        return p

    @pytest.mark.asyncio
    async def test_lista_de_espera_creation(self, db_session, profesional):
        """Scenario: Registro en lista de espera."""
        paciente = Paciente(
            nombre="Maria", apellido="Gomez", dni="55555555", telefono="6",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.flush()

        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 6, 15),
            profesional_id=profesional.id,
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)

        assert registro.id is not None
        assert registro.paciente_id == paciente.id
        assert registro.fecha_solicitada == date(2026, 6, 15)
        assert registro.notificado is False
        assert registro.creado_en is not None
        assert registro.profesional_id == profesional.id

    @pytest.mark.asyncio
    async def test_lista_de_espera_notificado_default(self, db_session, profesional):
        """Scenario: notificado default FALSE — 4.10."""
        paciente = Paciente(
            nombre="Pedro", apellido="Sanz", dni="66666666", telefono="7",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.flush()

        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 6, 16),
            profesional_id=profesional.id,
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)
        assert registro.notificado is False

    @pytest.mark.asyncio
    async def test_lista_de_espera_sin_paciente(self, db_session, profesional):
        """Scenario: Registro sin paciente."""
        registro = ListaDeEspera(
            paciente_id=None,
            fecha_solicitada=date(2026, 6, 15),
            profesional_id=profesional.id,
        )
        db_session.add(registro)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_lista_de_espera_profesional_id_required(self, db_session):
        """Scenario: Registro en lista de espera sin profesional."""
        registro = ListaDeEspera(
            paciente_id=1,
            fecha_solicitada=date(2026, 6, 15),
            profesional_id=None,
        )
        db_session.add(registro)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_lista_de_espera_multiple_por_paciente(self, db_session, profesional):
        """Scenario: Múltiples registros por paciente."""
        paciente = Paciente(
            nombre="Luis", apellido="Ruiz", dni="77777777", telefono="8",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.flush()

        for i in range(2):
            registro = ListaDeEspera(
                paciente_id=paciente.id,
                fecha_solicitada=date(2026, 6, 15 + i),
                profesional_id=profesional.id,
            )
            db_session.add(registro)
        await db_session.commit()

        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.paciente_id == paciente.id)
        )
        registros = result.scalars().all()
        assert len(registros) == 2

    @pytest.mark.asyncio
    async def test_lista_de_espera_index_exists(self, async_engine):
        """Scenario: Índice (profesional_id, paciente_id) existe."""
        async with async_engine.connect() as conn:
            def get_indexes(connection):
                inspector = inspect(connection)
                return inspector.get_indexes("lista_de_espera")

            indexes = await conn.run_sync(get_indexes)
            index_names = {idx["name"] for idx in indexes}
            assert "ix_lista_de_espera_profesional_paciente" in index_names
