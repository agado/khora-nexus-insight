import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import ROLE_LEVELS, require_min_level
from src.core.database import get_session
from src.core.services.audit_service import log_action
from src.core.services.user_service import (
    create_user,
    delete_user,
    list_users,
    reset_password,
    update_user,
)

logger = logging.getLogger("nexus")
router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])


def _validate_role_value(v: str) -> str:
    if v not in ROLE_LEVELS:
        raise ValueError(f"Invalid role: {v}. Valid: {sorted(ROLE_LEVELS)}")
    return v


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    department_id: int
    accessible_department_ids: list[int]

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:
        return _validate_role_value(v)


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
        return _validate_role_value(v)


@router.get("")
async def api_list_users(
    _user=Depends(require_min_level(3)),
    db: AsyncSession = Depends(get_session),
):
    return await list_users(db)


@router.post("", status_code=201)
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


@router.delete("/{user_id}", status_code=204)
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


@router.post("/{user_id}/reset-password")
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


@router.put("/{user_id}")
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
