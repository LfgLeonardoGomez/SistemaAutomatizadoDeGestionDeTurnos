import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.profesional import Profesional


class TestProfesionalModel:
    """Tests for Profesional model — Task 1.3."""

    @pytest.mark.asyncio
    async def test_profesional_creation(self, db_session):
        """Scenario: Crear profesional con datos básicos."""
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología general",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        )
        db_session.add(profesional)
        await db_session.commit()
        await db_session.refresh(profesional)

        assert profesional.id is not None
        assert profesional.nombre == "Dr. Test"
        assert profesional.especialidad == "Odontología general"
        assert profesional.duracion_turno == 30
        assert profesional.horario_inicio == "08:00"
        assert profesional.horario_fin == "18:00"
        assert profesional.dias_atencion == ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        assert profesional.creado_en is not None

    @pytest.mark.asyncio
    async def test_profesional_query_by_nombre(self, db_session):
        """Scenario: Triangulate — query profesional by nombre."""
        profesional = Profesional(
            nombre="Dr. García",
            especialidad="Cardiología",
            duracion_turno=45,
            horario_inicio="09:00",
            horario_fin="17:00",
            dias_atencion=["Lunes", "Miércoles"],
        )
        db_session.add(profesional)
        await db_session.commit()

        result = await db_session.execute(
            select(Profesional).where(Profesional.nombre == "Dr. García")
        )
        db_profesional = result.scalar_one()
        assert db_profesional.duracion_turno == 45
