import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import get_current_user, require_min_level
from src.core.database import get_session
from src.core.services.audit_service import log_action
from src.core.services.document_service import (
    DuplicateDocumentError,
    delete_document,
    get_document_by_id,
    get_documents_by_departments,
    toggle_document_visibility,
    upload_document,
)

logger = logging.getLogger("nexus")

router = APIRouter(prefix="/api/v1/documents")

MAX_FILE_SIZE = 10 * 1024 * 1024


class DocumentResponse(BaseModel):
    id: int
    filename: str
    sha256: str
    department_id: int
    uploaded_by: int
    created_at: str
    is_public: bool = False


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


def _to_doc_response(doc) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        sha256=doc.sha256,
        department_id=doc.department_id,
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at.isoformat(),
        is_public=doc.is_public,
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    department_id: int | None = Form(None),
    is_public: bool = Form(False),
    _user: dict = Depends(require_min_level(1)),
    db: AsyncSession = Depends(get_session),
):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are allowed.",
        )

    target_department = department_id or _user.get("department_id")
    accessible = _user.get("accessible_departments", [])
    if target_department not in accessible:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this department",
        )

    try:
        doc = await upload_document(
            db=db,
            filename=file.filename or "unnamed.pdf",
            content=content,
            department_id=target_department,
            user_id=_user["user_id"],
            is_public=is_public,
        )
    except DuplicateDocumentError:
        raise HTTPException(
            status_code=409,
            detail="A document with the same content already exists",
        ) from None

    logger.info(
        "Document uploaded: id=%d filename=%s dept=%d user=%d",
        doc.id,
        doc.filename,
        doc.department_id,
        doc.uploaded_by,
    )
    await log_action(
        db,
        action="upload",
        user_id=_user["user_id"],
        metadata={"filename": doc.filename, "sha256": doc.sha256, "document_id": doc.id},
    )
    return _to_doc_response(doc)


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    accessible = _user.get("accessible_departments", [])
    doc = await get_document_by_id(db, document_id, accessible)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_doc_response(doc)


@router.get("")
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    accessible = _user.get("accessible_departments", [])
    if not accessible:
        return DocumentListResponse(documents=[], total=0)
    docs = await get_documents_by_departments(db, accessible, skip=skip, limit=limit)
    return DocumentListResponse(
        documents=[_to_doc_response(d) for d in docs],
        total=len(docs),
    )


@router.delete("/{document_id}")
async def delete_document_endpoint(
    document_id: int,
    _user: dict = Depends(require_min_level(2)),
    db: AsyncSession = Depends(get_session),
):
    accessible = _user.get("accessible_departments", [])
    deleted = await delete_document(db, document_id, accessible)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    logger.info("Document deleted: id=%d user=%d", document_id, _user["user_id"])
    await log_action(
        db,
        action="delete",
        user_id=_user["user_id"],
        metadata={"document_id": document_id},
    )
    return {"detail": "Document deleted"}


@router.patch("/{document_id}/toggle-public")
async def toggle_public(
    document_id: int,
    _user: dict = Depends(require_min_level(1)),
    db: AsyncSession = Depends(get_session),
):
    accessible = _user.get("accessible_departments", [])
    doc = await toggle_document_visibility(db, document_id, accessible)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await log_action(
        db,
        action="toggle_public",
        user_id=_user["user_id"],
        metadata={"document_id": document_id, "is_public": doc.is_public},
    )
    return _to_doc_response(doc)
