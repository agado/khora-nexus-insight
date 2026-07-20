import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
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
    list_users,
    reset_password,
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
        return HTMLResponse(status_code=409, content=str(exc))
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
        return HTMLResponse(status_code=409, content=str(exc))
    if not deleted:
        return HTMLResponse(status_code=404, content="User not found")
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
    ok = await reset_password(db, user_id, body.new_password)
    if not ok:
        return HTMLResponse(status_code=404, content="User not found")
    await log_action(
        db,
        action="reset_password",
        user_id=_user["user_id"],
        metadata={"user_id": user_id},
    )
    return {"detail": "Password reset"}


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
            {"departments": depts, "error": str(exc), "session_user": _user},
        )
    await log_action(
        db,
        action="create_user",
        user_id=_user["user_id"],
        metadata={"username": user.username, "role": user.role},
    )
    return RedirectResponse(url="/web/users", status_code=302)


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
    return RedirectResponse(url="/web/users", status_code=302)


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
    ok = await reset_password(db, user_id, form["new_password"])
    if not ok:
        return HTMLResponse(status_code=404, content="User not found")
    await log_action(
        db,
        action="reset_password",
        user_id=_user["user_id"],
        metadata={"user_id": user_id},
    )
    return RedirectResponse(url="/web/users", status_code=302)
