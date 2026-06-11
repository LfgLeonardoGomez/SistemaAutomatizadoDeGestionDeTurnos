import pytest
from datetime import date, time

from app.models.profesional import Profesional
from app.models.turno import Turno


class TestAvailabilityService:
    @pytest.mark.asyncio
    async def test_dia_laborable_sin_turnos(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        fecha = date(2026, 6, 15)  # Monday
        slots = await calcular_disponibilidad(db_session, fecha)
        assert len(slots) == 20
        assert slots[0] == "08:00"
        assert slots[-1] == "17:30"

    @pytest.mark.asyncio
    async def test_dia_no_laborable(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        fecha = date(2026, 6, 15)  # Monday
        slots = await calcular_disponibilidad(db_session, fecha)
        assert slots == []

    @pytest.mark.asyncio
    async def test_turnos_confirmados_excluyen_slots(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "09:00" not in slots

    @pytest.mark.asyncio
    async def test_turnos_reservado_temporal_excluyen_slots(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            estado="RESERVADO_TEMPORAL",
        )
        db_session.add(turno)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "10:00" not in slots

    @pytest.mark.asyncio
    async def test_solapamiento_parcial(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=45,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "09:00" not in slots

    @pytest.mark.asyncio
    async def test_turno_adyacente_sin_solapamiento(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "09:30" in slots

    @pytest.mark.asyncio
    async def test_cambio_duracion_turno(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=60,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert len(slots) == 10
        assert slots[0] == "08:00"
        assert slots[1] == "09:00"

    @pytest.mark.asyncio
    async def test_cambio_dias_atencion(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        fecha = date(2026, 6, 15)  # Monday
        slots = await calcular_disponibilidad(db_session, fecha)
        assert slots == []

    @pytest.mark.asyncio
    async def test_cambio_horario_inicio(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="10:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "08:00" not in slots
        assert "09:00" not in slots
        assert slots[0] == "10:00"

    @pytest.mark.asyncio
    async def test_dos_turnos_confirmados_excluyen_slots(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        t1 = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        )
        t2 = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        )
        db_session.add(t1)
        db_session.add(t2)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "09:00" not in slots
        assert "10:00" not in slots

    @pytest.mark.asyncio
    async def test_profesional_no_encontrado(self, db_session):
        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert slots == []

    @pytest.mark.asyncio
    async def test_slot_antes_de_turno(self, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        from app.services.availability_service import calcular_disponibilidad
        slots = await calcular_disponibilidad(db_session, date(2026, 6, 15))
        assert "08:30" in slots
