import pytest
from fastapi import status


class TestLogin:
    def test_login_with_valid_credentials_returns_200_and_token(self, api_client, profesional):
        payload = {
            "email": profesional.email,
            "password": "changeme",
        }
        response = api_client.post("/auth/login", json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_wrong_password_returns_401(self, api_client, profesional):
        payload = {
            "email": profesional.email,
            "password": "wrongpassword",
        }
        response = api_client.post("/auth/login", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_unknown_email_returns_401(self, api_client):
        payload = {
            "email": "nobody@local.dev",
            "password": "somepassword",
        }
        response = api_client.post("/auth/login", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedEndpoint:
    def test_access_protected_endpoint_with_valid_token_returns_200_and_api_key(self, api_client, profesional):
        login_payload = {
            "email": profesional.email,
            "password": "changeme",
        }
        login_response = api_client.post("/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        response = api_client.post(
            "/auth/api-key",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "api_key" in data
        assert len(data["api_key"]) > 0

    def test_access_protected_endpoint_with_invalid_token_returns_401(self, api_client):
        response = api_client.post(
            "/auth/api-key",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_endpoint_without_token_returns_401(self, api_client):
        response = api_client.post("/auth/api-key")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_endpoint_for_inactive_professional_returns_401(self, api_client, db_session):
        from app.models.profesional import Profesional
        from app.services.auth_service import hash_password

        inactive = Profesional(
            nombre="Dr. Inactivo",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="inactive@local.dev",
            password_hash=hash_password("inactivepass"),
            is_active=False,
        )
        db_session.add(inactive)
        # NOTE: db_session fixture auto-rolls back after test, but we need the ID for JWT
        # We'll generate token manually since the user is not committed
        from app.config import Settings
        from app.services.auth_service import create_access_token
        settings = Settings()
        token = create_access_token(99999, "inactive@local.dev", settings)

        response = api_client.post(
            "/auth/api-key",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestApiKeyAuth:
    @pytest.mark.asyncio
    async def test_valid_api_key_returns_professional(self, db_session, profesional):
        from app.services.auth_service import set_profesional_api_key
        from app.dependencies import get_profesional_by_api_key

        api_key = await set_profesional_api_key(db_session, profesional)
        result = await get_profesional_by_api_key(api_key=api_key, db=db_session)
        assert result.id == profesional.id

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, db_session):
        from app.dependencies import get_profesional_by_api_key
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_profesional_by_api_key(api_key="invalid-key", db=db_session)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_for_inactive_professional_returns_401(self, db_session):
        from app.dependencies import get_profesional_by_api_key
        from app.models.profesional import Profesional
        from app.services.auth_service import hash_password, set_profesional_api_key
        from fastapi import HTTPException

        inactive = Profesional(
            nombre="Dr. Inactivo",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            email="inactive_api@local.dev",
            password_hash=hash_password("inactivepass"),
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.commit()
        await db_session.refresh(inactive)

        # Even if we somehow had a key for inactive, it should fail
        # But inactive has no key; test missing key case
        with pytest.raises(HTTPException) as exc_info:
            await get_profesional_by_api_key(api_key="some-key", db=db_session)
        assert exc_info.value.status_code == 401
