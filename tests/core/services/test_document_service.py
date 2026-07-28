import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Document
from src.core.services.document_service import (
    DuplicateDocumentError,
    get_document_by_id,
    get_documents_by_departments,
    upload_document,
)


def _fake_pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake pdf content for testing"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestUploadDocument:
    @pytest.fixture
    def _mock_db(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_upload_new_pdf_extracts_text(self, _mock_db):
        content = _fake_pdf_bytes()

        with patch(
            "src.core.services.document_service._extract_text",
            return_value="extracted text",
        ):
            doc = await upload_document(_mock_db, "test.pdf", content, 1, 1)

        assert doc.sha256 == _sha256(content)
        assert doc.filename == "test.pdf"
        assert doc.content_text == "extracted text"
        assert doc.department_id == 1
        assert doc.uploaded_by == 1
        _mock_db.add.assert_called_once()
        _mock_db.flush.assert_awaited_once()
        _mock_db.refresh.assert_awaited_once_with(doc)

    @pytest.mark.asyncio
    async def test_upload_duplicate_raises_error(self):
        content = _fake_pdf_bytes()
        existing_doc = Document(
            id=1,
            filename="existing.pdf",
            sha256=_sha256(content),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()

        with pytest.raises(DuplicateDocumentError) as exc:
            await upload_document(mock_db, "dup.pdf", content, 1, 1)
        assert exc.value.sha256 == _sha256(content)
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_non_pdf_fallback_to_utf8(self, _mock_db):
        content = b"Hello, world! plain text"

        doc = await upload_document(_mock_db, "readme.txt", content, 2, 2)

        assert doc.sha256 == _sha256(content)
        assert doc.content_text == "Hello, world! plain text"
        _mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_binary_with_no_text_fallback(self, _mock_db):
        content = bytes(range(256))

        doc = await upload_document(_mock_db, "binary.bin", content, 1, 1)

        assert doc.sha256 == _sha256(content)
        assert doc.content_text is None


class TestGetDocumentById:
    @pytest.mark.asyncio
    async def test_finds_document_in_allowed_department(self):
        doc = Document(id=1, filename="test.pdf", department_id=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_document_by_id(mock_db, 1, [1, 2])

        assert result is doc

    @pytest.mark.asyncio
    async def test_returns_none_if_not_in_allowed_departments(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_document_by_id(mock_db, 1, [2, 3])

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_if_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_document_by_id(mock_db, 999, [1])

        assert result is None


class TestGetDocumentsByDepartments:
    @pytest.mark.asyncio
    async def test_returns_documents_for_allowed_departments(self):
        docs = [
            Document(id=1, filename="a.pdf", department_id=1),
            Document(id=2, filename="b.pdf", department_id=2),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_documents_by_departments(mock_db, [1, 2])

        assert result == docs

    @pytest.mark.asyncio
    async def test_empty_list_when_no_documents(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await get_documents_by_departments(mock_db, [3])

        assert result == []

    @pytest.mark.asyncio
    async def test_respects_skip_and_limit(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        await get_documents_by_departments(mock_db, [1], skip=10, limit=5)

        call_stmt = mock_db.execute.call_args[0][0]
        assert call_stmt._limit == 5
        assert call_stmt._offset == 10
