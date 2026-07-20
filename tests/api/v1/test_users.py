from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.database import get_session
from src.core.models import User
from src.main import app


def _admin_token() -> str:
    return create_access_token(
        {
            "sub": "admin",
            "role": "admin",
            "role_level": 3,
            "department_id": 1,
            "accessible_departments": [1, 2, 3],
            "user_id": 1,
        }
    )


def _staff_token() -> str:
    return create_access_token(
        {
            "sub": "staff",
            "role": "staff",
            "role_level": 1,
            "department_id": 2,
            "accessible_departments": [2],
            "user_id": 3,
        }
    )


@pytest.fixture
def client():
    mock_session = AsyncMock()
    mock_session.add.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def auth_client(client):
    client.cookies.set("access_token", _admin_token())
    return client


@pytest.fixture
def staff_client(client):
    client.cookies.set("access_token", _staff_token())
    return client


class TestListUsers:
    API = "/api/v1/admin/users"
    WEB = "/web/users"

    def test_api_requires_admin(self, client):
        response = client.get(self.API, headers={"Authorization": f"Bearer {_staff_token()}"})
        assert response.status_code == 403

    def test_api_lists_users(self, client):
        with patch("src.api.v1.users.list_users", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {
                    "id": 1,
                    "username": "admin",
                    "role": "admin",
                    "department_name": "IT",
                    "created_at": "2026-01-01T00:00:00",
                },
            ]
            response = client.get(self.API, headers={"Authorization": f"Bearer {_admin_token()}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "admin"

    def test_web_requires_admin(self, staff_client):
        response = staff_client.get(self.WEB)
        assert response.status_code == 403

    def test_web_renders(self, auth_client):
        with (
            patch("src.api.v1.users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.users.get_departments", new_callable=AsyncMock) as mock_depts,
        ):
            mock_list.return_value = []
            mock_depts.return_value = []
            response = auth_client.get(self.WEB)
        assert response.status_code == 200
        assert "Usuarios" in response.text


class TestCreateUser:
    API = "/api/v1/admin/users"
    WEB = "/web/users"

    def test_api_requires_admin(self, client):
        response = client.post(
            self.API,
            json={
                "username": "newuser",
                "password": "pass123",
                "role": "staff",
                "department_id": 1,
                "accessible_department_ids": [1],
            },
            headers={"Authorization": f"Bearer {_staff_token()}"},
        )
        assert response.status_code == 403

    def test_api_creates_user(self, client):
        mock_user = MagicMock(spec=User)
        mock_user.id = 2
        mock_user.username = "newuser"
        mock_user.role = "staff"
        mock_user.department_id = 1

        with (
            patch("src.api.v1.users.create_user", new_callable=AsyncMock) as mock_create,
            patch("src.api.v1.users.log_action", new_callable=AsyncMock),
        ):
            mock_create.return_value = mock_user
            response = client.post(
                self.API,
                json={
                    "username": "newuser",
                    "password": "pass123",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [1],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"

    def test_api_duplicate_returns_409(self, client):
        with patch("src.api.v1.users.create_user", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValueError("Username already exists")
            response = client.post(
                self.API,
                json={
                    "username": "admin",
                    "password": "pass123",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [1],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 409

    def test_api_invalid_role_returns_422(self, client):
        response = client.post(
            self.API,
            json={
                "username": "newuser",
                "password": "pass123",
                "role": "superadmin",
                "department_id": 1,
                "accessible_department_ids": [1],
            },
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert response.status_code == 422

    def test_web_requires_admin(self, staff_client):
        response = staff_client.post(
            self.WEB,
            data={
                "username": "newuser",
                "password": "pass123",
                "role": "staff",
                "department_id": 1,
                "accessible_department_ids": [1],
            },
        )
        assert response.status_code == 403

    def test_web_creates_user(self, auth_client):
        mock_user = MagicMock(spec=User)
        mock_user.id = 2
        mock_user.username = "newuser"

        with (
            patch("src.api.v1.users.create_user", new_callable=AsyncMock) as mock_create,
            patch("src.api.v1.users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.users.log_action", new_callable=AsyncMock),
        ):
            mock_create.return_value = mock_user
            mock_list.return_value = []
            response = auth_client.post(
                self.WEB,
                data={
                    "username": "newuser",
                    "password": "pass123",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [1],
                },
            )
        assert response.status_code == 200


class TestDeleteUser:
    API = "/api/v1/admin/users/2"
    WEB = "/web/users/2/delete"

    def test_api_requires_admin(self, client):
        response = client.delete(self.API, headers={"Authorization": f"Bearer {_staff_token()}"})
        assert response.status_code == 403

    def test_api_deletes_user(self, client):
        with (
            patch("src.api.v1.users.delete_user", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.users.log_action", new_callable=AsyncMock),
        ):
            mock_delete.return_value = True
            response = client.delete(
                self.API, headers={"Authorization": f"Bearer {_admin_token()}"}
            )
        assert response.status_code == 204

    def test_api_delete_not_found(self, client):
        with patch("src.api.v1.users.delete_user", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = False
            response = client.delete(
                self.API, headers={"Authorization": f"Bearer {_admin_token()}"}
            )
        assert response.status_code == 404

    def test_api_cannot_delete_self(self, client):
        with patch("src.api.v1.users.delete_user", new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = ValueError("Cannot delete yourself")
            response = client.delete(
                "/api/v1/admin/users/1",
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 409

    def test_web_requires_admin(self, staff_client):
        response = staff_client.post(self.WEB)
        assert response.status_code == 403

    def test_web_deletes_user(self, auth_client):
        with (
            patch("src.api.v1.users.delete_user", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.users.log_action", new_callable=AsyncMock),
        ):
            mock_delete.return_value = True
            mock_list.return_value = []
            response = auth_client.post(self.WEB)
        assert response.status_code == 200


class TestResetPassword:
    API = "/api/v1/admin/users/2/reset-password"
    WEB = "/web/users/2/reset-password"

    def test_api_requires_admin(self, client):
        response = client.post(
            self.API,
            json={"new_password": "newpass123"},
            headers={"Authorization": f"Bearer {_staff_token()}"},
        )
        assert response.status_code == 403

    def test_api_resets_password(self, client):
        with (
            patch("src.api.v1.users.reset_password", new_callable=AsyncMock) as mock_reset,
            patch("src.api.v1.users.log_action", new_callable=AsyncMock),
        ):
            mock_reset.return_value = True
            response = client.post(
                self.API,
                json={"new_password": "newpass123"},
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 200

    def test_api_reset_not_found(self, client):
        with patch("src.api.v1.users.reset_password", new_callable=AsyncMock) as mock_reset:
            mock_reset.return_value = False
            response = client.post(
                self.API,
                json={"new_password": "newpass123"},
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 404

    def test_web_requires_admin(self, staff_client):
        response = staff_client.post(self.WEB, data={"new_password": "newpass123"})
        assert response.status_code == 403

    def test_web_resets_password(self, auth_client):
        with (
            patch("src.api.v1.users.reset_password", new_callable=AsyncMock) as mock_reset,
            patch("src.api.v1.users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.users.log_action", new_callable=AsyncMock),
        ):
            mock_reset.return_value = True
            mock_list.return_value = []
            response = auth_client.post(self.WEB, data={"new_password": "newpass123"})
        assert response.status_code == 200
