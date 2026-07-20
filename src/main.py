import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from jwt import PyJWTError
from starlette.templating import Jinja2Templates

from src.core.auth.jwt import verify_token
from src.core.config import settings
from src.core.middleware.rate_limiter import RateLimitMiddleware
from src.core.middleware.security_headers import SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("nexus")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["company_name"] = settings.company_name

from src.api.v1.auth import router as auth_router
from src.api.v1.documents import router as documents_router
from src.api.v1.health import router as health_router
from src.api.v1.rag import router as rag_router
from src.api.v1.users import api_router as users_api_router, web_router as users_web_router
from src.api.v1.web import router as web_router

app = FastAPI(title="Khora — Nexus Insight")

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
