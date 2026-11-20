import pytest
from fastapi import status
from app.services.conversation_service import conversation_service

@pytest.fixture(autouse=True)
def clean_default_user_chats():
    all_convs = conversation_service._load_all()
    cleaned = {cid: c for cid, c in all_convs.items() if c.get("user_id") != "default_user"}
    conversation_service._save_all(cleaned)
    yield
    all_convs = conversation_service._load_all()
    cleaned = {cid: c for cid, c in all_convs.items() if c.get("user_id") != "default_user"}
    conversation_service._save_all(cleaned)

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


def test_greeting_unit_policy():
    """Validates that greeting is only attached for first response and stripped from follow-ups."""
    from app.services.ai.ai_service import AIService, GREETING_TEXT

    # 1. First response when model outputs clean body: greeting should be prepended
    ans1 = AIService._apply_greeting_policy("Here is the explanation of PostgreSQL replication lag.", is_first_response=True)
    assert ans1.startswith(GREETING_TEXT)
    assert "Here is the explanation" in ans1

    # 2. First response when model itself generated greeting: greeting normalized, not duplicated
    raw_with_greeting = "Hello! I am TitanOps AI, your assistant for Cloud Operations and Site Reliability Engineering (SRE).\n\nHere is the answer."
    ans2 = AIService._apply_greeting_policy(raw_with_greeting, is_first_response=True)
    assert ans2.count(GREETING_TEXT) == 1
    assert "Here is the answer." in ans2

    # 3. Follow-up response when model generated greeting: greeting MUST be stripped
    followup_raw = "Hello! I am TitanOps AI, your assistant for Cloud Operations and Site Reliability Engineering (SRE).\n\nHere is the follow-up answer."
    ans3 = AIService._apply_greeting_policy(followup_raw, is_first_response=False)
    assert GREETING_TEXT not in ans3
    assert "TitanOps AI" not in ans3
    assert ans3 == "Here is the follow-up answer."

    # 4. Follow-up response when model did not include greeting: returned untouched
    followup_clean = "Run `patronictl -c /etc/patroni/db.yml switchover` to mitigate lag."
    ans4 = AIService._apply_greeting_policy(followup_clean, is_first_response=False)
    assert ans4 == followup_clean
    assert GREETING_TEXT not in ans4


def test_greeting_only_once_in_multiturn_chat(client):
    """
    Verifies that across multiple turns in a conversation:
    - Turn 1: Greeting + actual answer
    - Turn 2: Actual answer only (no greeting)
    - Turn 3: Actual answer only (no greeting)
    - A new conversation: Greeting appears again on Turn 1
    """
    from app.services.ai.ai_service import GREETING_TEXT

    # --- Conversation A ---
    # Turn 1
    res1 = client.post("/api/v1/chat", json={"message": "What is an SRE?"})
    assert res1.status_code == status.HTTP_200_OK
    data1 = res1.json()
    conv_id = data1["conversation_id"]
    msg1 = data1["message"]
    assert msg1.startswith(GREETING_TEXT), f"First message should start with greeting: {msg1[:100]}"

    # Turn 2: Follow-up
    res2 = client.post("/api/v1/chat", json={"message": "What is an SLA?", "conversation_id": conv_id})
    assert res2.status_code == status.HTTP_200_OK
    data2 = res2.json()
    msg2 = data2["message"]
    assert GREETING_TEXT not in msg2, f"Second message should NOT contain greeting: {msg2[:100]}"
    assert not msg2.startswith("Hello! I am TitanOps AI")

    # Turn 3: Second follow-up
    res3 = client.post("/api/v1/chat", json={"message": "And what is an SLO?", "conversation_id": conv_id})
    assert res3.status_code == status.HTTP_200_OK
    data3 = res3.json()
    msg3 = data3["message"]
    assert GREETING_TEXT not in msg3, f"Third message should NOT contain greeting: {msg3[:100]}"

    # Verify conversation history preservation
    conv_res = client.get(f"/api/v1/conversations/{conv_id}")
    assert conv_res.status_code == status.HTTP_200_OK
    messages = conv_res.json().get("messages", [])
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
    assert len(assistant_msgs) >= 3
    # First assistant message retains greeting
    assert GREETING_TEXT in assistant_msgs[0]["content"]
    # Subsequent assistant messages DO NOT have greeting
    assert GREETING_TEXT not in assistant_msgs[1]["content"]
    assert GREETING_TEXT not in assistant_msgs[2]["content"]

    # --- Conversation B (New chat) ---
    res_new = client.post("/api/v1/chat", json={"message": "What is error budget?"})
    assert res_new.status_code == status.HTTP_200_OK
    data_new = res_new.json()
    msg_new = data_new["message"]
    assert msg_new.startswith(GREETING_TEXT), f"New chat should have greeting again on first message: {msg_new[:100]}"

