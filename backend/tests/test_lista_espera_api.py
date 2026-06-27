import pytest
from datetime import date
from unittest.mock import patch, AsyncMock

from app.models.paciente import Paciente
from tests.conftest import make_profesional


class TestListaEsperaAPI:
    @pytest.mark.asyncio
    async def test_post_lista_espera_crea_registro(self, authenticated_client, db_session, profesional):
        """Scenario: POST /lista-espera crea un registro en lista de espera."""
        # First create a paciente
        paciente_data = {
            "nombre": "Juan",
            "apellido": "Perez",
            "dni": "12345678",
            "telefono": "555-1234",
        }
        resp = authenticated_client.post("/pacientes", json=paciente_data)
        assert resp.status_code in (200, 201)
        paciente_id = resp.json()["id"]

        lista_data = {
            "paciente_id": paciente_id,
            "fecha_solicitada": "2026-06-15",
            "telegram_chat_id": "12345",
        }
        resp = authenticated_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["paciente_id"] == paciente_id
        assert body["fecha_solicitada"] == "2026-06-15"
        assert body["notificado"] is False
        assert body["turno_ofrecido_id"] is None
        assert body["telegram_chat_id"] == "12345"

    @pytest.mark.asyncio
    async def test_post_lista_espera_paciente_inexistente(self, authenticated_client, db_session, profesional):
        """Scenario: POST /lista-espera con paciente inexistente retorna 404."""
        lista_data = {
            "paciente_id": 99999,
            "fecha_solicitada": "2026-06-15",
        }
        resp = authenticated_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_post_lista_espera_sin_fecha(self, authenticated_client, db_session, profesional):
        """Scenario: POST /lista-espera sin fecha_solicitada retorna 422."""
        lista_data = {"paciente_id": 1}
        resp = authenticated_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_lista_espera_exitoso(self, authenticated_client, db_session, profesional):
        """Scenario: DELETE /lista-espera/{id} elimina el registro."""
        paciente_data = {
            "nombre": "Ana",
            "apellido": "Garcia",
            "dni": "87654321",
            "telefono": "555-9999",
        }
        resp = authenticated_client.post("/pacientes", json=paciente_data)
        assert resp.status_code in (200, 201)
        paciente_id = resp.json()["id"]

        lista_data = {
            "paciente_id": paciente_id,
            "fecha_solicitada": "2026-06-16",
        }
        resp = authenticated_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 201
        lista_id = resp.json()["id"]

        resp = authenticated_client.delete(f"/lista-espera/{lista_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_lista_espera_inexistente(self, authenticated_client, db_session, profesional):
        """Scenario: DELETE /lista-espera/{id} con ID inexistente retorna 404."""
        resp = authenticated_client.delete("/lista-espera/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_lista_espera_otro_profesional(self, authenticated_client, db_session, profesional):
        """Scenario: DELETE /lista-espera/{id} de otro profesional retorna 404."""
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
            nombre="Otro", apellido="Paciente", dni="77777777", telefono="7",
            profesional_id=otro_profesional.id,
        )
        db_session.add(paciente)
        await db_session.commit()
        await db_session.refresh(paciente)

        from app.models.lista_de_espera import ListaDeEspera
        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 6, 15),
            profesional_id=otro_profesional.id,
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)

        resp = authenticated_client.delete(f"/lista-espera/{registro.id}")
        assert resp.status_code == 404
