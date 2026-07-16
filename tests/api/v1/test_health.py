from unittest.mock import AsyncMock, patch


def test_health_ollama_healthy(client):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 200
        response = client.get("/api/v1/health/ollama")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_health_ollama_unhealthy(client):
    with patch("httpx.AsyncClient.get", side_effect=ConnectionError("Ollama down")):
        response = client.get("/api/v1/health/ollama")
        assert response.status_code == 200
        assert response.json()["status"] == "unhealthy"


def test_health_db_healthy(client):
    with patch("asyncpg.connect", new_callable=AsyncMock):
        response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_health_db_unhealthy(client):
    with patch("asyncpg.connect", side_effect=Exception("DB down")):
        response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        assert response.json()["status"] == "unhealthy"


def test_health_aggregator_all_healthy(client):
    with (
        patch("asyncpg.connect", new_callable=AsyncMock),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        mock_get.return_value.status_code = 200
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"]["status"] == "healthy"
        assert data["services"]["ollama"]["status"] == "healthy"


def test_health_aggregator_degraded(client):
    with (
        patch("asyncpg.connect", new_callable=AsyncMock),
        patch("httpx.AsyncClient.get", side_effect=ConnectionError("Ollama down")),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
