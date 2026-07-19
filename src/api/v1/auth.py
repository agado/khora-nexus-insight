import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.services.audit_service import log_action
from src.core.services.auth_service import authenticate_user

logger = logging.getLogger("nexus")
router = APIRouter(prefix="/api/v1/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_session)):
    result = await authenticate_user(db, request.username, request.password)
    if not result:
        logger.warning("Login failed: %s", request.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await log_action(db, action="login", user_id=result["user_id"])
    logger.info("Login successful: %s", request.username)
    return {"access_token": result["access_token"], "token_type": "bearer"}
