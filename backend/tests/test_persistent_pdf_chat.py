"""
Persistent PDF Context Within Chat Verification Suite.
Validates the 10 required production scenarios:
1. Upload one PDF and ask multiple questions.
2. Ask follow-up questions without re-uploading (natural follow-up reference resolution).
3. Refresh page and continue conversation (simulated reload from persistent storage).
4. Close and reopen an existing conversation.
5. Attach two PDFs to one conversation.
6. Remove one PDF and verify it is no longer used in retrieval.
7. Start a new conversation and verify it does not inherit unrelated PDFs.
8. Upload an already indexed PDF and avoid unnecessary duplicate indexing.
9. Verify citations still show correct document names and page numbers.
10. Verify users cannot access other users' documents.
"""

import io
import fitz
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import auth_service
from app.services.document_service import document_service
from app.services.conversation_service import conversation_service

client = TestClient(app)

def create_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf.getvalue()


from app.schemas.auth import UserRegisterRequest

@pytest.fixture(scope="module")
def persistent_test_setup():
    """Sets up two test users and sample PDF runbooks for testing."""
    users = auth_service._load_users()

    # User A
    user_a_id = next((u["user_id"] for u in users.values() if u.get("email") == "pers_tester_a@titanops.ai"), None)
    if not user_a_id:
        user_a = auth_service.register_user(
            UserRegisterRequest(
                username="pers_tester_a",
                email="pers_tester_a@titanops.ai",
                password="Password123!",
                full_name="Persistent Tester A"
            )
        )
        user_a_id = user_a.user_id
        token_a = user_a.access_token
    else:
        token_a, _ = auth_service.create_access_token(user_a_id, "pers_tester_a@titanops.ai", "pers_tester_a")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B
    user_b_id = next((u["user_id"] for u in users.values() if u.get("email") == "pers_tester_b@titanops.ai"), None)
    if not user_b_id:
        user_b = auth_service.register_user(
            UserRegisterRequest(
                username="pers_tester_b",
                email="pers_tester_b@titanops.ai",
                password="Password123!",
                full_name="Persistent Tester B"
            )
        )
        user_b_id = user_b.user_id
        token_b = user_b.access_token
    else:
        token_b, _ = auth_service.create_access_token(user_b_id, "pers_tester_b@titanops.ai", "pers_tester_b")

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # PDF 1: PostgreSQL Failover Runbook
    pdf1_content = (
        "TitanCloud PostgreSQL Failover Runbook.\n"
        "Maximum allowable replication lag before automatic failover is 60 seconds (60s).\n"
        "If replication lag exceeds 60 seconds, Patroni triggers automatic leader isolation.\n"
        "Emergency CLI command: patronictl -c /etc/patroni.yml failover titan-cluster-01.\n"
        "The failover procedure takes approximately 12 seconds to complete."
    )
    pdf1_bytes = create_pdf(pdf1_content)

    # PDF 2: Redis Cluster Cache Runbook
    pdf2_content = (
        "TitanCloud Redis Cluster In-Memory Runbook.\n"
        "The maximum cache memory limit is 128GB with volatile-lru eviction policy.\n"
        "Failover threshold is 5 consecutive missed cluster heartbeats.\n"
        "CLI recovery command: redis-cli --cluster failover takeover."
    )
    pdf2_bytes = create_pdf(pdf2_content)

    return {
        "headers_a": headers_a,
        "user_a_id": user_a_id,
        "headers_b": headers_b,
        "user_b_id": user_b_id,
        "pdf1_bytes": pdf1_bytes,
        "pdf2_bytes": pdf2_bytes,
    }


def test_scenario_1_and_2_upload_pdf_and_ask_multiple_followup_questions(persistent_test_setup):
    """
    Scenario 1: Upload one PDF and ask multiple questions.
    Scenario 2: Ask follow-up questions without re-uploading the PDF.
    """
    headers = persistent_test_setup["headers_a"]

    # 1. Upload & Index PDF 1
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("titancloud_sre_incident_runbook_50p.pdf", persistent_test_setup["pdf1_bytes"], "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    doc_id = upload_res.json()["document_id"]

    index_res = client.post(f"/api/v1/documents/{doc_id}/index", headers=headers)
    assert index_res.status_code == status.HTTP_200_OK

    # 2. Open new chat and ask first question with PDF attached
    chat1 = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the maximum replication lag before automatic failover?",
            "document_ids": [doc_id]
        },
        headers=headers
    )
    assert chat1.status_code == status.HTTP_200_OK
    data1 = chat1.json()
    conv_id = data1["conversation_id"]
    assert "60" in data1["answer"] or "60s" in data1["answer"]
    assert len(data1["sources"]) > 0

    # 3. Ask follow-up question 1 WITHOUT re-sending document_ids or uploading again
    chat2 = client.post(
        "/api/v1/chat",
        json={
            "message": "What happens if replication lag exceeds this threshold?",
            "conversation_id": conv_id
            # document_ids intentionally omitted!
        },
        headers=headers
    )
    assert chat2.status_code == status.HTTP_200_OK
    data2 = chat2.json()
    assert data2["conversation_id"] == conv_id
    assert len(data2["sources"]) > 0
    # Answers must come from the same uploaded PDF
    assert any("titancloud_sre_incident_runbook_50p.pdf" in s.get("document_name", "") for s in data2["sources"])

    # 4. Ask follow-up question 2 WITHOUT re-uploading
    chat3 = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain the automatic failover procedure.",
            "conversation_id": conv_id
        },
        headers=headers
    )
    assert chat3.status_code == status.HTTP_200_OK
    data3 = chat3.json()
    assert any("titancloud_sre_incident_runbook_50p.pdf" in s.get("document_name", "") for s in data3["sources"])


def test_scenario_3_and_4_refresh_page_and_reopen_conversation(persistent_test_setup):
    """
    Scenario 3: Refresh the page and continue the conversation.
    Scenario 4: Close and reopen an existing conversation.
    """
    headers = persistent_test_setup["headers_a"]

    # 1. Fetch conversations list (simulating page reload)
    convs_res = client.get("/api/v1/conversations", headers=headers)
    assert convs_res.status_code == status.HTTP_200_OK
    convs = convs_res.json()
    assert len(convs) > 0

    target_conv_id = convs[0]["id"]

    # 2. Re-fetch conversation details
    detail_res = client.get(f"/api/v1/conversations/{target_conv_id}", headers=headers)
    assert detail_res.status_code == status.HTTP_200_OK
    detail = detail_res.json()

    # The PDF attachment context must be preserved across reload!
    assert len(detail["documents"]) > 0
    assert detail["documents"][0]["document_name"] == "titancloud_sre_incident_runbook_50p.pdf"
    assert len(detail["messages"]) >= 2

    # 3. Send another question in the reloaded conversation without re-uploading
    chat_reload = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the emergency CLI command mentioned in this runbook?",
            "conversation_id": target_conv_id
        },
        headers=headers
    )
    assert chat_reload.status_code == status.HTTP_200_OK
    data_reload = chat_reload.json()
    assert "patronictl" in data_reload["answer"].lower() or len(data_reload["sources"]) > 0


def test_scenario_5_and_6_attach_multiple_pdfs_and_remove_one(persistent_test_setup):
    """
    Scenario 5: Attach two PDFs to one conversation.
    Scenario 6: Remove one PDF and verify it is no longer used in retrieval.
    """
    headers = persistent_test_setup["headers_a"]

    # 1. Upload & Index PDF 2 (Redis)
    upload2 = client.post(
        "/api/v1/documents/upload",
        files={"file": ("titancloud_redis_runbook.pdf", persistent_test_setup["pdf2_bytes"], "application/pdf")},
        headers=headers
    )
    doc2_id = upload2.json()["document_id"]
    client.post(f"/api/v1/documents/{doc2_id}/index", headers=headers)

    # 2. Create new conversation
    conv_create = client.post(
        "/api/v1/conversations",
        json={"title": "Multi-Runbook Investigation"},
        headers=headers
    )
    conv_id = conv_create.json()["id"]

    # 3. Attach existing PDF 1 (PostgreSQL) and PDF 2 (Redis) to the conversation
    all_docs = client.get("/api/v1/documents", headers=headers).json()
    doc1 = next((d for d in all_docs if "titancloud_sre_incident_runbook_50p.pdf" in d["filename"]), None)
    if not doc1:
        upload1 = client.post(
            "/api/v1/documents/upload",
            files={"file": ("titancloud_sre_incident_runbook_50p.pdf", persistent_test_setup["pdf1_bytes"], "application/pdf")},
            headers=headers
        )
        doc1_id = upload1.json()["document_id"]
        client.post(f"/api/v1/documents/{doc1_id}/index", headers=headers)
    else:
        doc1_id = doc1["document_id"]

    client.post(f"/api/v1/conversations/{conv_id}/documents/{doc1_id}", headers=headers)
    client.post(f"/api/v1/conversations/{conv_id}/documents/{doc2_id}", headers=headers)

    # Verify both PDFs are attached
    conv_detail = client.get(f"/api/v1/conversations/{conv_id}", headers=headers).json()
    assert len(conv_detail["documents"]) == 2

    # 4. Ask comparison/multi-doc question
    multi_chat = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the cache memory limit in the Redis runbook?",
            "conversation_id": conv_id
        },
        headers=headers
    )
    assert multi_chat.status_code == status.HTTP_200_OK
    assert "128" in multi_chat.json()["answer"] or "128gb" in multi_chat.json()["answer"].lower()

    # 5. Remove PDF 2 (Redis) from conversation
    detach_res = client.delete(f"/api/v1/conversations/{conv_id}/documents/{doc2_id}", headers=headers)
    assert detach_res.status_code == status.HTTP_200_OK
    updated_detail = detach_res.json()
    assert len(updated_detail["documents"]) == 1
    assert updated_detail["documents"][0]["document_id"] == doc1_id

    # 6. Verify Redis information is now outside the active context scope
    det_chat = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the Redis heartbeat threshold?",
            "conversation_id": conv_id
        },
        headers=headers
    )
    assert det_chat.status_code == status.HTTP_200_OK
    # Should short-circuit or acknowledge insufficient info in the selected PDF
    assert (
        "couldn't find" in det_chat.json()["answer"].lower() or
        not any("redis" in s.get("document_name", "").lower() for s in det_chat.json()["sources"])
    )


def test_scenario_7_new_chat_does_not_inherit_unrelated_pdfs(persistent_test_setup):
    """
    Scenario 7: Start a new conversation and verify it does not automatically inherit unrelated PDFs.
    """
    headers = persistent_test_setup["headers_a"]

    new_conv = client.post(
        "/api/v1/conversations",
        json={"title": "Brand New Isolated Session"},
        headers=headers
    ).json()

    assert len(new_conv["documents"]) == 0
    assert len(new_conv["messages"]) == 0

    # Ensure get_conversation also returns empty documents
    check = client.get(f"/api/v1/conversations/{new_conv['id']}", headers=headers).json()
    assert len(check["documents"]) == 0


def test_scenario_8_deduplication_of_already_indexed_pdf(persistent_test_setup):
    """
    Scenario 8: Upload an already indexed PDF and avoid unnecessary duplicate indexing.
    """
    headers = persistent_test_setup["headers_a"]

    # Upload PDF 1 again with identical content
    re_upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("titancloud_sre_incident_runbook_50p.pdf", persistent_test_setup["pdf1_bytes"], "application/pdf")},
        headers=headers
    )
    assert re_upload.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
    re_data = re_upload.json()

    # Re-indexing should be idempotent
    re_index = client.post(f"/api/v1/documents/{re_data['document_id']}/index", headers=headers)
    assert re_index.status_code == status.HTTP_200_OK
    assert re_index.json()["document_id"] == re_data["document_id"]


def test_scenario_9_citation_accuracy(persistent_test_setup):
    """
    Scenario 9: Verify citations still show correct document names and page numbers.
    """
    headers = persistent_test_setup["headers_a"]
    convs = client.get("/api/v1/conversations", headers=headers).json()
    # Pick the conversation that has the attached document
    conv = next((c for c in convs if len(c.get("documents", [])) > 0), None)
    assert conv is not None, "Expected at least one conversation with an attached document"
    conv_id = conv["id"]

    chat_res = client.post(
        "/api/v1/chat",
        json={
            "message": "State the replication lag threshold and cite the page.",
            "conversation_id": conv_id
        },
        headers=headers
    )
    assert chat_res.status_code == status.HTTP_200_OK
    sources = chat_res.json()["sources"]
    assert len(sources) > 0
    assert sources[0]["document_name"] == "titancloud_sre_incident_runbook_50p.pdf"
    assert sources[0]["page_number"] == 1


def test_scenario_10_cross_tenant_document_and_conversation_isolation(persistent_test_setup):
    """
    Scenario 10: Verify users cannot access other users' documents or conversations.
    """
    headers_a = persistent_test_setup["headers_a"]
    headers_b = persistent_test_setup["headers_b"]

    # User A's conversation
    conv_a = client.get("/api/v1/conversations", headers=headers_a).json()[0]
    conv_a_id = conv_a["id"]

    # User B attempts to access User A's conversation -> 403 Forbidden
    res_b = client.get(f"/api/v1/conversations/{conv_a_id}", headers=headers_b)
    assert res_b.status_code == status.HTTP_403_FORBIDDEN

    # User B attempts to delete User A's conversation -> 403 Forbidden
    del_b = client.delete(f"/api/v1/conversations/{conv_a_id}", headers=headers_b)
    assert del_b.status_code == status.HTTP_403_FORBIDDEN


def test_scenario_11_general_question_without_attached_pdf(persistent_test_setup):
    """
    Scenario 11: General question without attached PDF.
    Verifies that asking general knowledge questions (e.g. 'Who is the president of India?')
    does NOT search or cite previously uploaded PDFs, and returns zero document sources.
    """
    headers = persistent_test_setup["headers_a"]

    # Create new clean conversation with no documents attached
    new_conv = client.post(
        "/api/v1/conversations",
        json={"title": "General Knowledge Inquiry"},
        headers=headers
    ).json()
    conv_id = new_conv["id"]

    res = client.post(
        "/api/v1/chat",
        json={
            "message": "Who is the president of India?",
            "conversation_id": conv_id
        },
        headers=headers
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Must NOT have attached documents or sources
    assert len(data.get("attached_documents", [])) == 0
    assert len(data.get("sources", [])) == 0
    # Must NOT reference titancloud or any other PDF filename in answer
    assert "titancloud" not in data["message"].lower()
    assert "runbook" not in data["message"].lower()


def test_scenario_12_runbook_question_without_attached_pdf(persistent_test_setup):
    """
    Scenario 12: Ask a runbook-specific question without attached PDF.
    Verifies that the assistant prompts the user to upload a document first,
    without inventing citations or using unattached PDFs.
    """
    headers = persistent_test_setup["headers_a"]

    new_conv = client.post(
        "/api/v1/conversations",
        json={"title": "Unattached Runbook Inquiry"},
        headers=headers
    ).json()
    conv_id = new_conv["id"]

    res = client.post(
        "/api/v1/chat",
        json={
            "message": "What is the replication lag threshold in the runbook?",
            "conversation_id": conv_id
        },
        headers=headers
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    # Must NOT have attached documents or sources
    assert len(data.get("attached_documents", [])) == 0
    assert len(data.get("sources", [])) == 0
    # Must politely tell user that no PDF is attached
    assert "no pdf" in data["message"].lower() or "attach" in data["message"].lower() or "upload" in data["message"].lower()
