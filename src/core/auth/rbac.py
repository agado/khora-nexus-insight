import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jwt import PyJWTError

from src.core.auth.jwt import verify_token

logger = logging.getLogger("nexus")
security = HTTPBearer(auto_error=False)

ROLE_LEVELS = {
    "admin": 3,
    "lead": 2,
    "staff": 1,
}


async def get_current_user(token: str | None = Depends(security)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = verify_token(token.credentials)
        return payload
    except PyJWTError:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None


async def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = verify_token(token)
        return payload
    except PyJWTError:
        logger.warning("Invalid or expired token from cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None


def require_role(required_role: str):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != required_role:
            logger.warning(
                "Forbidden: role '%s' != '%s'",
                current_user.get("role"),
                required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


def require_min_level(min_level: int):
    async def level_checker(current_user: dict = Depends(get_current_user)):
        user_level = ROLE_LEVELS.get(current_user.get("role", ""), 0)
        if user_level < min_level:
            logger.warning(
                "Forbidden: role '%s' level %d < %d",
                current_user.get("role"),
                user_level,
                min_level,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return level_checker
