from fastapi.testclient import TestClient

from src.main import create_app


class TestDocsExposure:
    def test_docs_disabled_in_production(self):
        client = TestClient(create_app(env="production"))
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = client.get(path)
            assert response.status_code == 404, f"{path} deberia estar deshabilitado en produccion"

    def test_docs_enabled_in_development(self):
        client = TestClient(create_app(env="development"))
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200
