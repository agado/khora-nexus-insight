from os import getenv

from fastapi import APIRouter, Depends

from src.core.services.health_service import aggregate, check_db, check_ollama

router = APIRouter(prefix="/api/v1")


def get_db_url() -> str:
    url = getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def get_ollama_host() -> str:
    return getenv("OLLAMA_HOST", "http://ollama_service:11434")


@router.get("/health/db")
async def health_db(db_url: str = Depends(get_db_url)):
    return await check_db(db_url)


@router.get("/health/ollama")
async def health_ollama(ollama_host: str = Depends(get_ollama_host)):
    return await check_ollama(ollama_host)


@router.get("/health")
async def health(
    db_result: dict = Depends(health_db),
    ollama_result: dict = Depends(health_ollama),
):
    return aggregate(db_result, ollama_result)
