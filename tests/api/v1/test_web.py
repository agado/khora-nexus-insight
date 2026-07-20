from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.database import get_session
from src.main import app


def _cookie_token(role_level: int = 3) -> str:
    return create_access_token(
        {
            "sub": "admin",
            "role": "admin",
            "role_level": role_level,
            "department_id": 1,
            "accessible_departments": [1, 2, 3],
            "user_id": 1,
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
    token = _cookie_token()
    client.cookies.set("access_token", token)
    return client


class TestLoginPage:
    def test_login_page_returns_form(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "<form" in response.text.lower()

    def test_login_success_sets_cookie_and_redirects(self, client):
        with (
            patch("src.api.v1.web.authenticate_user", new_callable=AsyncMock) as mock_auth,
            patch("src.api.v1.web.log_action", new_callable=AsyncMock),
        ):
            mock_auth.return_value = {"access_token": "valid.jwt.token", "user_id": 1}
            response = client.post(
                "/login",
                data={"username": "admin", "password": "admin123"},
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"
        assert "access_token" in response.cookies

    def test_login_failure_shows_error(self, client):
        with (
            patch("src.api.v1.web.authenticate_user", new_callable=AsyncMock) as mock_auth,
            patch("src.api.v1.web.log_action", new_callable=AsyncMock),
        ):
            mock_auth.return_value = None
            response = client.post(
                "/login",
                data={"username": "admin", "password": "wrong"},
            )
        assert response.status_code == 200
        assert "Credenciales inválidas" in response.text


class TestDashboard:
    def test_dashboard_without_cookie_redirects(self, client):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/login"

    def test_dashboard_with_cookie_returns_html(self, auth_client):
        response = auth_client.get("/dashboard")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "Nexus Insight" in response.text
        assert "Subir" in response.text
        assert "Documentos" in response.text

    def test_dashboard_staff_hides_upload_tab(self, client):
        token = _cookie_token(role_level=1)
        client.cookies.set("access_token", token)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Subir" not in response.text
        assert "Documentos" in response.text


class TestLogout:
    def test_logout_clears_cookie_and_redirects(self, auth_client):
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/login"
        assert "access_token" not in response.cookies or response.cookies["access_token"] == ""

    def test_logout_then_dashboard_redirects(self, auth_client):
        auth_client.get("/logout", follow_redirects=False)
        auth_client.cookies.clear()
        response = auth_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/login"


class TestUploadTab:
    def test_upload_tab_renders_form(self, auth_client):
        response = auth_client.get("/web/upload")
        assert response.status_code == 200
        assert 'type="file"' in response.text

    def test_web_upload_unauthorized(self, client):
        response = client.post(
            "/web/upload",
            files={"file": ("dummy.pdf", b"%PDF-1.4 test", "application/pdf")},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/login"

    def test_web_upload_success(self, auth_client):
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc123"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with (
            patch("src.api.v1.web.upload_document", new_callable=AsyncMock) as mock_up,
            patch("src.api.v1.web.log_action", new_callable=AsyncMock),
        ):
            mock_up.return_value = mock_doc
            response = auth_client.post(
                "/web/upload",
                files={"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
            )
        assert response.status_code == 200
        assert "test.pdf" in response.text


class TestDocumentListTab:
    def test_documents_tab_renders(self, auth_client):
        with patch(
            "src.api.v1.web.get_documents_by_departments", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []
            response = auth_client.get("/web/documents")
        assert response.status_code == 200
        assert "Documentos" in response.text

    def test_web_documents_list_empty(self, auth_client):
        with patch(
            "src.api.v1.web.get_documents_by_departments", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []
            response = auth_client.get("/web/documents")
        assert response.status_code == 200
        assert "No hay documentos disponibles" in response.text


class TestQueryTab:
    def test_query_form_renders(self, auth_client):
        with patch(
            "src.api.v1.web.get_documents_by_departments", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [MagicMock(id=1, filename="test.pdf")]
            response = auth_client.get("/web/query")
        assert response.status_code == 200
        assert "Consultar" in response.text
        assert "textarea" in response.text.lower()

    def test_query_form_empty_docs_shows_warning(self, auth_client):
        with patch(
            "src.api.v1.web.get_documents_by_departments", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []
            response = auth_client.get("/web/query")
        assert response.status_code == 200
        assert "No hay documentos disponibles" in response.text
        assert "textarea" not in response.text.lower()

    def test_query_submit_returns_answer(self, auth_client):
        with patch("src.api.v1.web.execute_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "answer": "Respuesta de prueba",
                "context_used": ["texto del doc"],
            }
            with patch(
                "src.api.v1.web.get_documents_by_departments", new_callable=AsyncMock
            ) as mock_list:
                mock_list.return_value = [MagicMock(id=1, filename="test.pdf")]
                response = auth_client.post(
                    "/web/query",
                    data={"query": "¿test?", "document_ids": ["1"]},
                )
        assert response.status_code == 200
        assert "Respuesta de prueba" in response.text
        assert "texto del doc" in response.text

    def test_query_unauthorized_redirects(self, client):
        response = client.get("/web/query", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    def test_htmx_unauthorized_returns_hx_redirect(self, client):
        response = client.get(
            "/web/query",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == "/login"
