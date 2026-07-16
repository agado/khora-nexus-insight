import asyncpg
import httpx


async def check_db(db_url: str) -> dict:
    try:
        conn = await asyncpg.connect(db_url)
        await conn.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "detail": str(e)}


async def check_ollama(ollama_host: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ollama_host}/api/tags")
            if resp.status_code == 200:
                return {"status": "healthy"}
            return {"status": "unhealthy", "detail": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "detail": str(e)}


def aggregate(db_result: dict, ollama_result: dict) -> dict:
    services = {
        "database": {"status": db_result["status"]},
        "ollama": {"status": ollama_result["status"]},
    }
    if db_result["status"] == "healthy" and ollama_result["status"] == "healthy":
        return {"status": "healthy", "services": services}
    return {"status": "degraded", "services": services}
