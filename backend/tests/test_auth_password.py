import pytest
from app.services.auth_service import hash_password, verify_password


class TestHashPassword:
    def test_hash_password_produces_different_hashes_for_same_input(self):
        password = "supersecret123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")

    def test_hash_password_returns_string(self):
        result = hash_password("anypassword")
        assert isinstance(result, str)
        assert len(result) > 0


class TestVerifyPassword:
    def test_verify_password_returns_true_for_correct_password(self):
        password = "supersecret123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_returns_false_for_incorrect_password(self):
        password = "supersecret123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_returns_false_for_empty_password(self):
        password = "supersecret123"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False
