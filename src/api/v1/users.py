import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import (
    ROLE_LEVELS,
    require_min_level,
    require_web_min_level,
)
from src.core.database import get_session
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
api_router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])
web_router = APIRouter(prefix="/web", tags=["admin-web"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    department_id: int
    accessible_department_ids: list[int]

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:
        if v not in ROLE_LEVELS:
            raise ValueError(f"Invalid role: {v}. Valid: {sorted(ROLE_LEVELS)}")
        return v


class ResetPasswordRequest(BaseModel):
    new_password: str


class UpdateUserRequest(BaseModel):
    username: str
    role: str
    department_id: int
    accessible_department_ids: list[int]

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:
        if v not in ROLE_LEVELS:
            raise ValueError(f"Invalid role: {v}. Valid: {sorted(ROLE_LEVELS)}")
        return v


@api_router.get("")
async def api_list_users(
    _user=Depends(require_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    return await list_users(db)


@api_router.post("", status_code=201)
async def api_create_user(
    body: CreateUserRequest,
    _user=Depends(require_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    try:
        user = await create_user(
            db=db,
            username=body.username,
            password=body.password,
            role=body.role,
            department_id=body.department_id,
            accessible_department_ids=body.accessible_department_ids,
        )
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    await log_action(
        db,
        action="create_user",
        user_id=_user["user_id"],
        metadata={"username": user.username, "role": user.role},
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "department_id": user.department_id,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


@api_router.delete("/{user_id}", status_code=204)
async def api_delete_user(
    user_id: int,
    _user=Depends(require_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    try:
        deleted = await delete_user(db, user_id, current_user_id=_user["user_id"])
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    await log_action(
        db,
        action="delete_user",
        user_id=_user["user_id"],
        metadata={"user_id": user_id},
    )


@api_router.post("/{user_id}/reset-password")
async def api_reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    _user=Depends(require_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    try:
        ok = await reset_password(db, user_id, body.new_password)
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    if not ok:
        return JSONResponse(status_code=404, content={"detail": "User not found"})
    await log_action(
        db,
        action="reset_password",
        user_id=_user["user_id"],
        metadata={"user_id": user_id},
    )


@api_router.put("/{user_id}")
async def api_update_user(
    user_id: int,
    body: UpdateUserRequest,
    _user=Depends(require_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    try:
        user = await update_user(
            db=db,
            user_id=user_id,
            username=body.username,
            role=body.role,
            department_id=body.department_id,
            accessible_department_ids=body.accessible_department_ids,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            return JSONResponse(status_code=404, content={"detail": msg})
        return JSONResponse(status_code=409, content={"detail": msg})
    await log_action(
        db,
        action="update_user",
        user_id=_user["user_id"],
        metadata={
            "target_user_id": user_id,
            "new_role": body.role,
            "new_department_id": body.department_id,
        },
    )
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "department_id": user.department_id,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


@web_router.get("/users")
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


@web_router.get("/users/new")
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


@web_router.post("/users")
async def web_create_user(
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    form = await request.form()
    if form["password"] != form.get("password_confirm", ""):
        depts = await get_departments(db)
        return templates.TemplateResponse(
            request,
            "_user_form.html",
            {
                "departments": depts,
                "error": "Las contraseñas no coinciden.",
                "session_user": _user,
                "form_data": {
                    "username": form.get("username", ""),
                    "role": form.get("role", ""),
                    "department_id": form.get("department_id", ""),
                    "accessible_department_ids": [
                        int(x) for x in form.getlist("accessible_department_ids") if x.strip()
                    ],
                },
            },
        )
    ids = [int(x) for x in form.getlist("accessible_department_ids") if x.strip()]
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
                "form_data": {
                    "username": form.get("username", ""),
                    "role": form.get("role", ""),
                    "department_id": form.get("department_id", ""),
                    "accessible_department_ids": [
                        int(x) for x in form.getlist("accessible_department_ids") if x.strip()
                    ],
                },
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


@web_router.post("/users/{user_id}/delete")
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


@web_router.get("/users/{user_id}/reset-password")
async def web_reset_password_form(
    user_id: int,
    request: Request,
    _user=Depends(require_web_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    if isinstance(_user, Response):
        return _user
    from sqlalchemy import select

    from src.core.models import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return HTMLResponse(status_code=404, content="User not found")
    return templates.TemplateResponse(
        request,
        "_reset_password_form.html",
        {"user_id": user.id, "username": user.username, "session_user": _user},
    )


@web_router.post("/users/{user_id}/reset-password")
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


@web_router.get("/users/{user_id}/edit")
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


@web_router.post("/users/{user_id}/edit")
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
