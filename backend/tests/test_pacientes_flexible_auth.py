"""Tests for the flexible (X-API-Key OR Bearer JWT) auth widened onto /pacientes/*.

Covers c-27 group 4 (CRITICAL governance — explicit human approval granted by
the user in conversation on 2026-07-31, task 4.1). The four pre-existing
``pacientes.py`` endpoints plus the new ``GET /pacientes/buscar`` (c-27 groups
2-3) swap ``CurrentProfesionalDep`` for ``FlexibleProfesionalDep``, reusing
``get_current_profesional_flexible`` unchanged (design.md § D2). This widens
what the n8n API-key credential can reach from ``/turnos/*`` (c-26) to
``/pacientes/*`` too. Scope stays bounded exactly as before: every query is
still scoped by the resolved ``profesional_id``.

One test per endpoint for the two acceptance scenarios (4.2, 4.3), matching
the design's explicit-test-per-endpoint requirement instead of a single
dependency-level test, since this is an auth-surface change.
"""
import uuid

import pytest
from fastapi import status

from app.config import Settings
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.services.auth_service import create_access_token, set_profesional_api_key
from tests.conftest import make_profesional_persisted


async def _seed_activa_con_api_key(db_session, **overrides) -> Profesional:
    """Persisted, active Profesional with a real ``api_key`` set.

    Mirrors ``test_flexible_auth.py``'s helper of the same name (kept as a
    local duplicate — these are independent test modules, not shared
    production code).
    """
    overrides.setdefault("email", f"pac-flex-{uuid.uuid4().hex[:8]}@local.dev")
    p = await make_profesional_persisted(db_session, **overrides)
    await set_profesional_api_key(db_session, p)
    await db_session.refresh(p)
    return p


async def _seed_inactiva_con_api_key(db_session, **overrides) -> Profesional:
    overrides["is_active"] = False
    return await _seed_activa_con_api_key(db_session, **overrides)


def _login_token(client, profesional: Profesional, password: str = "test-password") -> str:
    response = client.post(
        "/auth/login",
        json={"email": profesional.email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


PACIENTE_PAYLOAD = {
    "nombre": "Juan",
    "apellido": "Pérez",
    "dni": "30111222",
    "telefono": "1122334455",
}


async def _seed_paciente(db_session, profesional_id: int, **overrides) -> Paciente:
    defaults = {
        "nombre": "Ana",
        "apellido": "García",
        "dni": "33333333",
        "telefono": "4",
    }
    defaults.update(overrides)
    paciente = Paciente(profesional_id=profesional_id, **defaults)
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


class TestApiKeyAceptadoEnPacientes:
    """4.2: a valid X-API-Key is accepted on each of the five endpoints."""

    @pytest.mark.asyncio
    async def test_post_pacientes_api_key_aceptado(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)

        response = client.post(
            "/pacientes",
            json=PACIENTE_PAYLOAD,
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_get_pacientes_api_key_aceptado(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)

        response = client.get("/pacientes", headers={"X-API-Key": prof.api_key})

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_paciente_por_id_api_key_aceptado(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        paciente = await _seed_paciente(db_session, prof.id)

        response = client.get(f"/pacientes/{paciente.id}", headers={"X-API-Key": prof.api_key})

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_api_key_aceptado(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        paciente = await _seed_paciente(db_session, prof.id)

        response = client.get(f"/pacientes/{paciente.id}/turnos", headers={"X-API-Key": prof.api_key})

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_pacientes_buscar_api_key_aceptado(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        await _seed_paciente(db_session, prof.id, dni="30111222")

        response = client.get(
            "/pacientes/buscar",
            params={"dni": "30111222"},
            headers={"X-API-Key": prof.api_key},
        )

        assert response.status_code == status.HTTP_200_OK


class TestJwtSigueFuncionandoEnPacientes:
    """4.3: an existing Bearer JWT still works — regression guard, the JWT
    path must not be traded away for the key path."""

    @pytest.mark.asyncio
    async def test_post_pacientes_jwt_sigue_funcionando(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        token = _login_token(client, prof)

        response = client.post(
            "/pacientes",
            json=PACIENTE_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_get_pacientes_jwt_sigue_funcionando(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        token = _login_token(client, prof)

        response = client.get("/pacientes", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_paciente_por_id_jwt_sigue_funcionando(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        token = _login_token(client, prof)
        paciente = await _seed_paciente(db_session, prof.id)

        response = client.get(
            f"/pacientes/{paciente.id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_paciente_turnos_jwt_sigue_funcionando(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        token = _login_token(client, prof)
        paciente = await _seed_paciente(db_session, prof.id)

        response = client.get(
            f"/pacientes/{paciente.id}/turnos", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_pacientes_buscar_jwt_sigue_funcionando(self, client, db_session):
        prof = await _seed_activa_con_api_key(db_session)
        token = _login_token(client, prof)
        await _seed_paciente(db_session, prof.id, dni="30111222")

        response = client.get(
            "/pacientes/buscar",
            params={"dni": "30111222"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK


class TestSinCredencialesPacientes:
    """4.4: no credentials at all -> 401 generic, no scheme disclosed."""

    @pytest.mark.asyncio
    async def test_sin_credenciales_401_generico(self, client, db_session):
        sin_headers = client.get("/pacientes")

        assert sin_headers.status_code == status.HTTP_401_UNAUTHORIZED
        assert sin_headers.json()["detail"] == "Credenciales inválidas"

    @pytest.mark.asyncio
    async def test_api_key_invalida_sin_jwt_401_mismo_body_que_sin_headers(self, client, db_session):
        """No scheme leak: an invalid X-API-Key alone gets the byte-identical
        generic 401 body as sending no headers at all."""
        sin_headers = client.get("/pacientes")

        response = client.get(
            "/pacientes", headers={"X-API-Key": "this-key-does-not-exist"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == sin_headers.json()["detail"] == "Credenciales inválidas"


class TestApiKeyInactivaPacientes:
    """4.5: an X-API-Key belonging to an inactive professional -> 401."""

    @pytest.mark.asyncio
    async def test_api_key_profesional_inactivo_401(self, client, db_session):
        prof = await _seed_inactiva_con_api_key(db_session)

        response = client.get("/pacientes", headers={"X-API-Key": prof.api_key})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAislamientoPorApiKeyPacientes:
    """4.6: a professional authenticated by API key sees only their own
    patients — cross-professional isolation."""

    @pytest.mark.asyncio
    async def test_api_key_aislamiento_entre_profesionales(self, client, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)

        await _seed_paciente(db_session, prof_a.id, nombre="Mio", apellido="Propio", dni="20000001", telefono="1")
        await _seed_paciente(db_session, prof_b.id, nombre="Ajeno", apellido="Otro", dni="20000002", telefono="2")

        response = client.get("/pacientes", headers={"X-API-Key": prof_a.api_key})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Mio"

    @pytest.mark.asyncio
    async def test_api_key_buscar_aislamiento_entre_profesionales(self, client, db_session):
        """Same isolation guarantee on the new /pacientes/buscar lookup."""
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session)

        await _seed_paciente(db_session, prof_a.id, nombre="Propio", apellido="A", dni="30111222", telefono="1")
        await _seed_paciente(db_session, prof_b.id, nombre="Ajeno", apellido="B", dni="30111222", telefono="2")

        response = client.get(
            "/pacientes/buscar", params={"dni": "30111222"}, headers={"X-API-Key": prof_a.api_key}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["nombre"] == "Propio"
