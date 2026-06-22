import pytest
from datetime import date
from unittest.mock import patch, AsyncMock


class TestListaEsperaAPI:
    def test_post_lista_espera_crea_registro(self, api_client):
        """Scenario: POST /lista-espera crea un registro en lista de espera."""
        # First create a paciente
        paciente_data = {
            "nombre": "Juan",
            "apellido": "Perez",
            "dni": "12345678",
            "telefono": "555-1234",
        }
        resp = api_client.post("/pacientes", json=paciente_data)
        assert resp.status_code in (200, 201)
        paciente_id = resp.json()["id"]

        lista_data = {
            "paciente_id": paciente_id,
            "fecha_solicitada": "2026-06-15",
            "telegram_chat_id": "12345",
        }
        resp = api_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["paciente_id"] == paciente_id
        assert body["fecha_solicitada"] == "2026-06-15"
        assert body["notificado"] is False
        assert body["turno_ofrecido_id"] is None
        assert body["telegram_chat_id"] == "12345"

    def test_post_lista_espera_paciente_inexistente(self, api_client):
        """Scenario: POST /lista-espera con paciente inexistente retorna 404."""
        lista_data = {
            "paciente_id": 99999,
            "fecha_solicitada": "2026-06-15",
        }
        resp = api_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 404

    def test_post_lista_espera_sin_fecha(self, api_client):
        """Scenario: POST /lista-espera sin fecha_solicitada retorna 422."""
        lista_data = {"paciente_id": 1}
        resp = api_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 422

    def test_delete_lista_espera_exitoso(self, api_client):
        """Scenario: DELETE /lista-espera/{id} elimina el registro."""
        paciente_data = {
            "nombre": "Ana",
            "apellido": "Garcia",
            "dni": "87654321",
            "telefono": "555-9999",
        }
        resp = api_client.post("/pacientes", json=paciente_data)
        assert resp.status_code in (200, 201)
        paciente_id = resp.json()["id"]

        lista_data = {
            "paciente_id": paciente_id,
            "fecha_solicitada": "2026-06-16",
        }
        resp = api_client.post("/lista-espera", json=lista_data)
        assert resp.status_code == 201
        lista_id = resp.json()["id"]

        resp = api_client.delete(f"/lista-espera/{lista_id}")
        assert resp.status_code == 204

    def test_delete_lista_espera_inexistente(self, api_client):
        """Scenario: DELETE /lista-espera/{id} con ID inexistente retorna 404."""
        resp = api_client.delete("/lista-espera/99999")
        assert resp.status_code == 404
