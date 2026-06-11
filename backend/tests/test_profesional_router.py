import pytest
from datetime import date, time

from app.models.profesional import Profesional
from app.models.turno import Turno


class TestProfesionalRouter:
    @pytest.mark.asyncio
    async def test_get_configuracion(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        response = api_client.get("/profesional/configuracion")
        assert response.status_code == 200
        data = response.json()
        assert data["horario_inicio"] == "08:00"
        assert data["horario_fin"] == "18:00"
        assert data["dias_atencion"] == ["Lunes", "Martes"]
        assert data["duracion_turno"] == 30
        assert data["especialidad"] == "Odontología"

    @pytest.mark.asyncio
    async def test_put_configuracion(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        payload = {"duracion_turno": 60, "horario_inicio": "09:00"}
        response = api_client.put("/profesional/configuracion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["duracion_turno"] == 60
        assert data["horario_inicio"] == "09:00"
        assert data["horario_fin"] == "18:00"

    @pytest.mark.asyncio
    async def test_put_configuracion_validacion_horario(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        payload = {"horario_inicio": "18:00", "horario_fin": "08:00"}
        response = api_client.put("/profesional/configuracion", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_put_configuracion_validacion_duracion(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        payload = {"duracion_turno": 0}
        response = api_client.put("/profesional/configuracion", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_put_configuracion_validacion_dias(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        payload = {"dias_atencion": []}
        response = api_client.put("/profesional/configuracion", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_configuracion_no_profesional(self, api_client, db_session):
        response = api_client.get("/profesional/configuracion")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_put_configuracion_multiple_fields(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        payload = {
            "duracion_turno": 45,
            "horario_inicio": "07:00",
            "horario_fin": "17:00",
            "dias_atencion": ["Lunes", "Miércoles", "Viernes"],
        }
        response = api_client.put("/profesional/configuracion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["duracion_turno"] == 45
        assert data["horario_inicio"] == "07:00"
        assert data["horario_fin"] == "17:00"
        assert data["dias_atencion"] == ["Lunes", "Miércoles", "Viernes"]
        assert data["especialidad"] == "Odontología"

    @pytest.mark.asyncio
    async def test_put_configuracion_validacion_dia_invalido(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        payload = {"dias_atencion": ["Lunes", "Invalido"]}
        response = api_client.put("/profesional/configuracion", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_disponibilidad_dia_laborable(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        response = api_client.get("/profesional/disponibilidad?fecha=2026-06-15")
        assert response.status_code == 200
        data = response.json()
        assert len(data["horarios"]) == 20
        assert data["horarios"][0] == "08:00"
        assert data["horarios"][-1] == "17:30"

    @pytest.mark.asyncio
    async def test_get_disponibilidad_dia_no_laborable(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Martes"],
        )
        db_session.add(profesional)
        await db_session.commit()

        response = api_client.get("/profesional/disponibilidad?fecha=2026-06-15")
        assert response.status_code == 200
        data = response.json()
        assert data["horarios"] == []

    @pytest.mark.asyncio
    async def test_get_disponibilidad_con_turno_ocupado(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
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

        response = api_client.get("/profesional/disponibilidad?fecha=2026-06-15")
        assert response.status_code == 200
        data = response.json()
        assert "09:00" not in data["horarios"]

    @pytest.mark.asyncio
    async def test_get_disponibilidad_fecha_invalida(self, api_client, db_session):
        response = api_client.get("/profesional/disponibilidad?fecha=invalid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_disponibilidad_reservado_temporal(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
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

        response = api_client.get("/profesional/disponibilidad?fecha=2026-06-15")
        assert response.status_code == 200
        data = response.json()
        assert "10:00" not in data["horarios"]

    @pytest.mark.asyncio
    async def test_get_disponibilidad_no_profesional(self, api_client, db_session):
        response = api_client.get("/profesional/disponibilidad?fecha=2026-06-15")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_disponibilidad_adyacente(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
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

        response = api_client.get("/profesional/disponibilidad?fecha=2026-06-15")
        assert response.status_code == 200
        data = response.json()
        assert "09:30" in data["horarios"]
