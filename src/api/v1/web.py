import logging

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import require_web_user
from src.core.database import get_session
from src.core.services.auth_service import authenticate_user
from src.core.services.document_service import (
    DuplicateDocumentError,
    get_documents_by_departments,
    upload_document,
)
from src.core.services.rag_service import RagConnectionError, RagQueryError, execute_query
from src.main import templates

_QUERY_RESULT_TPL = Template(
    "<article>"
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
    token = await authenticate_user(db, username, password)
    if not token:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Credenciales inválidas"},
        )
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
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
        )
    except DuplicateDocumentError:
        return templates.TemplateResponse(
            request,
            "_upload_form.html",
            {"error": "Documento duplicado"},
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
    return templates.TemplateResponse(
        request,
        "_document_list.html",
        {"documents": docs},
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
    from src.core.config import settings as app_settings

    if len(query) > 2000:
        return HTMLResponse(
            _QUERY_RESULT_TPL.render(
                answer="La consulta excede el máximo de 2000 caracteres.",
                context_used=[],
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
        )
    except (RagConnectionError, RagQueryError) as exc:
        logger.warning("RAG web error: %s", exc)
        return HTMLResponse(
            _QUERY_RESULT_TPL.render(answer=str(exc), context_used=[]),
            status_code=500,
        )
    return HTMLResponse(
        _QUERY_RESULT_TPL.render(
            answer=result["answer"],
            context_used=result["context_used"],
        ),
    )
