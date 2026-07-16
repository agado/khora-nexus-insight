from unittest.mock import AsyncMock, patch

import pytest

from src.core.services.health_service import aggregate, check_db, check_ollama


@pytest.mark.asyncio
async def test_check_db_healthy():
    with patch("asyncpg.connect", new_callable=AsyncMock):
        result = await check_db("postgresql://test:test@localhost:5432/test")
        assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_check_db_unhealthy():
    with patch("asyncpg.connect", side_effect=Exception("DB down")):
        result = await check_db("postgresql://test:test@localhost:5432/test")
        assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_check_ollama_healthy():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 200
        result = await check_ollama("http://ollama:11434")
        assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_check_ollama_unhealthy():
    with patch("httpx.AsyncClient.get", side_effect=ConnectionError("down")):
        result = await check_ollama("http://ollama:11434")
        assert result["status"] == "unhealthy"


def test_aggregate_both_healthy():
    result = aggregate({"status": "healthy"}, {"status": "healthy"})
    assert result["status"] == "healthy"
    assert result["services"]["database"]["status"] == "healthy"
    assert result["services"]["ollama"]["status"] == "healthy"


def test_aggregate_db_unhealthy():
    result = aggregate({"status": "unhealthy"}, {"status": "healthy"})
    assert result["status"] == "degraded"


def test_aggregate_both_unhealthy():
    result = aggregate({"status": "unhealthy"}, {"status": "unhealthy"})
    assert result["status"] == "degraded"
