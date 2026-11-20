import os
import io
import shutil
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture
def sample_pdf_bytes():
    """Generates a valid minimal PDF binary buffer."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n168\n%%EOF\n"

@pytest.fixture
def fake_txt_bytes():
    """Non-PDF plain text buffer."""
    return b"This is not a PDF file. It is plain text."
