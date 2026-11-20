from fastapi import status

def test_valid_chat_request(client):
    """Test 2: Valid chat inquiry returns grounded response structure with generated conversation_id."""
    payload = {
        "message": "What is the replication lag threshold for PostgreSQL?",
        "conversation_id": None
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "conversation_id" in data
    assert data["conversation_id"] is not None
    assert "message" in data
    assert data["status"] in ("completed", "pending")

def test_valid_chat_request_with_existing_conversation_id(client):
    """Verify chat inquiry with existing conversation_id preserves ID."""
    custom_id = "test-conv-sre-123"
    payload = {
        "message": "How do we recover from an etcd quorum loss?",
        "conversation_id": custom_id
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["conversation_id"] == custom_id
    assert data["status"] in ("completed", "pending")

def test_invalid_chat_request_empty_message(client):
    """Test 3a: Empty message fails validation with 422."""
    payload = {
        "message": "   ",
        "conversation_id": None
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "error" in data

def test_invalid_chat_request_missing_body(client):
    """Test 3b: Missing message body returns 422 validation error."""
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "error" in data
