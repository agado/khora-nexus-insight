class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        response = client.get("/login")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src" in response.headers.get("Content-Security-Policy", "")
