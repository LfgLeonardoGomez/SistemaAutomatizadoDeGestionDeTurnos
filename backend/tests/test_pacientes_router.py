import pytest
from datetime import date, time

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno


class TestPacientesRouter:
    """Tests de integración para /pacientes — Task 3.5."""

    @pytest.mark.asyncio
    async def test_post_crear_paciente(self, api_client, db_session):
        """Scenario: POST /pacientes crea paciente."""
        payload = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "dni": "12345678",
            "telefono": "+54 9 11 1234-5678",
        }
        response = api_client.post("/pacientes", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Juan"
        assert data["apellido"] == "Pérez"
        assert data["dni"] == "12345678"
        assert data["telefono"] == "+54 9 11 1234-5678"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_post_paciente_dni_existente(self, api_client, db_session):
        """Scenario: POST /pacientes con DNI existente retorna 409 o existente."""
        payload = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "dni": "12345678",
            "telefono": "1",
        }
        r1 = api_client.post("/pacientes", json=payload)
        assert r1.status_code == 201

        payload2 = {
            "nombre": "Otro",
            "apellido": "Nombre",
            "dni": "12345678",
            "telefono": "2",
        }
        r2 = api_client.post("/pacientes", json=payload2)
        # Auto-identificación: retorna 200 OK con el existente
        assert r2.status_code == 200
        assert r2.json()["id"] == r1.json()["id"]
        assert r2.json()["nombre"] == "Juan"

    @pytest.mark.asyncio
    async def test_post_paciente_datos_incompletos(self, api_client, db_session):
        """Scenario: POST /pacientes sin campos requeridos → 422."""
        payload = {"apellido": "Pérez", "dni": "12345678"}
        response = api_client.post("/pacientes", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_paciente_con_historial(self, api_client, db_session):
        """Scenario: GET /pacientes/{id} retorna paciente con turnos."""
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

        paciente = Paciente(nombre="Ana", apellido="García", dni="33333333", telefono="4")
        db_session.add(paciente)
        await db_session.flush()

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        db_session.add(turno)
        await db_session.commit()

        response = api_client.get(f"/pacientes/{paciente.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == paciente.id
        assert data["nombre"] == "Ana"
        assert len(data["turnos"]) == 1
        assert data["turnos"][0]["estado"] == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_get_paciente_no_existe(self, api_client, db_session):
        """Scenario: GET /pacientes/{id} no existe → 404."""
        response = api_client.get("/pacientes/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paciente_turnos(self, api_client, db_session):
        """Scenario: GET /pacientes/{id}/turnos retorna lista."""
        profesional = Profesional(
            nombre="Dr. Turnos",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
        )
        db_session.add(profesional)
        await db_session.flush()

        paciente = Paciente(nombre="Luis", apellido="Lopez", dni="44444444", telefono="5")
        db_session.add(paciente)
        await db_session.flush()

        t1 = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        t2 = Turno(
            fecha=date(2026, 6, 16),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            estado="CONFIRMADO",
        )
        db_session.add(t1)
        db_session.add(t2)
        await db_session.commit()

        response = api_client.get(f"/pacientes/{paciente.id}/turnos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_no_existe(self, api_client, db_session):
        """Scenario: GET /pacientes/{id}/turnos paciente no existe → 404."""
        response = api_client.get("/pacientes/9999/turnos")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_vacio(self, api_client, db_session):
        """Scenario: GET /pacientes/{id}/turnos paciente sin turnos → 200 lista vacía."""
        paciente = Paciente(nombre="Pepe", apellido="Argento", dni="55555555", telefono="6")
        db_session.add(paciente)
        await db_session.commit()

        response = api_client.get(f"/pacientes/{paciente.id}/turnos")
        assert response.status_code == 200
        data = response.json()
        assert data == []
