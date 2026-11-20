import io
import pytest
from fastapi import status
from app.core.config import settings

def test_valid_pdf_upload(client, sample_pdf_bytes):
    """Test 4: Valid PDF upload returns 201 Created and metadata."""
    file_tuple = ("titancloud_sre_incident_runbook_50p.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
    response = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "titancloud_sre_incident_runbook_50p.pdf"
    assert data["status"] == "uploaded"
    assert "successfully" in data["message"].lower()

def test_invalid_file_extension(client, fake_txt_bytes):
    """Test 5a: Non-PDF extension rejected with 400 Bad Request."""
    file_tuple = ("malicious.txt", io.BytesIO(fake_txt_bytes), "text/plain")
    response = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data
    assert "PDF" in data["error"]["message"]

def test_invalid_file_spoofed_pdf_magic_bytes(client, fake_txt_bytes):
    """Test 5b: Fake PDF (named .pdf with non-PDF header bytes) rejected with 400 Bad Request."""
    file_tuple = ("fake_document.pdf", io.BytesIO(fake_txt_bytes), "application/pdf")
    response = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "error" in data
    assert "header verification failed" in data["error"]["message"].lower()

def test_oversized_file_upload(client, monkeypatch):
    """Test 6: File exceeding maximum upload size rejected with 413."""
    # Monkeypatch max upload size to 100KB for test speed
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0.05) # ~50KB

    oversized_bytes = b"%PDF-1.4\n" + (b"A" * (80 * 1024)) # 80KB > 50KB
    file_tuple = ("oversized_runbook.pdf", io.BytesIO(oversized_bytes), "application/pdf")
    response = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    data = response.json()
    assert "error" in data
    assert "exceeds maximum allowed limit" in data["error"]["message"].lower()

def test_document_listing(client, sample_pdf_bytes):
    """Test 7: List documents returns array of uploaded documents."""
    # Upload one first
    file_tuple = ("listing_test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
    client.post("/api/v1/documents/upload", files={"file": file_tuple})

    response = client.get("/api/v1/documents")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(doc["filename"] == "listing_test.pdf" for doc in data)

def test_document_retrieval(client, sample_pdf_bytes):
    """Test 8: Retrieve single document metadata by ID."""
    file_tuple = ("retrieval_test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
    upload_res = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    doc_id = upload_res.json()["document_id"]

    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["filename"] == "retrieval_test.pdf"
    assert data["content_type"] == "application/pdf"
    assert "uploaded_at" in data

def test_document_deletion(client, sample_pdf_bytes):
    """Test 9: Delete document removes metadata and file."""
    file_tuple = ("delete_test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
    upload_res = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    doc_id = upload_res.json()["document_id"]

    # Delete
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == status.HTTP_200_OK
    data = del_res.json()
    assert data["document_id"] == doc_id
    assert data["status"] == "deleted"

    # Confirm it cannot be retrieved anymore
    get_res = client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND

def test_missing_document_handling(client):
    """Test 10: Non-existent document ID returns 404 Not Found."""
    non_existent_id = "non-existent-doc-uuid-9999"
    response = client.get(f"/api/v1/documents/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"

    del_res = client.delete(f"/api/v1/documents/{non_existent_id}")
    assert del_res.status_code == status.HTTP_404_NOT_FOUND

def test_document_stage_endpoint(client, sample_pdf_bytes):
    """Test 11: Document stage endpoint returns real-time granular stage and progress."""
    file_tuple = ("stage_test_runbook.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
    upload_res = client.post("/api/v1/documents/upload", files={"file": file_tuple})
    assert upload_res.status_code == status.HTTP_201_CREATED
    doc_id = upload_res.json()["document_id"]

    stage_res = client.get(f"/api/v1/documents/{doc_id}/stage")
    assert stage_res.status_code == status.HTTP_200_OK
    stage_data = stage_res.json()
    assert stage_data["document_id"] == doc_id
    assert "stage" in stage_data
    assert "progress" in stage_data
    assert "message" in stage_data
