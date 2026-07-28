import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import require_web_min_level
from src.core.database import get_session
from src.core.models import User
from src.core.services.audit_service import log_action
from src.core.services.user_service import (
    create_user,
    delete_user,
    get_departments,
    get_user_by_id,
    list_users,
    reset_password,
    update_user,
)
from src.main import templates

logger = logging.getLogger("nexus")
router = APIRouter(prefix="/web", tags=["admin-web"])


@router.get("/users")
async def web_list_users(
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    users = await list_users(db)
    return templates.TemplateResponse(
        request,
        "_user_list.html",
        {"users": users, "session_user": _user},
    )


@router.get("/users/new")
async def web_new_user_form(
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    depts = await get_departments(db)
    return templates.TemplateResponse(
        request,
        "_user_form.html",
        {"departments": depts, "session_user": _user},
    )


@router.post("/users")
async def web_create_user(
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    form = await request.form()

    def _form_data() -> dict:
        return {
            "username": form.get("username", ""),
            "role": form.get("role", ""),
            "department_id": form.get("department_id", ""),
            "accessible_department_ids": [
                int(x) for x in form.getlist("accessible_department_ids") if x.strip()
            ],
        }

    if form["password"] != form.get("password_confirm", ""):
        depts = await get_departments(db)
        return templates.TemplateResponse(
            request,
            "_user_form.html",
            {
                "departments": depts,
                "error": "Las contraseñas no coinciden.",
                "session_user": _user,
                "form_data": _form_data(),
            },
        )
    data = _form_data()
    ids = data["accessible_department_ids"]
    try:
        user = await create_user(
            db=db,
            username=form["username"],
            password=form["password"],
            role=form["role"],
            department_id=int(form["department_id"]),
            accessible_department_ids=ids,
        )
    except ValueError as exc:
        depts = await get_departments(db)
        return templates.TemplateResponse(
            request,
            "_user_form.html",
            {
                "departments": depts,
                "error": str(exc),
                "session_user": _user,
                "form_data": _form_data(),
            },
        )
    await log_action(
        db,
        action="create_user",
        user_id=_user["user_id"],
        metadata={"username": user.username, "role": user.role},
    )
    users = await list_users(db)
    return templates.TemplateResponse(
        request,
        "_user_list.html",
        {"users": users, "session_user": _user, "success": "Usuario creado correctamente."},
    )


@router.post("/users/{user_id}/delete")
async def web_delete_user(
    user_id: int,
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    try:
        deleted = await delete_user(db, user_id, current_user_id=_user["user_id"])
    except ValueError:
        return HTMLResponse(status_code=409, content="Cannot delete yourself")
    if not deleted:
        return HTMLResponse(status_code=404, content="User not found")
    await log_action(
        db,
        action="delete_user",
        user_id=_user["user_id"],
        metadata={"user_id": user_id},
    )
    users = await list_users(db)
    return templates.TemplateResponse(
        request,
        "_user_list.html",
        {"users": users, "session_user": _user, "success": "Usuario eliminado correctamente."},
    )


@router.get("/users/{user_id}/reset-password")
async def web_reset_password_form(
    user_id: int,
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return HTMLResponse(status_code=404, content="User not found")
    return templates.TemplateResponse(
        request,
        "_reset_password_form.html",
        {"user_id": user.id, "username": user.username, "session_user": _user},
    )


@router.post("/users/{user_id}/reset-password")
async def web_reset_password(
    user_id: int,
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    form = await request.form()
    new_password = form["new_password"]
    if new_password != form.get("password_confirm", ""):
        edit_user = await get_user_by_id(db, user_id)
        if not edit_user:
            return HTMLResponse(status_code=404, content="User not found")
        return templates.TemplateResponse(
            request,
            "_reset_password_form.html",
            {
                "user_id": user_id,
                "username": edit_user.username,
                "session_user": _user,
                "error": "Las contraseñas no coinciden.",
            },
        )
    try:
        ok = await reset_password(db, user_id, new_password)
    except ValueError as exc:
        edit_user = await get_user_by_id(db, user_id)
        if not edit_user:
            return HTMLResponse(status_code=404, content="User not found")
        return templates.TemplateResponse(
            request,
            "_reset_password_form.html",
            {
                "user_id": user_id,
                "username": edit_user.username,
                "session_user": _user,
                "error": str(exc),
            },
        )
    if not ok:
        return HTMLResponse(status_code=404, content="User not found")
    await log_action(
        db,
        action="reset_password",
        user_id=_user["user_id"],
        metadata={"user_id": user_id},
    )
    users = await list_users(db)
    return templates.TemplateResponse(
        request,
        "_user_list.html",
        {"users": users, "session_user": _user, "success": "Contraseña actualizada correctamente."},
    )


@router.get("/users/{user_id}/edit")
async def web_edit_user_form(
    user_id: int,
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    user = await get_user_by_id(db, user_id)
    if not user:
        return HTMLResponse(status_code=404, content="User not found")
    depts = await get_departments(db)
    current_accessible_ids = [d.id for d in user.accessible_departments]
    return templates.TemplateResponse(
        request,
        "_edit_user_form.html",
        {
            "edit_user": user,
            "departments": depts,
            "current_accessible_ids": current_accessible_ids,
            "session_user": _user,
        },
    )


@router.post("/users/{user_id}/edit")
async def web_edit_user(
    user_id: int,
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    form = await request.form()
    ids = [int(x) for x in form.getlist("accessible_department_ids") if x.strip()]
    try:
        await update_user(
            db=db,
            user_id=user_id,
            username=form["username"],
            role=form["role"],
            department_id=int(form["department_id"]),
            accessible_department_ids=ids,
        )
    except ValueError as exc:
        depts = await get_departments(db)
        edit_user = await get_user_by_id(db, user_id)
        return templates.TemplateResponse(
            request,
            "_edit_user_form.html",
            {
                "edit_user": edit_user,
                "departments": depts,
                "current_accessible_ids": ids,
                "session_user": _user,
                "error": str(exc),
            },
        )
    await log_action(
        db,
        action="update_user",
        user_id=_user["user_id"],
        metadata={
            "target_user_id": user_id,
            "new_username": form["username"],
            "new_role": form["role"],
            "new_department_id": int(form["department_id"]),
        },
    )
    users = await list_users(db)
    return templates.TemplateResponse(
        request,
        "_user_list.html",
        {"users": users, "session_user": _user, "success": "Usuario actualizado correctamente."},
    )
