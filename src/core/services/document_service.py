import hashlib
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models import Document


class DuplicateDocumentError(Exception):
    def __init__(self, sha256: str) -> None:
        self.sha256 = sha256
        super().__init__(f"Document with SHA-256 {sha256} already exists")


def _compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _extract_text(content: bytes) -> str | None:
    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfReadError:
        try:
            return content.decode("utf-8")
        except (UnicodeDecodeError, UnicodeError):
            return None


async def upload_document(
    db: AsyncSession,
    filename: str,
    content: bytes,
    department_id: int,
    user_id: int,
) -> Document:
    sha256 = _compute_sha256(content)
    existing = await db.execute(select(Document).where(Document.sha256 == sha256))
    if existing.scalar_one_or_none() is not None:
        raise DuplicateDocumentError(sha256)

    content_text = _extract_text(content)
    document = Document(
        filename=filename,
        sha256=sha256,
        content_text=content_text,
        department_id=department_id,
        uploaded_by=user_id,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


async def get_document_by_id(
    db: AsyncSession,
    document_id: int,
    department_ids: list[int],
) -> Document | None:
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.department_id.in_(department_ids))
        .options(selectinload(Document.uploader))
    )
    return result.scalar_one_or_none()


async def get_documents_by_departments(
    db: AsyncSession,
    department_ids: list[int],
    skip: int = 0,
    limit: int = 50,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.department_id.in_(department_ids))
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
