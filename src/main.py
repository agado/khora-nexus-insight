import logging

from fastapi import FastAPI

from src.api.v1.auth import router as auth_router
from src.api.v1.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("nexus")

app = FastAPI(title="Nexus Insight - Infra Check")

app.include_router(auth_router)
app.include_router(health_router)


@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {
        "status": "online",
        "message": "¡La infraestructura de Khora Nexus Insight está viva!",
        "env": __import__("os").getenv("ENV", "development"),
    }
