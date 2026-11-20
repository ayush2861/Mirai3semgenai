"""
Tests for Conversation Limit (Max 5) and Cascade Deletion of Data Folder.
"""

import io
import fitz
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.auth_service import auth_service
from app.services.conversation_service import conversation_service
from app.services.document_service import document_service

client = TestClient(app)

def create_sample_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def clean_limit_test_user():
    test_email = "limit_tester@titanops.ai"
    users = auth_service._load_users()
    user_id = next((u["user_id"] for u in users.values() if u.get("email") == test_email), None)
    if not user_id:
        from app.schemas.auth import UserRegisterRequest
        u = auth_service.register_user(
            UserRegisterRequest(
                username="limit_tester",
                email=test_email,
                password="Password123!",
                full_name="Limit Tester"
            )
        )
        user_id = u.user_id
        token = u.access_token
    else:
        token, _ = auth_service.create_access_token(user_id, test_email, "limit_tester")

    headers = {"Authorization": f"Bearer {token}"}

    # Clean existing conversations for this user
    all_convs = conversation_service._load_all()
    cleaned = {cid: c for cid, c in all_convs.items() if c.get("user_id") != user_id}
    conversation_service._save_all(cleaned)

    yield {"headers": headers, "user_id": user_id}

    # Post-cleanup
    all_convs = conversation_service._load_all()
    cleaned = {cid: c for cid, c in all_convs.items() if c.get("user_id") != user_id}
    conversation_service._save_all(cleaned)


def test_conversation_limit_enforced_and_data_cleanup(clean_limit_test_user):
    headers = clean_limit_test_user["headers"]
    user_id = clean_limit_test_user["user_id"]

    # 1. Upload a PDF runbook to attach to conversation 1
    pdf_bytes = create_sample_pdf("Incident Runbook for Database failover in Kubernetes cluster.")
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("db_failover_runbook.pdf", pdf_bytes, "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    doc_id = upload_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/index", headers=headers)

    # Verify physical file exists in uploads
    stored_meta = document_service._load_metadata()[doc_id]
    upload_file_path = settings.UPLOADS_DIR / stored_meta["stored_filename"]
    assert upload_file_path.exists(), "Uploaded PDF must exist in data/uploads"

    # 2. Create 5 conversations (reaching max limit)
    conv_ids = []
    # Conv 1 has the PDF attached
    conv1_res = client.post(
        "/api/v1/conversations",
        json={"title": "Chat 1 with PDF", "document_ids": [doc_id]},
        headers=headers
    )
    assert conv1_res.status_code == status.HTTP_201_CREATED
    conv_ids.append(conv1_res.json()["id"])

    for i in range(2, 6):
        res = client.post(
            "/api/v1/conversations",
            json={"title": f"Chat {i}"},
            headers=headers
        )
        assert res.status_code == status.HTTP_201_CREATED
        conv_ids.append(res.json()["id"])

    assert len(conv_ids) == 5

    # 3. Attempting to create a 6th conversation must fail with 400
    conv6_res = client.post(
        "/api/v1/conversations",
        json={"title": "Chat 6 - Should Fail"},
        headers=headers
    )
    assert conv6_res.status_code == status.HTTP_400_BAD_REQUEST
    err_json = conv6_res.json()
    assert "CONVERSATION_LIMIT_REACHED" in str(err_json)
    assert "Conversation limit reached" in str(err_json)

    # 4. Attempting to send a chat message without conv_id (which auto-creates a conversation) must also fail with 400
    chat_overflow = client.post(
        "/api/v1/chat",
        json={"message": "This should not create a 6th chat session"},
        headers=headers
    )
    assert chat_overflow.status_code == status.HTTP_400_BAD_REQUEST
    assert "CONVERSATION_LIMIT_REACHED" in str(chat_overflow.json())

    # 5. Delete Conv 1 (which holds the uploaded PDF)
    del_res = client.delete(f"/api/v1/conversations/{conv_ids[0]}", headers=headers)
    assert del_res.status_code == status.HTTP_200_OK

    # Verify that deleting Conv 1 also cascaded to delete the PDF from data/uploads and data/processed
    assert not upload_file_path.exists(), "Uploaded file must be removed from data/uploads upon conversation deletion"
    processed_path = settings.DATA_DIR / "processed" / f"{doc_id}.json"
    assert not processed_path.exists(), "Processed file must be removed from data/processed upon conversation deletion"

    # Verify document index no longer has doc_id
    with pytest.raises(Exception):
        document_service.get_document(doc_id)

    # 6. Now conversation count is 4/5, creating a new chat must succeed!
    new_chat_res = client.post(
        "/api/v1/conversations",
        json={"title": "New Chat after Deletion"},
        headers=headers
    )
    assert new_chat_res.status_code == status.HTTP_201_CREATED
    assert new_chat_res.json()["title"] == "New Chat after Deletion"
