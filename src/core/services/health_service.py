import logging

import asyncpg
import httpx

logger = logging.getLogger("nexus")


async def check_db(db_url: str) -> dict:
    try:
        conn = await asyncpg.connect(db_url)
        await conn.close()
        return {"status": "healthy"}
    except Exception:
        logger.exception("Health check DB failed")
        return {"status": "unhealthy", "detail": "Database connection failed"}


async def check_ollama(ollama_host: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ollama_host}/api/tags")
            if resp.status_code == 200:
                return {"status": "healthy"}
            return {"status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except Exception:
        logger.exception("Health check Ollama failed")
        return {"status": "unhealthy", "detail": "Ollama service unreachable"}


def aggregate(db_result: dict, ollama_result: dict) -> dict:
    services = {
        "database": {"status": db_result["status"]},
        "ollama": {"status": ollama_result["status"]},
    }
    if db_result["status"] == "healthy" and ollama_result["status"] == "healthy":
        return {"status": "healthy", "services": services}
    return {"status": "degraded", "services": services}
