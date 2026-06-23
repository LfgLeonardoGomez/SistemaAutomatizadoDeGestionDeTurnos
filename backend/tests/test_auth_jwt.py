import time

import pytest
from jose import jwt, JWTError

from app.config import Settings
from app.services.auth_service import create_access_token


@pytest.fixture
def jwt_settings(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-jwt")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    return Settings()


class TestCreateAccessToken:
    def test_returns_non_empty_string(self, jwt_settings):
        token = create_access_token(1, "test@example.com", jwt_settings)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decoding_valid_token_returns_correct_sub_and_email(self, jwt_settings):
        token = create_access_token(42, "test@example.com", jwt_settings)
        payload = jwt.decode(token, jwt_settings.secret_key, algorithms=[jwt_settings.algorithm])
        assert payload["sub"] == "42"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload

    def test_decoding_expired_token_raises_exception(self, jwt_settings, monkeypatch):
        monkeypatch.setattr(jwt_settings, "access_token_expire_minutes", -1)
        token = create_access_token(1, "test@example.com", jwt_settings)
        time.sleep(0.1)
        with pytest.raises(JWTError):
            jwt.decode(token, jwt_settings.secret_key, algorithms=[jwt_settings.algorithm])

    def test_decoding_malformed_token_raises_exception(self, jwt_settings):
        with pytest.raises(JWTError):
            jwt.decode("not.a.token", jwt_settings.secret_key, algorithms=[jwt_settings.algorithm])

    def test_different_professionals_get_different_tokens(self, jwt_settings):
        token1 = create_access_token(1, "a@example.com", jwt_settings)
        token2 = create_access_token(2, "b@example.com", jwt_settings)
        assert token1 != token2

    def test_token_contains_exp_and_iat(self, jwt_settings):
        import time as time_module
        before = int(time_module.time())
        token = create_access_token(1, "test@example.com", jwt_settings)
        after = int(time_module.time())
        payload = jwt.decode(token, jwt_settings.secret_key, algorithms=[jwt_settings.algorithm])
        assert "exp" in payload
        assert "iat" in payload
        assert before <= payload["iat"] <= after + 1
        expected_exp = payload["iat"] + jwt_settings.access_token_expire_minutes * 60
        assert payload["exp"] == expected_exp
