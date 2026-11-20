import io
import json
import pytest
from pathlib import Path
from fastapi import status
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app.core.config import settings
from app.services.pdf_extractor import pdf_extractor
from app.services.text_cleaner import text_cleaner
from app.services.text_chunker import text_chunker, TextChunker
from app.schemas.processing import ExtractedPage

def create_test_pdf_buffer(pages_content: list) -> bytes:
    """Helper to dynamically generate in-memory PDFs with specific text or empty pages."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    for idx, content in enumerate(pages_content):
        if content:
            textobject = c.beginText(50, 750)
            textobject.setFont("Helvetica", 10)
            for line in content.split("\n"):
                textobject.textLine(line)
            c.drawText(textobject)
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def test_1_valid_pdf_extraction(tmp_path):
    """Test 1: Valid PDF extraction successfully extracts text from a PDF."""
    pdf_bytes = create_test_pdf_buffer(["TitanCloud System Operations\nVersion 1.0"])
    pdf_path = tmp_path / "test_extract.pdf"
    pdf_path.write_bytes(pdf_bytes)

    pages, stats = pdf_extractor.extract_pdf(pdf_path)
    assert len(pages) == 1
    assert "TitanCloud System Operations" in pages[0].raw_text
    assert pages[0].page_number == 1
    assert pages[0].is_empty is False
    assert stats["total_pages"] == 1
    assert stats["extracted_pages"] == 1

def test_2_extraction_across_multiple_pages(tmp_path):
    """Test 2: Extraction across multiple pages parses all pages in order."""
    page1 = "Page 1: Kubernetes Cluster Outage Overview"
    page2 = "Page 2: Patroni PostgreSQL High Availability"
    page3 = "Page 3: Envoy API Gateway Circuit Breakers"

    pdf_bytes = create_test_pdf_buffer([page1, page2, page3])
    pdf_path = tmp_path / "multi_page.pdf"
    pdf_path.write_bytes(pdf_bytes)

    pages, stats = pdf_extractor.extract_pdf(pdf_path)
    assert len(pages) == 3
    assert stats["total_pages"] == 3
    assert "Kubernetes" in pages[0].raw_text
    assert "Patroni" in pages[1].raw_text
    assert "Envoy" in pages[2].raw_text

def test_3_correct_page_number_preservation(tmp_path):
    """Test 3: Page numbers start at 1 and match original index sequence."""
    pdf_bytes = create_test_pdf_buffer(["First", "Second", "Third", "Fourth"])
    pdf_path = tmp_path / "numbered.pdf"
    pdf_path.write_bytes(pdf_bytes)

    pages, _ = pdf_extractor.extract_pdf(pdf_path)
    for idx, page in enumerate(pages):
        assert page.page_number == idx + 1

def test_4_empty_page_detection(tmp_path):
    """Test 4: Detects empty pages and flags is_empty correctly."""
    pdf_bytes = create_test_pdf_buffer(["Content on page 1", "", "Content on page 3"])
    pdf_path = tmp_path / "with_empty.pdf"
    pdf_path.write_bytes(pdf_bytes)

    pages, stats = pdf_extractor.extract_pdf(pdf_path)
    assert len(pages) == 3
    assert pages[0].is_empty is False
    assert pages[1].is_empty is True
    assert pages[2].is_empty is False
    assert stats["empty_pages"] == 1
    assert stats["extracted_pages"] == 2

def test_5_corrupted_pdf_handling(tmp_path):
    """Test 5: Corrupted PDF file raises FileCorruptedError."""
    from app.core.exceptions import FileCorruptedError

    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"%PDF-1.4\nBROKEN_GARBAGE_BYTES_THAT_CANNOT_PARSE\x00\xFF")

    with pytest.raises(FileCorruptedError):
        pdf_extractor.extract_pdf(corrupt_file)

def test_6_text_cleaning():
    """Test 6: Cleans text while strictly preserving CLI commands, error codes, and metrics."""
    raw_input = (
        "TitanCloud Global Infrastructure — SRE Operational Runbook\n"
        "Page 4 of 50\n"
        "Kubernetes   Cluster   Outage\n\n\n\n\n"
        "Execute command:\n"
        "kubectl get nodes -o wide\n"
        "ETCDCTL_API=3 etcdctl --endpoints=https://10.200.0.11:2379 endpoint health\n"
        "Alert: HTTP 502 and 504 errors detected. Availability dropped to 99.85% (SLA threshold: 99.99%).\n"
        "Replication delay of 12000ms triggers exit code 137 (OOMKilled)."
    )

    cleaned = text_cleaner.clean_text(raw_input)

    # 1. Boilerplate header/footer removed
    assert "TitanCloud Global Infrastructure — SRE Operational Runbook" not in cleaned
    assert "Page 4 of 50" not in cleaned

    # 2. Excessive whitespace normalized
    assert "Kubernetes Cluster Outage" in cleaned
    assert "   " not in cleaned

    # 3. Excessive newlines collapsed
    assert "\n\n\n" not in cleaned

    # 4. Critical SRE technical info strictly preserved
    assert "kubectl get nodes -o wide" in cleaned
    assert "ETCDCTL_API=3 etcdctl --endpoints=https://10.200.0.11:2379 endpoint health" in cleaned
    assert "502" in cleaned
    assert "504" in cleaned
    assert "99.85%" in cleaned
    assert "99.99%" in cleaned
    assert "137" in cleaned
    assert "OOMKilled" in cleaned

def test_7_chunk_size_limits():
    """Test 7: Chunk sizes do not exceed configured limits."""
    chunker = TextChunker(chunk_size=300, chunk_overlap=50)
    long_content = "Kubernetes etcd quorum failure requires defragmentation and compaction. " * 20
    test_page = ExtractedPage(page_number=1, raw_text=long_content, char_count=len(long_content), is_empty=False)

    chunks = chunker.chunk_document("doc-1", "test.pdf", [test_page])
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 350

def test_8_chunk_overlap():
    """Test 8: Successive chunks contain expected overlapping text."""
    chunker = TextChunker(chunk_size=90, chunk_overlap=30)
    text = (
        "Kubernetes worker node containment and memory eviction policy under severe resource "
        "pressure requires immediate scaling and container restart mitigation."
    )
    test_page = ExtractedPage(page_number=1, raw_text=text, char_count=len(text), is_empty=False)
    chunks = chunker.chunk_document("doc-test", "test.pdf", [test_page])

    assert len(chunks) >= 2
    # Verify exact overlap between chunk 0 and chunk 1
    tail_sample = chunks[0].content[-25:]
    assert tail_sample in chunks[1].content

def test_9_metadata_preservation():
    """Test 9: Every chunk preserves document_id, document_name, page_number, chunk_id, etc."""
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)
    content = "PostgreSQL Patroni failover execution."
    p1 = ExtractedPage(page_number=14, raw_text=content, char_count=len(content), is_empty=False)
    chunks = chunker.chunk_document("doc-sre-99", "patroni_runbook.pdf", [p1])

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.document_id == "doc-sre-99"
    assert chunk.document_name == "patroni_runbook.pdf"
    assert chunk.page_number == 14
    assert chunk.chunk_id == "doc-sre-99_p14_c0"
    assert chunk.chunk_index == 0
    assert chunk.char_count == len(content)
    assert chunk.extraction_timestamp is not None

def test_10_document_processing_endpoint(client):
    """Test 10: POST /api/v1/documents/{document_id}/process executes pipeline."""
    pdf_bytes = create_test_pdf_buffer([
        "Page 1: Critical Kafka consumer lag triage.",
        "Page 2: Scale consumer group replicas to 16."
    ])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("kafka_runbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    doc_id = upload_res.json()["document_id"]

    # Process
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == status.HTTP_200_OK
    data = proc_res.json()
    assert data["document_id"] == doc_id
    assert data["status"] == "processed"
    assert data["total_pages"] == 2
    assert data["extracted_pages"] == 2
    assert data["total_chunks"] >= 2

    # Verify processed file exists on disk
    processed_path = settings.PROCESSED_DIR / f"{doc_id}.json"
    assert processed_path.exists()

def test_11_processing_status_endpoint(client):
    """Test 11: GET /api/v1/documents/{document_id}/processing-status reports state."""
    pdf_bytes = create_test_pdf_buffer(["Redis cache sentinel split-brain remediation."])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("redis_runbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = upload_res.json()["document_id"]

    # Status before processing: uploaded
    st1 = client.get(f"/api/v1/documents/{doc_id}/processing-status")
    assert st1.status_code == status.HTTP_200_OK
    assert st1.json()["status"] == "uploaded"

    # Process
    client.post(f"/api/v1/documents/{doc_id}/process")

    # Status after processing: processed
    st2 = client.get(f"/api/v1/documents/{doc_id}/processing-status")
    assert st2.status_code == status.HTTP_200_OK
    assert st2.json()["status"] == "processed"
    assert st2.json()["total_pages"] == 1
    assert st2.json()["total_chunks"] >= 1

def test_12_missing_document_handling(client):
    """Test 12: Processing non-existent document returns 404."""
    fake_id = "missing-document-id-404"
    res = client.post(f"/api/v1/documents/{fake_id}/process")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    res_st = client.get(f"/api/v1/documents/{fake_id}/processing-status")
    assert res_st.status_code == status.HTTP_404_NOT_FOUND

def test_13_duplicate_processing(client):
    """Test 13: Reprocessing an already processed document is idempotent and safe."""
    pdf_bytes = create_test_pdf_buffer(["BGP routing anomaly and AS-path prepending."])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("bgp_runbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = upload_res.json()["document_id"]

    # First run
    p1 = client.post(f"/api/v1/documents/{doc_id}/process")
    assert p1.status_code == status.HTTP_200_OK
    assert p1.json()["status"] == "processed"

    # Second run (re-processing)
    p2 = client.post(f"/api/v1/documents/{doc_id}/process")
    assert p2.status_code == status.HTTP_200_OK
    assert p2.json()["status"] == "processed"
    assert p2.json()["total_chunks"] == p1.json()["total_chunks"]

def test_14_extraction_failure_handling(client, tmp_path):
    """Test 14: Extraction failures update status to failed with clean error message."""
    pdf_bytes = create_test_pdf_buffer(["Temporary valid file for upload"])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("corrupt_target.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = upload_res.json()["document_id"]

    # Overwrite the physical file with corrupt data
    from app.services.document_service import document_service
    meta = document_service._load_metadata()
    stored_name = meta[doc_id]["stored_filename"]
    (settings.UPLOADS_DIR / stored_name).write_bytes(b"CORRUPTED_NON_PARSEABLE_DATA_12345")

    # Processing should catch and handle gracefully
    res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    data = res.json()
    assert "error" in data

    # Verify status changed to failed
    st = client.get(f"/api/v1/documents/{doc_id}/processing-status")
    assert st.json()["status"] == "failed"
    assert st.json()["error_message"] is not None
