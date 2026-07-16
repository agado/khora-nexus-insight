import pytest
from fastapi.testclient import TestClient

from src.api.v1.health import get_db_url, get_ollama_host
from src.main import app

app.dependency_overrides[get_db_url] = lambda: "postgresql://test:test@localhost:5432/test"
app.dependency_overrides[get_ollama_host] = lambda: "http://ollama:11434"


@pytest.fixture
def client():
    return TestClient(app)
