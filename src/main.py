import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from jwt import PyJWTError
from starlette.templating import Jinja2Templates

from src.core.auth.jwt import verify_token
from src.core.config import check_jwt_secret, settings
from src.core.database import engine
from src.core.middleware import JSONFormatter
from src.core.middleware.access_log import AccessLogMiddleware
from src.core.middleware.rate_limiter import RateLimitMiddleware
from src.core.middleware.request_id import RequestIDMiddleware
from src.core.middleware.security_headers import SecurityHeadersMiddleware

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("nexus")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["company_name"] = settings.company_name

from src.api.v1.api_users import router as users_api_router
from src.api.v1.auth import router as auth_router
from src.api.v1.documents import router as documents_router
from src.api.v1.health import router as health_router
from src.api.v1.rag import router as rag_router
from src.api.v1.web import router as web_router
from src.api.v1.web_users import router as users_web_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    check_jwt_secret(env=settings.nexus_env)
    logger.info("startup", extra={"version": "1.0.0"})
    yield
    await engine.dispose()
    logger.info("shutdown")


def create_app(env: str | None = None) -> FastAPI:
    """Crea la aplicacion. En produccion se ocultan /docs, /redoc y /openapi.json
    (OWASP A05: no exponer el contrato de la API al exterior)."""
    is_production = (env or settings.nexus_env).lower() == "production"
    app = FastAPI(
        title="Khora — Nexus Insight",
        lifespan=lifespan,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(health_router)
    app.include_router(rag_router)
    app.include_router(users_api_router)
    app.include_router(users_web_router)
    app.include_router(web_router)
    return app


app = create_app()


@app.get("/")
async def read_root(request: Request):
    token = request.cookies.get("access_token")
    if token:
        try:
            verify_token(token)
            return RedirectResponse(url="/dashboard", status_code=302)
        except PyJWTError:
            pass
    return RedirectResponse(url="/login", status_code=302)
