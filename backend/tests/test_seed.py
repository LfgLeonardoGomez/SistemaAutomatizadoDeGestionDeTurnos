import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional
from app.seed import seed_profesional


class TestSeedProfesional:
    """Tests for seed idempotency — Task 3.1/3.3."""

    @pytest.mark.asyncio
    async def test_seed_creates_profesional_when_empty(self, db_session):
        """Scenario: Seed crea profesional si no existe — 3.1."""
        result = await db_session.execute(select(func.count()).select_from(Profesional))
        count_before = result.scalar_one()
        assert count_before == 0

        await seed_profesional(db_session)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(Profesional))
        count_after = result.scalar_one()
        assert count_after == 1

        result = await db_session.execute(select(Profesional))
        profesional = result.scalar_one()
        assert profesional.nombre == "Dr. Por Defecto"
        assert profesional.especialidad == "Odontología general"
        assert profesional.duracion_turno == 30
        assert profesional.horario_inicio == "08:00"
        assert profesional.horario_fin == "18:00"
        assert profesional.dias_atencion == [
            "Lunes", "Martes", "Miércoles", "Jueves", "Viernes"
        ]

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, db_session):
        """Scenario: Seed no duplica registros — 3.3."""
        await seed_profesional(db_session)
        await db_session.commit()

        await seed_profesional(db_session)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(Profesional))
        count = result.scalar_one()
        assert count == 1
