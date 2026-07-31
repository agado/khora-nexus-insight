def test_health_response_has_request_id(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID v4 format


def test_each_request_gets_unique_request_id(client):
    r1 = client.get("/api/v1/health")
    r2 = client.get("/api/v1/health")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


def test_health_response_includes_request_id_field(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] == response.headers["X-Request-ID"]
