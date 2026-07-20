import logging

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
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


def _redirect_to_login(request: Request) -> Response:
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return Response(status_code=200, headers={"HX-Redirect": "/login"})
    return RedirectResponse(url="/login", status_code=302)


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


def _get_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get("access_token")


async def get_current_user_from_cookie(request: Request):
    token = _get_token_from_cookie(request)
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


async def require_web_user(request: Request):
    """Web-only dependency: returns redirect Response instead of 401.

    For HTMX requests returns HX-Redirect header for full page navigation.
    """
    token = _get_token_from_cookie(request)
    if not token:
        return _redirect_to_login(request)
    try:
        return verify_token(token)
    except PyJWTError:
        return _redirect_to_login(request)


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


def require_web_min_level(min_level: int):
    async def _checker(_user=Depends(require_web_user)):
        if isinstance(_user, Response):
            return _user
        user_level = ROLE_LEVELS.get(_user.get("role", ""), 0)
        if user_level < min_level:
            return HTMLResponse(status_code=403, content="Acceso denegado")
        return _user

    return _checker
