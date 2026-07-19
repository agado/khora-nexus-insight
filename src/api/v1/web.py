import logging

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import require_web_user
from src.core.database import get_session
from src.core.models import AuditLog, User
from src.core.services.audit_service import log_action
from src.core.services.auth_service import authenticate_user
from src.core.services.document_service import (
    DuplicateDocumentError,
    delete_document,
    get_documents_by_departments,
    toggle_document_visibility,
    upload_document,
)
from src.core.services.rag_service import (
    RagConnectionError,
    RagQueryError,
    execute_query,
)
from src.main import templates

_QUERY_RESULT_TPL = Template(
    "<article>"
    "{% if audience %}<small>Audiencia: <strong>{{ audience }}</strong></small><br>{% endif %}"
    "<strong>Respuesta:</strong>"
    "<p>{{ answer }}</p>"
    "{% if context_used %}"
    "<details>"
    "<summary>Contexto utilizado ({{ context_used|length }} documentos)</summary>"
    "{% for c in context_used %}"
    "<blockquote>{{ c[:300] }}</blockquote>"
    "{% endfor %}"
    "</details>"
    "{% endif %}"
    "</article>"
)

logger = logging.getLogger("nexus")
router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_session),
):
    result = await authenticate_user(db, username, password)
    if not result:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Credenciales inválidas"},
        )
    await log_action(db, action="login", user_id=result["user_id"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        samesite="lax",
        max_age=1800,
        path="/",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token", path="/")
    return response


@router.get("/dashboard")
async def dashboard(request: Request, _user=Depends(require_web_user)):
    if isinstance(_user, Response):
        return _user
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"username": _user.get("sub", "")},
    )


@router.get("/web/upload")
async def upload_form(request: Request, _user=Depends(require_web_user)):
    if isinstance(_user, Response):
        return _user
    return templates.TemplateResponse(request, "_upload_form.html")


@router.post("/web/upload")
async def web_upload(
    request: Request,
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    content = await file.read()
    target_department = _user.get("department_id")
    accessible = _user.get("accessible_departments", [])
    if target_department not in accessible:
        return templates.TemplateResponse(
            request,
            "_upload_form.html",
            {"error": "Departamento no accesible"},
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
        return templates.TemplateResponse(
            request,
            "_upload_form.html",
            {"error": "Documento duplicado"},
        )

    await log_action(
        db,
        action="upload",
        user_id=_user["user_id"],
        metadata={"filename": doc.filename, "sha256": doc.sha256, "document_id": doc.id},
    )

    return templates.TemplateResponse(
        request,
        "_upload_form.html",
        {"success": f"Subido: {doc.filename} (SHA-256: {doc.sha256[:16]}...)"},
    )


@router.get("/web/documents")
async def web_documents(
    request: Request,
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    accessible = _user.get("accessible_departments", [])
    docs = await get_documents_by_departments(db, accessible)
    role_level = _user.get("role_level", 0)
    return templates.TemplateResponse(
        request,
        "_document_list.html",
        {"documents": docs, "role_level": role_level},
    )


@router.post("/web/documents/{document_id}/delete")
async def web_delete_document(
    document_id: int,
    request: Request,
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    role_level = _user.get("role_level", 0)
    if role_level < 2:
        return HTMLResponse(status_code=403, content="Forbidden")
    accessible = _user.get("accessible_departments", [])
    deleted = await delete_document(db, document_id, accessible)
    if not deleted:
        return HTMLResponse(status_code=404, content="Not found")
    await log_action(
        db,
        action="delete",
        user_id=_user["user_id"],
        metadata={"document_id": document_id},
    )
    return HTMLResponse(
        status_code=200,
        content='<tr><td colspan="7">Documento eliminado</td></tr>',
    )


@router.post("/web/documents/{document_id}/toggle-public")
async def web_toggle_public(
    document_id: int,
    request: Request,
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    accessible = _user.get("accessible_departments", [])
    doc = await toggle_document_visibility(db, document_id, accessible)
    if doc is None:
        return HTMLResponse(status_code=404, content="Not found")
    await log_action(
        db,
        action="toggle_public",
        user_id=_user["user_id"],
        metadata={"document_id": document_id, "is_public": doc.is_public},
    )
    return templates.TemplateResponse(
        request,
        "_document_row.html",
        {"doc": doc, "role_level": _user.get("role_level", 0)},
    )


@router.get("/web/query")
async def query_form(
    request: Request,
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    accessible = _user.get("accessible_departments", [])
    docs = await get_documents_by_departments(db, accessible)
    return templates.TemplateResponse(
        request,
        "_query_form.html",
        {"documents": docs},
    )


@router.post("/web/query")
async def web_query(
    request: Request,
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    form = await request.form()
    query = form.get("query", "")
    raw_ids = form.getlist("document_ids")
    ids = [int(x) for x in raw_ids if x.strip()]
    audience = form.get("audience", "general")
    from src.core.config import settings as app_settings

    if len(query) > 2000:
        return HTMLResponse(
            _QUERY_RESULT_TPL.render(
                answer="La consulta excede el máximo de 2000 caracteres.",
                context_used=[],
                audience=None,
            ),
            status_code=400,
        )

    try:
        result = await execute_query(
            db=db,
            query_text=query,
            document_ids=ids,
            user=_user,
            ollama_host=app_settings.ollama_host,
            model_name=app_settings.model_name,
            audience=audience,
        )
    except (RagConnectionError, RagQueryError) as exc:
        logger.warning("RAG web error: %s", exc)
        return HTMLResponse(
            _QUERY_RESULT_TPL.render(answer=str(exc), context_used=[], audience=None),
            status_code=500,
        )
    return HTMLResponse(
        _QUERY_RESULT_TPL.render(
            answer=result["answer"],
            context_used=result["context_used"],
            audience=audience,
        ),
    )


@router.get("/web/logs")
async def web_logs(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    _user=Depends(require_web_user),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    stmt = (
        select(AuditLog, User.username)
        .join(User, AuditLog.user_id == User.id)
        .order_by(desc(AuditLog.timestamp))
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    logs = [
        {
            "id": row.AuditLog.id,
            "action": row.AuditLog.action,
            "username": row.username,
            "timestamp": row.AuditLog.timestamp.isoformat(),
            "metadata": row.AuditLog.metadata_,
        }
        for row in rows
    ]
    return templates.TemplateResponse(request, "_logs_table.html", {"logs": logs})
