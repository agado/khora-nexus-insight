import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.auth.rbac import get_current_user_from_cookie, require_min_level
from src.core.config import settings


def _app_with_deps():
    app = FastAPI()

    @app.get("/level2")
    async def level2(user: dict = Depends(require_min_level(2))):
        return {"user": user}

    @app.get("/level3")
    async def level3(user: dict = Depends(require_min_level(3))):
        return {"user": user}

    return app


class TestRequireMinLevel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.client = TestClient(_app_with_deps())

    def test_admin_level2_allowed(self):
        token = create_access_token({"sub": "admin", "role": "admin", "department_id": 1})
        response = self.client.get("/level2", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_admin_level3_allowed(self):
        token = create_access_token({"sub": "admin", "role": "admin", "department_id": 1})
        response = self.client.get("/level3", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_lead_level2_allowed(self):
        token = create_access_token({"sub": "lead_it", "role": "lead", "department_id": 1})
        response = self.client.get("/level2", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_lead_level3_denied(self):
        token = create_access_token({"sub": "lead_it", "role": "lead", "department_id": 1})
        response = self.client.get("/level3", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_staff_level2_denied(self):
        token = create_access_token({"sub": "staff", "role": "staff", "department_id": 2})
        response = self.client.get("/level2", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_staff_level3_denied(self):
        token = create_access_token({"sub": "staff", "role": "staff", "department_id": 2})
        response = self.client.get("/level3", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_missing_token_returns_401(self):
        response = self.client.get("/level2")
        assert response.status_code == 401


class TestGetCurrentUserFromCookie:
    @pytest.fixture(autouse=True)
    def _setup(self):
        app = FastAPI()

        @app.get("/me")
        async def me(user: dict = Depends(get_current_user_from_cookie)):
            return {"user": user}

        self.client = TestClient(app)

    def test_valid_cookie_returns_user(self):
        token = create_access_token({"sub": "admin", "role": "admin", "department_id": 1})
        self.client.cookies.set("access_token", token)
        response = self.client.get("/me")
        assert response.status_code == 200
        assert response.json()["user"]["sub"] == "admin"

    def test_missing_cookie_returns_401(self):
        response = self.client.get("/me")
        assert response.status_code == 401

    def test_invalid_cookie_returns_401(self):
        self.client.cookies.set("access_token", "invalid.token.here")
        response = self.client.get("/me")
        assert response.status_code == 401

    def test_expired_cookie_returns_401(self):
        payload = {
            "sub": "admin",
            "role": "admin",
            "department_id": 1,
            "exp": int(time.time()) - 10,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        self.client.cookies.set("access_token", token)
        response = self.client.get("/me")
        assert response.status_code == 401
