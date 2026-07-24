import hashlib
import logging
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models import Document

logger = logging.getLogger("nexus")


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
    is_public: bool = False,
) -> Document:
    sha256 = _compute_sha256(content)
    existing = await db.execute(select(Document).where(Document.sha256 == sha256))
    if existing.scalar_one_or_none() is not None:
        logger.warning(
            "Duplicate upload attempt: sha256=%s filename=%s user_id=%s", sha256, filename, user_id
        )
        raise DuplicateDocumentError(sha256)

    content_text = _extract_text(content)
    document = Document(
        filename=filename,
        sha256=sha256,
        content_text=content_text,
        department_id=department_id,
        uploaded_by=user_id,
        is_public=is_public,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)
    logger.info(
        "Document uploaded: id=%s filename=%s sha256=%s dept=%s user=%s",
        document.id,
        filename,
        sha256,
        department_id,
        user_id,
    )
    return document


async def get_document_by_id(
    db: AsyncSession,
    document_id: int,
    department_ids: list[int],
) -> Document | None:
    result = await db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            or_(
                Document.department_id.in_(department_ids),
                Document.is_public,
            ),
        )
        .options(selectinload(Document.uploader))
    )
    return result.scalar_one_or_none()


async def delete_document(
    db: AsyncSession,
    document_id: int,
    department_ids: list[int],
    user_id: int | None = None,
) -> bool:
    doc = await get_document_by_id(db, document_id, department_ids)
    if doc is None:
        logger.warning(
            "Delete failed: document not found id=%s dept_ids=%s", document_id, department_ids
        )
        return False
    await db.delete(doc)
    await db.flush()
    logger.info("Document deleted: id=%s filename=%s user=%s", document_id, doc.filename, user_id)
    return True


async def get_documents_by_departments(
    db: AsyncSession,
    department_ids: list[int],
    skip: int = 0,
    limit: int = 50,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(
            or_(
                Document.department_id.in_(department_ids),
                Document.is_public,
            )
        )
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def toggle_document_visibility(
    db: AsyncSession,
    document_id: int,
    department_ids: list[int],
    user_id: int | None = None,
) -> Document | None:
    result = await db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.department_id.in_(department_ids),
        )
        .options(selectinload(Document.uploader))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        logger.warning("Toggle visibility failed: document not found id=%s", document_id)
        return None
    doc.is_public = not doc.is_public
    await db.flush()
    await db.refresh(doc)
    logger.info(
        "Document visibility toggled: id=%s is_public=%s user=%s",
        document_id,
        doc.is_public,
        user_id,
    )
    return doc
