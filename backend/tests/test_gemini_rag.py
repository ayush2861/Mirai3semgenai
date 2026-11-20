import io
import pytest
import pymupdf
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai.gemini_provider import gemini_provider
from app.services.ai.prompt_builder import prompt_builder
from app.services.ai.context_builder import context_builder
from app.services.ai.answer_formatter import answer_formatter
from app.services.ai.ai_service import ai_service
from app.schemas.search import SearchResultChunk

client = TestClient(app)

def create_pdf(pages: list) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        p = doc.new_page()
        p.insert_text((50, 72), text, fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b

def test_1_gemini_provider_availability():
    """Verifies Gemini provider initialization and configuration."""
    assert gemini_provider.is_available() is True
    assert gemini_provider.primary_model == "gemini-3.1-flash-lite"

def test_2_prompt_and_system_instructions():
    """Validates system prompt rules and evidence structure formatting."""
    system_inst = prompt_builder.build_system_instruction()
    assert "InfraMind AI" in system_inst
    assert "EVIDENCE" in system_inst
    assert "sufficient information" in system_inst.lower()

    evidence = "--- EVIDENCE CHUNK [1] ---\nSource Document: sre.pdf\nPage Number: 4\nContent: etcd cluster health."
    prompt = prompt_builder.build_rag_prompt("How to check etcd?", evidence)
    assert "=== RETRIEVED DOCUMENT EVIDENCE ===" in prompt
    assert "=== CURRENT USER INQUIRY ===" in prompt
    assert "How to check etcd?" in prompt

def test_3_insufficient_evidence_short_circuit():
    """When query has zero matching evidence in user's documents, returns standard insufficient info notice."""
    res = client.post(
        "/api/v1/chat",
        json={"message": "What is the secret recipe for Belgian waffles?"},
        headers={"X-User-ID": "user_empty_kb"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "couldn't find sufficient information" in data["message"].lower()
    assert len(data["sources"]) == 0

def test_4_grounded_factual_and_numerical_rag_answer():
    """Uploads technical SRE runbook and queries exact numerical thresholds and CLI commands."""
    p1 = (
        "TitanCloud SRE Runbook - Section 3: PostgreSQL High Availability.\n"
        "When replication lag exceeds 100ms or error ERR_PG_REPLICA_LAG is observed,\n"
        "the On-Call SRE must execute:\n"
        "  patronictl -c /etc/patroni/db.yml switchover\n"
        "SLA target is strictly 99.95% uptime."
    )
    pdf_bytes = create_pdf([p1])

    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("postgres_sre.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_rag_tester"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        # Index document into ChromaDB & BM25
        idx_res = client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_rag_tester"})
        assert idx_res.status_code == 200

        # Ask grounded question
        chat_res = client.post(
            "/api/v1/chat",
            json={"message": "What is the command to run when ERR_PG_REPLICA_LAG occurs and what is the SLA threshold?"},
            headers={"X-User-ID": "user_rag_tester"}
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        
        answer_text = chat_data["message"]
        # Verify grounding: model must include CLI command and numbers
        assert "patronictl" in answer_text
        assert "99.95%" in answer_text or "100ms" in answer_text
        
        # Verify citations
        assert len(chat_data["sources"]) >= 1
        assert chat_data["sources"][0]["document_name"] == "postgres_sre.pdf"
        assert chat_data["sources"][0]["page"] == 1

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_rag_tester"})

def test_5_multi_page_synthesis_and_citations():
    """Tests question that requires synthesizing information across multiple pages."""
    p1 = "Module 1: Ingress Gateway Architecture. Envoy proxy handles external TLS termination on Page 1."
    p2 = "Module 2: Mitigation Procedure. When 502 Bad Gateway rate spikes above 5%, run: envoy-cli reload-routes."
    pdf_bytes = create_pdf([p1, p2])

    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("envoy_runbook.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_multipage"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_multipage"})

        chat_res = client.post(
            "/api/v1/chat",
            json={"message": "What does Envoy handle on Page 1 and what is the mitigation command for 502 errors?"},
            headers={"X-User-ID": "user_multipage"}
        )
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert "TLS" in data["message"] or "termination" in data["message"]
        assert "envoy-cli reload-routes" in data["message"]
        assert len(data["sources"]) >= 1

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_multipage"})

def test_6_conversational_history_followup():
    """Validates that follow-up questions leverage prior conversation turns."""
    p1 = "Kubernetes Pod Memory Limits. When a pod is OOMKilled with Exit Code 137, inspect dmesg kernel logs."
    pdf_bytes = create_pdf([p1])

    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("k8s_oom.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_conv"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_conv"})

        # Turn 1
        t1_res = client.post(
            "/api/v1/chat",
            json={"message": "What exit code is associated with OOMKilled pods?"},
            headers={"X-User-ID": "user_conv"}
        )
        assert t1_res.status_code == 200
        conv_id = t1_res.json()["conversation_id"]
        assert "137" in t1_res.json()["message"]

        # Turn 2: Follow-up referring to previous turn
        t2_res = client.post(
            "/api/v1/chat",
            json={"message": "And what logs should I inspect for that exit code?", "conversation_id": conv_id},
            headers={"X-User-ID": "user_conv"}
        )
        assert t2_res.status_code == 200
        assert "dmesg" in t2_res.json()["message"]
        assert t2_res.json()["conversation_id"] == conv_id

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_conv"})

def test_7_chat_document_isolation():
    """Ensures User Bob cannot retrieve or generate answers from User Alice's documents."""
    alice_pdf = create_pdf(["Confidential Secret Financial Compensation: CEO salary is $5,000,000 annually."])
    up_a = client.post(
        "/api/v1/documents/upload",
        files={"file": ("alice_secrets.pdf", alice_pdf, "application/pdf")},
        headers={"X-User-ID": "alice"}
    )
    alice_doc_id = up_a.json()["document_id"]
    client.post(f"/api/v1/documents/{alice_doc_id}/index", headers={"X-User-ID": "alice"})

    try:
        # Bob asks about CEO salary
        bob_chat = client.post(
            "/api/v1/chat",
            json={"message": "What is the CEO salary according to the documents?"},
            headers={"X-User-ID": "bob"}
        )
        assert bob_chat.status_code == 200
        # Bob must get insufficient info, NOT Alice's confidential data
        assert "$5,000,000" not in bob_chat.json()["message"]
        assert "sufficient information" in bob_chat.json()["message"].lower()

    finally:
        client.delete(f"/api/v1/documents/{alice_doc_id}", headers={"X-User-ID": "alice"})
