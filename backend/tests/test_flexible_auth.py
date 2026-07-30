"""Tests for the flexible (X-API-Key OR Bearer JWT) auth dependency on /turnos/*.

Covers C-26 (professional-flexible-auth): ``get_current_profesional_flexible``
must accept either a valid ``X-API-Key`` header or a valid ``Authorization:
Bearer <jwt>`` header as equivalent professional-scoped credentials, with
X-API-Key taking precedence when both are present, a single generic 401 on
total failure (no scheme leak), and inactive professionals rejected under
either scheme.

Target endpoint for the auth-matrix cases: ``GET /turnos/disponibles`` on
``fecha=2026-06-15`` (a Monday). Professional A uses the default Mon-Fri
schedule (20 slots that day); professional B only attends Tuesdays (0 slots
that day). This difference in slot count lets us assert *which* professional
was actually resolved by the dependency, not just that the call succeeded.
"""
import uuid

import pytest
from fastapi import status

from app.config import Settings
from app.models.profesional import Profesional
from app.services.auth_service import create_access_token, set_profesional_api_key
from tests.conftest import make_profesional_persisted

FECHA = "2026-06-15"  # Monday — matches professional A's default dias_atencion.


async def _seed_activa_con_api_key(db_session, **overrides) -> Profesional:
    """Persisted, active Profesional with a real ``api_key`` set.

    Uses ``make_profesional``'s default plaintext password ("test-password"),
    matching the hash it stores in ``password_hash``.

    Overrides ``email`` to the ``@local.dev`` domain (mirroring conftest's
    ``profesional`` fixture) instead of ``make_profesional``'s default
    ``@test.local`` — the latter fails ``EmailStr`` deliverability validation
    on ``POST /auth/login`` because ``.local`` is an mDNS special-use TLD.
    """
    overrides.setdefault("email", f"flex-{uuid.uuid4().hex[:8]}@local.dev")
    p = await make_profesional_persisted(db_session, **overrides)
    await set_profesional_api_key(db_session, p)
    await db_session.refresh(p)
    return p


async def _seed_inactiva_con_api_key(db_session, **overrides) -> Profesional:
    overrides["is_active"] = False
    return await _seed_activa_con_api_key(db_session, **overrides)


def _login_token(client, profesional: Profesional, password: str = "test-password") -> str:
    """Get a real JWT via ``POST /auth/login`` (only works for active profs)."""
    response = client.post(
        "/auth/login",
        json={"email": profesional.email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


def _mint_token_bypassing_login(profesional: Profesional) -> str:
    """Mint a valid JWT directly, bypassing the ``is_active`` login gate.

    Needed for the inactive-professional JWT scenario (2.8): login itself
    rejects inactive professionals, so we can't obtain a token that way even
    though the JWT payload/signature would otherwise be perfectly valid.
    """
    return create_access_token(profesional.id, profesional.email, Settings())


class TestFlexibleAuthTurnosDisponibles:
    """9-scenario auth matrix against GET /turnos/disponibles."""

    @pytest.mark.asyncio
    async def test_api_key_only_resuelve_profesional(self, client, db_session):
        """2.1: valid X-API-Key only, no Authorization -> 200, resolves A."""
        prof_a = await _seed_activa_con_api_key(db_session)

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"X-API-Key": prof_a.api_key},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 20

    @pytest.mark.asyncio
    async def test_jwt_only_resuelve_profesional_sin_cambios(self, client, db_session):
        """2.2: valid Bearer JWT only, no X-API-Key -> 200, same as pre-change JWT behavior."""
        prof_a = await _seed_activa_con_api_key(db_session)
        token = _login_token(client, prof_a)

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 20

    @pytest.mark.asyncio
    async def test_ambos_headers_validos_api_key_tiene_precedencia(self, client, db_session):
        """2.3: valid X-API-Key (A) + valid Bearer (B) -> 200, resolved is A."""
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session, dias_atencion=["Martes"])
        token_b = _login_token(client, prof_b)

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={
                "X-API-Key": prof_a.api_key,
                "Authorization": f"Bearer {token_b}",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        # A's schedule (Mon-Fri) yields 20 slots on FECHA; B's (Tuesday-only)
        # would yield 0. 20 proves A won, not B.
        assert len(response.json()) == 20

    @pytest.mark.asyncio
    async def test_api_key_invalido_cae_a_jwt_valido(self, client, db_session):
        """2.4: invalid/unknown X-API-Key + valid Bearer (B) -> 200, falls through to B (OR semantics)."""
        prof_b = await _seed_activa_con_api_key(db_session, dias_atencion=["Martes"])
        token_b = _login_token(client, prof_b)

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={
                "X-API-Key": "this-key-does-not-exist",
                "Authorization": f"Bearer {token_b}",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        # B only attends Tuesdays; FECHA is a Monday -> 0 slots. Proves B
        # (not A, not a stale/empty resolution) was actually used.
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_sin_headers_401_generico(self, client, db_session):
        """2.5: no auth headers at all -> 401, generic body."""
        response = client.get("/turnos/disponibles", params={"fecha": FECHA})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Credenciales inválidas"

    @pytest.mark.asyncio
    async def test_api_key_invalido_sin_jwt_401_mismo_body_que_sin_headers(self, client, db_session):
        """2.6: invalid X-API-Key, no Bearer -> 401, byte-identical detail to 2.5 (no scheme leak)."""
        sin_headers = client.get("/turnos/disponibles", params={"fecha": FECHA})

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"X-API-Key": "this-key-does-not-exist"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == sin_headers.json()["detail"] == "Credenciales inválidas"

    @pytest.mark.asyncio
    async def test_api_key_de_profesional_inactivo_401(self, client, db_session):
        """2.7: valid X-API-Key belonging to an inactive professional, no JWT -> 401."""
        prof_c = await _seed_inactiva_con_api_key(db_session)

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"X-API-Key": prof_c.api_key},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_jwt_de_profesional_inactivo_401(self, client, db_session):
        """2.8: valid Bearer JWT belonging to an inactive professional, no X-API-Key -> 401."""
        prof_c = await _seed_inactiva_con_api_key(db_session)
        token_c = _mint_token_bypassing_login(prof_c)

        response = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"Authorization": f"Bearer {token_c}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_endpoint_no_turno_no_afectado_por_x_api_key(self, client, db_session):
        """2.9: a non-/turnos/* professional endpoint keeps its JWT-only dependency.

        GET /pacientes carries only a valid X-API-Key and no Authorization —
        the flexible dependency is not wired there, so it must still reject
        (401/403, same as the existing JWT-only contract; HTTPBearer with
        auto_error=True returns 403 when the Authorization header is absent).
        """
        prof_a = await _seed_activa_con_api_key(db_session)

        response = client.get("/pacientes", headers={"X-API-Key": prof_a.api_key})

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestFlexibleAuthTenantIsolation:
    """5.1: X-API-Key-authenticated /turnos/* calls stay scoped to the resolved professional."""

    @pytest.mark.asyncio
    async def test_api_key_scoping_identico_a_jwt_scoping(self, client, db_session):
        prof_a = await _seed_activa_con_api_key(db_session)
        prof_b = await _seed_activa_con_api_key(db_session, dias_atencion=["Martes"])

        by_api_key = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"X-API-Key": prof_a.api_key},
        )
        token_a = _login_token(client, prof_a)
        by_jwt = client.get(
            "/turnos/disponibles",
            params={"fecha": FECHA},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # Same professional, same day -> identical slot set regardless of scheme.
        assert by_api_key.status_code == by_jwt.status_code == status.HTTP_200_OK
        assert by_api_key.json() == by_jwt.json()
        assert len(by_api_key.json()) == 20  # A's slots, never B's (0).


class TestGetProfesionalByApiKeyUntouched:
    """5.2: get_profesional_by_api_key (used by recordatorios.py) stays independent."""

    def test_recordatorios_key_invalida_mantiene_mensaje_propio(self, client):
        """Regression: the recordatorios-only dependency keeps its own distinct
        401 message ("API Key inválida"), proving it was not merged/aliased
        into the new flexible dependency's shared generic message."""
        response = client.post(
            "/api/v1/recordatorios/run?fecha=2026-06-16",
            headers={"X-API-Key": "this-key-does-not-exist"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "API Key inválida"
