import time

from fastapi import APIRouter, Depends, Request

from src.core.config import settings
from src.core.services.health_service import aggregate, check_db, check_ollama

router = APIRouter(prefix="/api/v1")

_start_time = time.time()


def get_db_url() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def get_ollama_host() -> str:
    return settings.ollama_host


@router.get("/health/db")
async def health_db(db_url: str = Depends(get_db_url)):
    return await check_db(db_url)


@router.get("/health/ollama")
async def health_ollama(ollama_host: str = Depends(get_ollama_host)):
    return await check_ollama(ollama_host)


@router.get("/health")
async def health(
    request: Request,
    db_result: dict = Depends(health_db),
    ollama_result: dict = Depends(health_ollama),
):
    result = aggregate(db_result, ollama_result)
    result["version"] = "1.0.0"
    result["uptime_seconds"] = int(time.time() - _start_time)
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        result["request_id"] = request_id
    return result
