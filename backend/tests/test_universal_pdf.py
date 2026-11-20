import io
import json
import pytest
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app
from app.services.pdf.ocr_service import ocr_service
from app.services.pdf.table_extractor import table_extractor
from app.services.pdf.document_analyzer import document_analyzer
from app.services.pdf.text_cleaner import universal_text_cleaner
from app.services.pdf.pdf_extractor import universal_pdf_extractor
from app.services.pdf.processing_service import universal_processing_service
from app.services.document_service import document_service
from app.core.config import settings

client = TestClient(app)

def create_in_memory_pdf(pages_text: list) -> bytes:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_table_pdf() -> bytes:
    """Creates a PDF with a structured table using drawing lines."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Insert table text
    page.insert_text((50, 50), "Cluster Node Inventory", fontsize=16)
    
    # Draw table grid and content
    # Headers
    page.insert_text((55, 100), "Node Name", fontsize=10)
    page.insert_text((180, 100), "Role", fontsize=10)
    page.insert_text((300, 100), "Status", fontsize=10)
    page.insert_text((420, 100), "CPU Usage", fontsize=10)
    
    # Row 1
    page.insert_text((55, 130), "k8s-master-01", fontsize=10)
    page.insert_text((180, 130), "ControlPlane", fontsize=10)
    page.insert_text((300, 130), "Ready", fontsize=10)
    page.insert_text((420, 130), "14.5%", fontsize=10)

    # Row 2
    page.insert_text((55, 160), "k8s-worker-01", fontsize=10)
    page.insert_text((180, 160), "Worker", fontsize=10)
    page.insert_text((300, 160), "Ready", fontsize=10)
    page.insert_text((420, 160), "82.1%", fontsize=10)

    # Horizontal and vertical grid lines for PyMuPDF table finder
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(50, 80, 500, 180))
    shape.draw_line(pymupdf.Point(50, 115), pymupdf.Point(500, 115))
    shape.draw_line(pymupdf.Point(50, 145), pymupdf.Point(500, 145))
    shape.draw_line(pymupdf.Point(170, 80), pymupdf.Point(170, 180))
    shape.draw_line(pymupdf.Point(290, 80), pymupdf.Point(290, 180))
    shape.draw_line(pymupdf.Point(410, 80), pymupdf.Point(410, 180))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_scanned_image_pdf(text: str = "SCANNED INVOICE 99.95% RELIABILITY") -> bytes:
    """Creates a PDF containing an image of text, simulating a scanned document."""
    # Create an image with text
    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((30, 80), text, fill="black")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    doc = pymupdf.open()
    page = doc.new_page(width=600, height=300)
    page.insert_image(pymupdf.Rect(50, 50, 550, 250), stream=img_bytes)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_two_column_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)
    # Left column (x=50 to 250)
    page.insert_text((50, 100), "Column 1 Top Section", fontsize=11)
    page.insert_text((50, 200), "Column 1 Bottom Section", fontsize=11)
    # Right column (x=350 to 550)
    page.insert_text((350, 100), "Column 2 Top Section", fontsize=11)
    page.insert_text((350, 200), "Column 2 Bottom Section", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_ocr_service_availability_and_extraction():
    """Validates OCR service availability and scanned page extraction."""
    assert ocr_service.is_available() is True
    
    # Test OCR extraction on a synthesized image page
    scanned_pdf = create_scanned_image_pdf("INCIDENT P1 OUTAGE CRITICAL")
    doc = pymupdf.open(stream=scanned_pdf, filetype="pdf")
    page = doc[0]
    extracted_ocr = ocr_service.ocr_page(page)
    doc.close()

    assert "INCIDENT" in extracted_ocr
    assert "OUTAGE" in extracted_ocr

def test_table_extractor_markdown():
    """Validates table extraction and Markdown table reconstruction."""
    table_pdf = create_table_pdf()
    doc = pymupdf.open(stream=table_pdf, filetype="pdf")
    page = doc[0]
    tables = table_extractor.extract_tables_from_page(page, page_number=1)
    doc.close()

    assert len(tables) >= 1
    table = tables[0]
    assert table.page_number == 1
    assert table.col_count >= 3
    assert "---" in table.markdown
    assert "Ready" in table.markdown or "k8s" in table.markdown

def test_two_column_reading_order():
    """Verifies that multi-column layouts are sorted left column first, then right column."""
    two_col_pdf = create_two_column_pdf()
    doc = pymupdf.open(stream=two_col_pdf, filetype="pdf")
    page = doc[0]
    cols, ordered_blocks = document_analyzer.order_reading_blocks(page, page.rect.width)
    doc.close()

    assert cols == 2
    assert len(ordered_blocks) >= 2
    # Ensure Column 1 sections appear before Column 2 sections
    text_content = " ".join(ordered_blocks)
    idx_col1_bottom = text_content.find("Column 1 Bottom Section")
    idx_col2_top = text_content.find("Column 2 Top Section")
    assert idx_col1_bottom < idx_col2_top

def test_heading_detection():
    """Verifies heading level classification based on font size and weight."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 80), "TitanOps Incident Runbook", fontsize=24) # Heading 1
    page.insert_text((50, 140), "Symptom & Triage Checklist", fontsize=16) # Heading 2
    page.insert_text((50, 200), "Standard body paragraph describing the mitigation steps.", fontsize=10) # Body
    
    layout = document_analyzer.analyze_page_layout(page, page_number=1)
    doc.close()

    headings = layout["headings"]
    assert len(headings) >= 2
    assert any(h.level == 1 and "TitanOps Incident Runbook" in h.text for h in headings)
    assert any(h.level == 2 and "Symptom & Triage Checklist" in h.text for h in headings)

def test_universal_text_cleaner_preserves_technical_tokens():
    """Ensures CLI commands, flags, error codes, and percentages are untouched."""
    raw = (
        "Run the following command:\n"
        "  kubectl get pods -n prod-cluster --selector=app=ingress-gateway\n"
        "If error ERR_PG_REPLICA_LAG is observed (lag > 100ms or SLA < 99.95%),\n"
        "execute patronictl -c /etc/patroni/db.yml switchover.\n"
        "Document Page 1 of 5\n"
    )
    cleaned = universal_text_cleaner.clean_page_text(raw)
    
    assert "kubectl get pods -n prod-cluster --selector=app=ingress-gateway" in cleaned
    assert "ERR_PG_REPLICA_LAG" in cleaned
    assert "99.95%" in cleaned
    assert "100ms" in cleaned
    assert "patronictl -c /etc/patroni/db.yml switchover" in cleaned
    assert "Document Page 1 of 5" not in cleaned

def test_universal_dynamic_header_footer_discovery():
    """Ensures repeated headers across multiple pages are discovered and stripped."""
    pages = [
        "Confidential Internal Policy - Do Not Distribute\nSection 1: Security\nPage 1",
        "Confidential Internal Policy - Do Not Distribute\nSection 2: Access Control\nPage 2",
        "Confidential Internal Policy - Do Not Distribute\nSection 3: Incident Escalation\nPage 3",
        "Confidential Internal Policy - Do Not Distribute\nSection 4: Post-Mortem\nPage 4"
    ]
    recurring = universal_text_cleaner.identify_recurring_headers_footers(pages)
    assert "confidential internal policy - do not distribute" in recurring

    cleaned = universal_text_cleaner.clean_page_text(pages[0], dynamic_headers=recurring)
    assert "Confidential Internal Policy" not in cleaned
    assert "Section 1: Security" in cleaned

def test_hybrid_document_classification():
    """Verifies classification of hybrid document containing both native text and scanned image."""
    doc = pymupdf.open()
    # Page 1: Native text
    p1 = doc.new_page()
    p1.insert_text((50, 100), "Chapter 1: Kubernetes Architecture Overview and Controller Manager.", fontsize=12)
    # Page 2: Scanned image only
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "SCANNED RUNBOOK PAGE", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    p2 = doc.new_page(width=500, height=300)
    p2.insert_image(pymupdf.Rect(50, 50, 450, 250), stream=buf.getvalue())
    
    temp_pdf = settings.UPLOADS_DIR / "test_hybrid.pdf"
    doc.save(str(temp_pdf))
    doc.close()

    try:
        pages, analysis = universal_pdf_extractor.extract_document(temp_pdf, "doc_hybrid", "hybrid.pdf")
        assert len(pages) == 2
        assert analysis.document_type == "hybrid"
        assert analysis.native_text_pages >= 1
        assert analysis.ocr_pages >= 1
    finally:
        if temp_pdf.exists():
            temp_pdf.unlink()

def test_modular_storage_and_pages_api_endpoint():
    """Validates end-to-end upload -> universal process -> disk storage -> GET /pages."""
    pdf_bytes = create_table_pdf()
    # 1. Upload
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("inventory_table.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    try:
        # 2. Process
        proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
        assert proc_res.status_code == 200
        data = proc_res.json()
        assert data["status"] == "processed"
        assert data["total_pages"] == 1

        # 3. Check modular disk storage
        doc_dir = settings.PROCESSED_DIR / doc_id
        assert doc_dir.exists()
        assert (doc_dir / "document.json").exists()
        assert (doc_dir / "pages.jsonl").exists()

        with open(doc_dir / "document.json", "r") as f:
            doc_meta = json.load(f)
            assert doc_meta["document_id"] == doc_id
            assert "analysis" in doc_meta

        # 4. GET /api/v1/documents/{document_id}/pages
        pages_res = client.get(f"/api/v1/documents/{doc_id}/pages")
        assert pages_res.status_code == 200
        pages_data = pages_res.json()
        assert len(pages_data) == 1
        assert pages_data[0]["page_number"] == 1
        assert len(pages_data[0]["tables"]) >= 1

    finally:
        # Clean up
        client.delete(f"/api/v1/documents/{doc_id}")
