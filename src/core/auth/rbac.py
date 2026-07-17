import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jwt import PyJWTError

from src.core.auth.jwt import verify_token

logger = logging.getLogger("nexus")
security = HTTPBearer()


async def get_current_user(token: str = Depends(security)):
    try:
        payload = verify_token(token.credentials)
        return payload
    except PyJWTError:
        logger.warning("Invalid or expired token")
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
