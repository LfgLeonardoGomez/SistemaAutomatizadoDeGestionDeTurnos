import pytest
from datetime import date, time

from app.models.paciente import Paciente
from app.models.turno import Turno
from tests.conftest import make_profesional


class TestPacientesRouter:
    """Tests de integración para /pacientes — con autenticación."""

    @pytest.mark.asyncio
    async def test_post_crear_paciente(self, authenticated_client, db_session, profesional):
        """Scenario: POST /pacientes crea paciente."""
        payload = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "dni": "12345678",
            "telefono": "+54 9 11 1234-5678",
        }
        response = authenticated_client.post("/pacientes", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Juan"
        assert data["apellido"] == "Pérez"
        assert data["dni"] == "12345678"
        assert data["telefono"] == "+54 9 11 1234-5678"
        assert data["id"] is not None
        assert "profesional_id" not in data  # schema no expone este campo

    @pytest.mark.asyncio
    async def test_post_paciente_dni_existente(self, authenticated_client, db_session, profesional):
        """Scenario: POST /pacientes con DNI existente retorna 409 o existente."""
        payload = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "dni": "12345678",
            "telefono": "1",
        }
        r1 = authenticated_client.post("/pacientes", json=payload)
        assert r1.status_code == 201

        payload2 = {
            "nombre": "Otro",
            "apellido": "Nombre",
            "dni": "12345678",
            "telefono": "2",
        }
        r2 = authenticated_client.post("/pacientes", json=payload2)
        # Auto-identificación: retorna 200 OK con el existente
        assert r2.status_code == 200
        assert r2.json()["id"] == r1.json()["id"]
        assert r2.json()["nombre"] == "Juan"

    @pytest.mark.asyncio
    async def test_post_paciente_datos_incompletos(self, authenticated_client, db_session, profesional):
        """Scenario: POST /pacientes sin campos requeridos → 422."""
        payload = {"apellido": "Pérez", "dni": "12345678"}
        response = authenticated_client.post("/pacientes", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_paciente_con_historial(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes/{id} retorna paciente con turnos."""
        paciente = Paciente(
            nombre="Ana", apellido="García", dni="33333333", telefono="4",
            profesional_id=profesional.id,
        )
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

        response = authenticated_client.get(f"/pacientes/{paciente.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == paciente.id
        assert data["nombre"] == "Ana"
        assert len(data["turnos"]) == 1
        assert data["turnos"][0]["estado"] == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_get_paciente_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes/{id} no existe → 404."""
        response = authenticated_client.get("/pacientes/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paciente_turnos(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes/{id}/turnos retorna lista."""
        paciente = Paciente(
            nombre="Luis", apellido="Lopez", dni="44444444", telefono="5",
            profesional_id=profesional.id,
        )
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

        response = authenticated_client.get(f"/pacientes/{paciente.id}/turnos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes/{id}/turnos paciente no existe → 404."""
        response = authenticated_client.get("/pacientes/9999/turnos")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_vacio(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes/{id}/turnos paciente sin turnos → 200 lista vacía."""
        paciente = Paciente(
            nombre="Pepe", apellido="Argento", dni="55555555", telefono="6",
            profesional_id=profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        response = authenticated_client.get(f"/pacientes/{paciente.id}/turnos")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_pacientes_lista_ordenada(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes retorna todos los pacientes del profesional, ordenados por apellido/nombre."""
        for nombre, apellido, dni in [
            ("Ana", "Zapata", "10000001"),
            ("Beto", "Alvarez", "10000002"),
            ("Carla", "Alvarez", "10000003"),
        ]:
            db_session.add(Paciente(
                nombre=nombre, apellido=apellido, dni=dni, telefono="1",
                profesional_id=profesional.id,
            ))
        await db_session.commit()

        response = authenticated_client.get("/pacientes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        # Ordenado por apellido, luego nombre: Alvarez/Beto, Alvarez/Carla, Zapata/Ana
        assert [p["apellido"] for p in data] == ["Alvarez", "Alvarez", "Zapata"]
        assert [p["nombre"] for p in data[:2]] == ["Beto", "Carla"]
        assert "profesional_id" not in data[0]  # schema no expone tenant

    @pytest.mark.asyncio
    async def test_get_pacientes_solo_los_del_profesional(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes NO incluye pacientes de otro profesional (aislamiento multi-tenant)."""
        otro = make_profesional(
            nombre="Dr. B", dias_atencion=["Lunes"],
            email="drb2@local.dev", password_hash="fakehash",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        db_session.add(Paciente(
            nombre="Mio", apellido="Propio", dni="20000001", telefono="1",
            profesional_id=profesional.id,
        ))
        db_session.add(Paciente(
            nombre="Ajeno", apellido="Otro", dni="20000002", telefono="2",
            profesional_id=otro.id,
        ))
        await db_session.commit()

        response = authenticated_client.get("/pacientes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Mio"

    @pytest.mark.asyncio
    async def test_get_pacientes_limit_offset(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes respeta limit y offset."""
        for i in range(5):
            db_session.add(Paciente(
                nombre=f"P{i}", apellido=f"Ap{i:02d}", dni=f"3000000{i}", telefono="1",
                profesional_id=profesional.id,
            ))
        await db_session.commit()

        r_limit = authenticated_client.get("/pacientes?limit=2")
        assert r_limit.status_code == 200
        assert len(r_limit.json()) == 2

        r_offset = authenticated_client.get("/pacientes?limit=2&offset=2")
        assert r_offset.status_code == 200
        data_offset = r_offset.json()
        assert len(data_offset) == 2
        # offset avanza en el orden por apellido: Ap02, Ap03
        assert data_offset[0]["apellido"] == "Ap02"

    @pytest.mark.asyncio
    async def test_get_pacientes_vacio(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes sin pacientes → 200 lista vacía."""
        response = authenticated_client.get("/pacientes")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_pacientes_sin_token_401(self, client, db_session, profesional):
        """Scenario: GET /pacientes sin token → 401/403."""
        response = client.get("/pacientes")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_pacientes_limit_invalido_422(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes con limit fuera de rango → 422."""
        assert authenticated_client.get("/pacientes?limit=0").status_code == 422
        assert authenticated_client.get("/pacientes?limit=101").status_code == 422

    @pytest.mark.asyncio
    async def test_get_paciente_otro_profesional_devuelve_404(self, authenticated_client, db_session, profesional):
        """Scenario: GET /pacientes/{id} de otro profesional → 404."""
        otro_profesional = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
        )
        db_session.add(otro_profesional)
        await db_session.commit()
        await db_session.refresh(otro_profesional)

        paciente = Paciente(
            nombre="Otro", apellido="Paciente", dni="99999999", telefono="9",
            profesional_id=otro_profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        response = authenticated_client.get(f"/pacientes/{paciente.id}")
        assert response.status_code == 404
