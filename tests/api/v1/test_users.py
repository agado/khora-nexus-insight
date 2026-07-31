from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.__aenter__ = MagicMock(return_value=mock_session)
    mock_session.__aexit__ = MagicMock()

    async def _override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = _override_get_session
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
        with patch("src.api.v1.api_users.list_users", new_callable=AsyncMock) as mock_list:
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
            patch("src.api.v1.web_users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.web_users.get_departments", new_callable=AsyncMock) as mock_depts,
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
            patch("src.api.v1.api_users.create_user", new_callable=AsyncMock) as mock_create,
            patch("src.api.v1.api_users.log_action", new_callable=AsyncMock),
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
        with patch("src.api.v1.api_users.create_user", new_callable=AsyncMock) as mock_create:
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

    def test_api_empty_accessible_departments_returns_409(self, client):
        with patch("src.api.v1.api_users.create_user", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValueError(
                "Debe seleccionar al menos un departamento accesible"
            )
            response = client.post(
                self.API,
                json={
                    "username": "newuser",
                    "password": "pass123",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 409

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
            patch("src.api.v1.web_users.create_user", new_callable=AsyncMock) as mock_create,
            patch("src.api.v1.web_users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.web_users.log_action", new_callable=AsyncMock),
        ):
            mock_create.return_value = mock_user
            mock_list.return_value = []
            response = auth_client.post(
                self.WEB,
                data={
                    "username": "newuser",
                    "password": "Pass123!",
                    "password_confirm": "Pass123!",
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
            patch("src.api.v1.api_users.delete_user", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.api_users.log_action", new_callable=AsyncMock),
        ):
            mock_delete.return_value = True
            response = client.delete(
                self.API, headers={"Authorization": f"Bearer {_admin_token()}"}
            )
        assert response.status_code == 204

    def test_api_delete_not_found(self, client):
        with patch("src.api.v1.api_users.delete_user", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = False
            response = client.delete(
                self.API, headers={"Authorization": f"Bearer {_admin_token()}"}
            )
        assert response.status_code == 404

    def test_api_cannot_delete_self(self, client):
        with patch("src.api.v1.api_users.delete_user", new_callable=AsyncMock) as mock_delete:
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
            patch("src.api.v1.web_users.delete_user", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.web_users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.web_users.log_action", new_callable=AsyncMock),
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
            patch("src.api.v1.api_users.reset_password", new_callable=AsyncMock) as mock_reset,
            patch("src.api.v1.api_users.log_action", new_callable=AsyncMock),
        ):
            mock_reset.return_value = True
            response = client.post(
                self.API,
                json={"new_password": "newpass123"},
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 200

    def test_api_reset_not_found(self, client):
        with patch("src.api.v1.api_users.reset_password", new_callable=AsyncMock) as mock_reset:
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
            patch("src.api.v1.web_users.reset_password", new_callable=AsyncMock) as mock_reset,
            patch("src.api.v1.web_users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.web_users.log_action", new_callable=AsyncMock),
        ):
            mock_reset.return_value = True
            mock_list.return_value = []
            response = auth_client.post(
                self.WEB, data={"new_password": "newpass123", "password_confirm": "newpass123"}
            )
        assert response.status_code == 200

    def test_web_reset_password_mismatch_shows_error(self, auth_client):
        with (
            patch("src.api.v1.web_users.get_user_by_id", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = MagicMock(id=2, username="testuser")
            response = auth_client.post(
                self.WEB,
                data={"new_password": "newpass123", "password_confirm": "different"},
            )
        assert response.status_code == 200
        assert "Las contraseñas no coinciden." in response.text


class TestUpdateUser:
    API = "/api/v1/admin/users/2"
    WEB_GET = "/web/users/2/edit"
    WEB_POST = "/web/users/2/edit"

    def test_api_requires_admin(self, client):
        response = client.put(
            self.API,
            json={
                "username": "hacker",
                "role": "staff",
                "department_id": 1,
                "accessible_department_ids": [1],
            },
            headers={"Authorization": f"Bearer {_staff_token()}"},
        )
        assert response.status_code == 403

    def test_api_updates_user_role_and_department(self, client):
        mock_user = MagicMock(spec=User)
        mock_user.id = 2
        mock_user.username = "ceo"
        mock_user.role = "staff"
        mock_user.department_id = 2
        mock_user.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with (
            patch("src.api.v1.api_users.update_user", new_callable=AsyncMock) as mock_update,
            patch("src.api.v1.api_users.log_action", new_callable=AsyncMock),
        ):
            mock_update.return_value = mock_user
            response = client.put(
                self.API,
                json={
                    "username": "ceo",
                    "role": "staff",
                    "department_id": 2,
                    "accessible_department_ids": [2],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "ceo"
        assert data["role"] == "staff"

    def test_api_update_not_found(self, client):
        with (
            patch("src.api.v1.api_users.update_user", new_callable=AsyncMock) as mock_update,
        ):
            mock_update.side_effect = ValueError("User not found")
            response = client.put(
                "/api/v1/admin/users/999",
                json={
                    "username": "ghost",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [1],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 404

    def test_api_update_invalid_role(self, client):
        response = client.put(
            self.API,
            json={
                "username": "ceo",
                "role": "superadmin",
                "department_id": 1,
                "accessible_department_ids": [1],
            },
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert response.status_code == 422

    def test_api_update_duplicate_username(self, client):
        with (
            patch("src.api.v1.api_users.update_user", new_callable=AsyncMock) as mock_update,
        ):
            mock_update.side_effect = ValueError("Username already exists")
            response = client.put(
                self.API,
                json={
                    "username": "admin",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [1],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 409

    def test_api_update_empty_accessible_returns_409(self, client):
        with (
            patch("src.api.v1.api_users.update_user", new_callable=AsyncMock) as mock_update,
        ):
            mock_update.side_effect = ValueError(
                "Debe seleccionar al menos un departamento accesible"
            )
            response = client.put(
                self.API,
                json={
                    "username": "ceo",
                    "role": "staff",
                    "department_id": 1,
                    "accessible_department_ids": [],
                },
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert response.status_code == 409

    def test_web_edit_form_requires_admin(self, staff_client):
        response = staff_client.get(self.WEB_GET)
        assert response.status_code == 403

    def test_web_edit_form_renders(self, auth_client):
        mock_user = MagicMock(spec=User)
        mock_user.id = 2
        mock_user.username = "ceo"
        mock_user.role = "admin"
        mock_user.department_id = 1

        with (
            patch("src.api.v1.web_users.get_user_by_id", new_callable=AsyncMock) as mock_get,
            patch("src.api.v1.web_users.get_departments", new_callable=AsyncMock) as mock_depts,
        ):
            mock_get.return_value = mock_user
            mock_depts.return_value = [{"id": 1, "name": "IT"}]
            response = auth_client.get(self.WEB_GET)
        assert response.status_code == 200
        assert "ceo" in response.text

    def test_web_edit_form_user_not_found(self, auth_client):
        with (
            patch("src.api.v1.web_users.get_user_by_id", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = None
            response = auth_client.get("/web/users/999/edit")
        assert response.status_code == 404

    def test_web_edit_submit_requires_admin(self, staff_client):
        response = staff_client.post(
            self.WEB_POST,
            data={
                "username": "ceo",
                "role": "staff",
                "department_id": 2,
                "accessible_department_ids": [2],
            },
        )
        assert response.status_code == 403

    def test_web_edit_submit_success(self, auth_client):
        mock_user = MagicMock(spec=User)
        mock_user.id = 2
        mock_user.username = "ceo"
        mock_user.role = "staff"

        with (
            patch("src.api.v1.web_users.update_user", new_callable=AsyncMock) as mock_update,
            patch("src.api.v1.web_users.list_users", new_callable=AsyncMock) as mock_list,
            patch("src.api.v1.web_users.log_action", new_callable=AsyncMock),
        ):
            mock_update.return_value = mock_user
            mock_list.return_value = [{"id": 2, "username": "ceo", "role": "staff"}]
            response = auth_client.post(
                self.WEB_POST,
                data={
                    "username": "ceo",
                    "role": "staff",
                    "department_id": 2,
                    "accessible_department_ids": [2],
                },
            )
        assert response.status_code == 200
        assert "correctamente" in response.text

    def test_web_edit_submit_invalid_role(self, auth_client):
        with (
            patch("src.api.v1.web_users.update_user", new_callable=AsyncMock) as mock_update,
            patch("src.api.v1.web_users.get_user_by_id", new_callable=AsyncMock) as mock_get,
            patch("src.api.v1.web_users.get_departments", new_callable=AsyncMock) as mock_depts,
        ):
            mock_update.side_effect = ValueError("Invalid role")
            mock_get.return_value = MagicMock(id=2, username="ceo", role="staff")
            mock_depts.return_value = [{"id": 1, "name": "IT"}]
            response = auth_client.post(
                self.WEB_POST,
                data={
                    "username": "ceo",
                    "role": "superadmin",
                    "department_id": 1,
                    "accessible_department_ids": [1],
                },
            )
        assert response.status_code == 200
        assert "error" in response.text or "Invalid" in response.text
