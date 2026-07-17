from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.core.auth.jwt import create_access_token, verify_token
from src.core.config import settings


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token({"sub": "admin"})
        assert isinstance(token, str)

    def test_contains_claims(self):
        token = create_access_token(
            {"sub": "admin", "role": "admin", "department_id": 1, "is_cross_department": False}
        )
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"
        assert payload["department_id"] == 1
        assert payload["is_cross_department"] is False

    def test_includes_iat_and_nbf(self):
        token = create_access_token({"sub": "admin"})
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        assert "iat" in payload
        assert "nbf" in payload
        assert isinstance(payload["iat"], int)
        assert isinstance(payload["nbf"], int)

    def test_expires_delta_respected(self):
        token = create_access_token({"sub": "admin"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        now = datetime.now(UTC)
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert exp > now


class TestVerifyToken:
    def test_returns_payload_for_valid_token(self):
        token = create_access_token({"sub": "admin", "role": "staff"})
        payload = verify_token(token)
        assert payload["sub"] == "admin"
        assert payload["role"] == "staff"

    def test_raises_on_expired_token(self):
        token = create_access_token({"sub": "admin"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(token)

    def test_raises_on_invalid_signature(self):
        token = jwt.encode({"sub": "admin"}, "x" * 32, algorithm="HS256")
        with pytest.raises(jwt.InvalidSignatureError):
            verify_token(token)

    def test_raises_on_malformed_token(self):
        with pytest.raises(jwt.PyJWTError):
            verify_token("not.a.token")
