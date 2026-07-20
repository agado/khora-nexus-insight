from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.database import get_session
from src.core.services.rag_service import RagConnectionError, RagQueryError
from src.main import app


def _admin_token() -> str:
    return create_access_token(
        {
            "sub": "admin",
            "role": "admin",
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


class TestQuery:
    def test_query_success(self, client):
        mock_result = {
            "answer": "Medidas de seguridad recomendadas",
            "context_used": ["texto del documento"],
        }

        with patch(
            "src.api.v1.rag.execute_query",
            return_value=mock_result,
        ):
            resp = client.post(
                "/api/v1/rag/query",
                json={"query": "¿medidas de seguridad?", "document_ids": [1]},
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Medidas de seguridad recomendadas"
        assert len(data["context_used"]) == 1

    def test_query_missing_token_returns_401(self, client):
        resp = client.post(
            "/api/v1/rag/query",
            json={"query": "test", "document_ids": [1]},
        )
        assert resp.status_code == 401

    def test_query_empty_text_returns_422(self, client):
        resp = client.post(
            "/api/v1/rag/query",
            json={"query": "", "document_ids": [1]},
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )
        assert resp.status_code == 422

    def test_query_delegates_to_service_with_correct_args(self, client):
        token = _admin_token()

        with patch("src.api.v1.rag.execute_query") as mock_service:
            mock_service.return_value = {"answer": "ok", "context_used": []}
            client.post(
                "/api/v1/rag/query",
                json={"query": "mi pregunta", "document_ids": [1, 2]},
                headers={"Authorization": f"Bearer {token}"},
            )

        mock_service.assert_called_once()
        args = mock_service.call_args[1]
        assert args["query_text"] == "mi pregunta"
        assert args["document_ids"] == [1, 2]

    def test_query_ollama_down_returns_503(self, client):
        with patch("src.api.v1.rag.execute_query") as mock_service:
            mock_service.side_effect = RagConnectionError("Ollama no disponible")
            resp = client.post(
                "/api/v1/rag/query",
                json={"query": "test", "document_ids": [1]},
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert resp.status_code == 503
        assert "Ollama" in resp.json()["detail"]

    def test_query_ollama_error_returns_502(self, client):
        with patch("src.api.v1.rag.execute_query") as mock_service:
            mock_service.side_effect = RagQueryError("Error en la consulta")
            resp = client.post(
                "/api/v1/rag/query",
                json={"query": "test", "document_ids": [1]},
                headers={"Authorization": f"Bearer {_admin_token()}"},
            )
        assert resp.status_code == 502
        assert "Error" in resp.json()["detail"]
