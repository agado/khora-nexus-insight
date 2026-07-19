from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.auth.rbac import get_current_user, require_role


class TestLoginEndpoint:
    def test_login_success(self, client):
        with (
            patch(
                "src.api.v1.auth.authenticate_user",
                new_callable=AsyncMock,
            ) as mock_auth,
            patch(
                "src.api.v1.auth.log_action",
                new_callable=AsyncMock,
            ),
        ):
            mock_auth.return_value = {"access_token": "valid.jwt.token", "user_id": 1}
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "valid.jwt.token"
            assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        with (
            patch(
                "src.api.v1.auth.authenticate_user",
                new_callable=AsyncMock,
            ) as mock_auth,
            patch(
                "src.api.v1.auth.log_action",
                new_callable=AsyncMock,
            ),
        ):
            mock_auth.return_value = None
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid credentials"

    def test_login_missing_fields(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


class TestRBAC:
    @pytest.fixture(autouse=True)
    def _setup_test_app(self):
        test_app = FastAPI()

        @test_app.get("/_test/protected")
        async def protected(user: dict = Depends(get_current_user)):
            return {"user": user}

        @test_app.get("/_test/admin")
        async def admin_only(user: dict = Depends(require_role("admin"))):
            return {"user": user}

        self._client = TestClient(test_app)

    def test_protected_no_token(self):
        response = self._client.get("/_test/protected")
        assert response.status_code == 401

    def test_protected_invalid_token(self):
        response = self._client.get(
            "/_test/protected",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_protected_valid_token(self):
        token = create_access_token({"sub": "admin", "role": "admin", "department_id": 1})
        response = self._client.get(
            "/_test/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["sub"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_admin_role_allowed(self):
        token = create_access_token({"sub": "admin", "role": "admin", "department_id": 1})
        response = self._client.get(
            "/_test/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_admin_role_forbidden(self):
        token = create_access_token({"sub": "staff", "role": "staff", "department_id": 2})
        response = self._client.get(
            "/_test/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"
