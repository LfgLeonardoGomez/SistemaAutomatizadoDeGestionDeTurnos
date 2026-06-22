import pytest
from datetime import date, time

from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.paciente import Paciente


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


class TestProfesionalTurnosHoyEndpoint:
    @pytest.mark.asyncio
    async def test_get_turnos_hoy_returns_confirmed_with_paciente(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        paciente = Paciente(nombre="Juan", apellido="Pérez", dni="12345678", telefono="5551234")
        db_session.add(paciente)
        await db_session.flush()

        hoy = date.today()
        turno = Turno(
            fecha=hoy,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        response = api_client.get("/profesional/turnos-hoy")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["estado"] == "CONFIRMADO"
        assert data[0]["paciente"]["nombre"] == "Juan"
        assert data[0]["paciente"]["apellido"] == "Pérez"
        assert data[0]["paciente"]["dni"] == "12345678"
        assert data[0]["paciente"]["telefono"] == "5551234"

    @pytest.mark.asyncio
    async def test_get_turnos_hoy_empty_when_no_confirmed(self, api_client, db_session):
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

        response = api_client.get("/profesional/turnos-hoy")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_turnos_hoy_excludes_non_confirmed(self, api_client, db_session):
        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        hoy = date.today()
        turno_cancelado = Turno(
            fecha=hoy,
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            estado="CANCELADO",
        )
        turno_disponible = Turno(
            fecha=hoy,
            hora_inicio=time(11, 0),
            hora_fin=time(11, 30),
            profesional_id=profesional.id,
            estado="DISPONIBLE",
        )
        db_session.add(turno_cancelado)
        db_session.add(turno_disponible)
        await db_session.commit()

        response = api_client.get("/profesional/turnos-hoy")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestProfesionalMetricasEndpoint:
    @pytest.mark.asyncio
    async def test_get_metricas_returns_calculated_values(self, api_client, db_session):
        from datetime import timedelta

        profesional = Profesional(
            nombre="Dr. Test",
            especialidad="Odontología",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        hoy = date.today()
        # 2 confirmed today
        for h in [(8, 0), (9, 0)]:
            db_session.add(Turno(
                fecha=hoy,
                hora_inicio=time(h[0], h[1]),
                hora_fin=time(h[0], h[1] + 30),
                profesional_id=profesional.id,
                estado="CONFIRMADO",
            ))
        # 1 cancelled today
        db_session.add(Turno(
            fecha=hoy,
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            estado="CANCELADO",
        ))
        # 1 confirmed 15 days ago
        db_session.add(Turno(
            fecha=hoy - timedelta(days=15),
            hora_inicio=time(11, 0),
            hora_fin=time(11, 30),
            profesional_id=profesional.id,
            estado="CONFIRMADO",
        ))
        # 1 cancelled 20 days ago
        db_session.add(Turno(
            fecha=hoy - timedelta(days=20),
            hora_inicio=time(12, 0),
            hora_fin=time(12, 30),
            profesional_id=profesional.id,
            estado="CANCELADO",
        ))
        await db_session.commit()

        response = api_client.get("/profesional/metricas")
        assert response.status_code == 200
        data = response.json()
        assert data["turnos_hoy"] == 2
        # total in last 30d = 5 (2 today + 1 today cancelled + 1 15d + 1 20d)
        # confirmados 30d = 3
        # cancelados 30d = 2
        assert data["tasa_confirmacion_30d"] == 0.6
        assert data["tasa_cancelacion_30d"] == 0.4

    @pytest.mark.asyncio
    async def test_get_metricas_zero_when_no_data(self, api_client, db_session):
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

        response = api_client.get("/profesional/metricas")
        assert response.status_code == 200
        data = response.json()
        assert data["turnos_hoy"] == 0
        assert data["tasa_confirmacion_30d"] == 0.0
        assert data["tasa_cancelacion_30d"] == 0.0

    @pytest.mark.asyncio
    async def test_get_metricas_response_model_filters_extra_fields(self, api_client, db_session):
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

        response = api_client.get("/profesional/metricas")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"turnos_hoy", "tasa_confirmacion_30d", "tasa_cancelacion_30d"}
