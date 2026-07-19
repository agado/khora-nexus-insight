from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.database import get_session
from src.core.models import Document
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


def _staff_token() -> str:
    return create_access_token(
        {
            "sub": "staff",
            "role": "staff",
            "department_id": 2,
            "accessible_departments": [2],
            "user_id": 3,
        }
    )


def _lead_token() -> str:
    return create_access_token(
        {
            "sub": "lead",
            "role": "lead",
            "department_id": 1,
            "accessible_departments": [1],
            "user_id": 2,
        }
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)


def _fake_pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content for testing"


class TestUpload:
    def test_upload_success(self, client):
        token = _admin_token()
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with patch("src.api.v1.documents.upload_document", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = mock_doc
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", _fake_pdf_bytes(), "application/pdf")},
                data={"department_id": 1},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["filename"] == "test.pdf"

    def test_upload_without_auth_returns_401(self, client):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", _fake_pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 401

    def test_upload_duplicate_returns_409(self, client):
        from src.core.services.document_service import DuplicateDocumentError

        token = _admin_token()
        with patch("src.api.v1.documents.upload_document", new_callable=AsyncMock) as mock_upload:
            mock_upload.side_effect = DuplicateDocumentError("abc123")
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("dup.pdf", _fake_pdf_bytes(), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 409

    def test_upload_file_too_large_returns_413(self, client):
        token = _admin_token()
        oversized = b"%PDF" + b"A" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("big.pdf", oversized, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 413

    def test_upload_invalid_file_type_returns_400(self, client):
        token = _admin_token()
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("not_a_pdf.txt", b"plain text", "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    def test_upload_missing_file_returns_422(self, client):
        token = _admin_token()
        response = client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_upload_department_access_denied(self, client):
        token = _staff_token()
        with patch("src.api.v1.documents.upload_document", new_callable=AsyncMock) as mock_upload:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", _fake_pdf_bytes(), "application/pdf")},
                data={"department_id": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403
        mock_upload.assert_not_called()


class TestGetDocument:
    def test_get_document_success(self, client):
        token = _admin_token()
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with patch("src.api.v1.documents.get_document_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_doc
            response = client.get(
                "/api/v1/documents/1",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_get_document_not_found(self, client):
        token = _admin_token()
        with patch("src.api.v1.documents.get_document_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            response = client.get(
                "/api/v1/documents/999",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 404


class TestListDocuments:
    def test_list_documents_success(self, client):
        token = _admin_token()
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with patch(
            "src.api.v1.documents.get_documents_by_departments", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [mock_doc]
            response = client.get(
                "/api/v1/documents",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 1
        assert data["total"] == 1


class TestDeleteDocument:
    def test_delete_success(self, client):
        token = _admin_token()
        with (
            patch("src.api.v1.documents.delete_document", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock),
        ):
            mock_delete.return_value = True
            response = client.delete(
                "/api/v1/documents/1",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json()["detail"] == "Document deleted"

    def test_delete_forbidden_staff(self, client):
        token = _staff_token()
        response = client.delete(
            "/api/v1/documents/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_delete_not_found(self, client):
        token = _admin_token()
        with (
            patch("src.api.v1.documents.delete_document", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock),
        ):
            mock_delete.return_value = False
            response = client.delete(
                "/api/v1/documents/999",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 404

    def test_delete_audit_log(self, client):
        token = _admin_token()
        with (
            patch("src.api.v1.documents.delete_document", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock) as mock_log,
        ):
            mock_delete.return_value = True
            client.delete(
                "/api/v1/documents/1",
                headers={"Authorization": f"Bearer {token}"},
            )
        mock_log.assert_awaited_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["action"] == "delete"
        assert call_kwargs["user_id"] == 1

    def test_lead_can_delete(self, client):
        token = _lead_token()
        with (
            patch("src.api.v1.documents.delete_document", new_callable=AsyncMock) as mock_delete,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock),
        ):
            mock_delete.return_value = True
            response = client.delete(
                "/api/v1/documents/1",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200


class TestDocumentVisibility:
    def test_toggle_visibility(self, client):
        token = _admin_token()
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 1
        mock_doc.is_public = False
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with (
            patch(
                "src.api.v1.documents.toggle_document_visibility", new_callable=AsyncMock
            ) as mock_toggle,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock),
        ):
            mock_toggle.return_value = mock_doc
            mock_doc.is_public = True
            response = client.patch(
                "/api/v1/documents/1/toggle-public",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json()["is_public"] is True

    def test_toggle_not_found(self, client):
        token = _admin_token()
        with (
            patch(
                "src.api.v1.documents.toggle_document_visibility", new_callable=AsyncMock
            ) as mock_toggle,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock),
        ):
            mock_toggle.return_value = None
            response = client.patch(
                "/api/v1/documents/999/toggle-public",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 404

    def test_toggle_staff_can_toggle(self, client):
        token = _staff_token()
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with (
            patch(
                "src.api.v1.documents.toggle_document_visibility", new_callable=AsyncMock
            ) as mock_toggle,
            patch("src.api.v1.documents.log_action", new_callable=AsyncMock),
        ):
            mock_toggle.return_value = mock_doc
            mock_doc.is_public = True
            response = client.patch(
                "/api/v1/documents/1/toggle-public",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json()["is_public"] is True

    def test_upload_with_is_public(self, client):
        token = _admin_token()
        mock_doc = MagicMock(spec=Document)
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.sha256 = "abc"
        mock_doc.department_id = 1
        mock_doc.uploaded_by = 1
        mock_doc.is_public = True
        mock_doc.created_at.isoformat.return_value = "2026-01-01T00:00:00"

        with patch("src.api.v1.documents.upload_document", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = mock_doc
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", _fake_pdf_bytes(), "application/pdf")},
                data={"department_id": 1, "is_public": "true"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["is_public"] is True
        _, kwargs = mock_upload.call_args
        assert kwargs["is_public"] is True
