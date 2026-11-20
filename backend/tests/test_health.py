from fastapi import status

def test_health_check_endpoint(client):
    """Test 1: Health endpoint returns status healthy, application name, and version."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["application"] == "InfraMind API"
    assert data["version"] == "1.0.0"

def test_root_endpoint(client):
    """Verify root endpoint responds with metadata."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["application"] == "InfraMind API"
    assert data["api_v1"] == "/api/v1"
