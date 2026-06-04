from datetime import datetime


class TestHealthCheck:
    """Smoke tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        """Scenario: Health check on running backend."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_fields(self, client):
        """Scenario: Health check response contains required fields."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["version"], str) and data["version"]
        assert isinstance(data["timestamp"], str)
        # Verify ISO 8601 timestamp format
        datetime.fromisoformat(data["timestamp"])
        assert data["environment"] in ("development", "production", "testing")

    def test_health_response_time(self, client):
        """Scenario: Health check response time under 1 second."""
        import time
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0
