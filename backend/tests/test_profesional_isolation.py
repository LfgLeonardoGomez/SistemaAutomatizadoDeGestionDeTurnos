"""Cross-professional isolation tests and integration-specific tests for C-22.

Tests verify:
1. PUT /profesional/integraciones partial update of google_calendar_id
2. PUT /profesional/integraciones rejects empty google_calendar_id
3. Cross-professional isolation for list endpoints
"""

import pytest
from datetime import date, time

from app.models.lista_de_espera import ListaDeEspera
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.services.auth_service import hash_password


async def _create_profesional(db_session, email: str, nombre: str = "Dr. Test") -> Profesional:
    """Create and persist a second profesional for isolation tests."""
    p = Profesional(
        nombre=nombre,
        especialidad="Test",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        email=email,
        password_hash=hash_password("changeme"),
        is_active=True,
        google_calendar_id="primary",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


def _get_token(client, email: str, password: str = "changeme") -> str:
    """Login and return the access token."""
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


class TestIntegracionesGoogleCalendarId:
    """T-14: google_calendar_id partial update and validation via router."""

    @pytest.mark.asyncio
    async def test_put_integraciones_partial_update_calendar_id(
        self, api_client, db_session, profesional
    ):
        """Scenario: PUT /profesional/integraciones with only google_calendar_id updates just that field."""
        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.put(
            "/profesional/integraciones",
            json={"google_calendar_id": "custom@group.calendar.google.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["google_calendar_id"] == "custom@group.calendar.google.com"
        # Other fields unchanged — has_telegram and has_google should be False
        assert data["has_telegram"] is False
        assert data["has_google"] is False

        del api_client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_put_integraciones_rejects_empty_calendar_id(
        self, api_client, db_session, profesional
    ):
        """Scenario: PUT /profesional/integraciones with empty google_calendar_id → 422."""
        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.put(
            "/profesional/integraciones",
            json={"google_calendar_id": ""},
        )
        assert response.status_code == 422

        del api_client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_get_integraciones_returns_calendar_id(
        self, api_client, db_session, profesional
    ):
        """Scenario: GET /profesional/integraciones returns google_calendar_id."""
        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.get("/profesional/integraciones")
        assert response.status_code == 200
        data = response.json()
        assert "google_calendar_id" in data
        assert data["google_calendar_id"] == "primary"

        del api_client.headers["Authorization"]


class TestCrossProfessionalIsolation:
    """T-14: Verify professional A cannot access professional B's data."""

    @pytest.mark.asyncio
    async def test_turnos_hoy_isolation(self, api_client, db_session, profesional):
        """Scenario: GET /profesional/turnos-hoy returns only own turnos."""
        other = await _create_profesional(db_session, "other@local.dev", "Dr. Other")

        # Create a turno for the other professional today
        hoy = date.today()
        turno = Turno(
            fecha=hoy,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=other.id,
            paciente_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        # Authenticate as the original profesional
        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.get("/profesional/turnos-hoy")
        assert response.status_code == 200
        data = response.json()
        # Should be empty — the turno belongs to the other professional
        assert len(data) == 0

        del api_client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_paciente_turnos_isolation(self, api_client, db_session, profesional):
        """Scenario: GET /pacientes/{id}/turnos for another professional's patient → 404."""
        other = await _create_profesional(db_session, "other2@local.dev", "Dr. Other2")

        paciente = Paciente(
            nombre="Otro", apellido="Paciente", dni="88888888", telefono="8",
            profesional_id=other.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.get(f"/pacientes/{paciente.id}/turnos")
        assert response.status_code == 404

        del api_client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_lista_espera_delete_isolation(self, api_client, db_session, profesional):
        """Scenario: DELETE /lista-espera/{id} for another professional's entry → 404."""
        other = await _create_profesional(db_session, "other3@local.dev", "Dr. Other3")

        paciente = Paciente(
            nombre="Wait", apellido="List", dni="77777777", telefono="7",
            profesional_id=other.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=date(2026, 7, 1),
            telegram_chat_id="12345",
            profesional_id=other.id,
        )
        db_session.add(registro)
        await db_session.commit()

        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.delete(f"/lista-espera/{registro.id}")
        assert response.status_code == 404

        del api_client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_turno_cancel_isolation(self, api_client, db_session, profesional):
        """Scenario: PUT /turnos/{id}/cancelar for another professional's turno → 404."""
        other = await _create_profesional(db_session, "other4@local.dev", "Dr. Other4")

        turno = Turno(
            fecha=date(2026, 7, 1),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            estado="CONFIRMADO",
            profesional_id=other.id,
            paciente_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        token = _get_token(api_client, profesional.email)
        api_client.headers["Authorization"] = f"Bearer {token}"

        response = api_client.put(f"/turnos/{turno.id}/cancelar")
        assert response.status_code == 404

        del api_client.headers["Authorization"]
