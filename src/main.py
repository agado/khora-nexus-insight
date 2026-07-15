from fastapi import FastAPI
import os
import asyncpg

app = FastAPI(title="Nexus Insight - Infra Check")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "¡La infraestructura de Khora Nexus Insight está viva!",
        "env": os.getenv("ENV", "development")
    }

@app.get("/health/db")
async def test_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return {"status": "error", "message": "DATABASE_URL no encontrada en el entorno"}
    try:
        # Si la URL viene con "+asyncpg", se lo quitamos solo para este test nativo
        clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        conn = await asyncpg.connect(clean_url)
        await conn.close()
        return {"status": "healthy", "database": "¡Conexión con PostgreSQL establecida con éxito! 🐘"}
    except Exception as e:
        return {"status": "unhealthy", "Error: Conexión con PostgreSQL no establecida 🐘": str(e)}
   