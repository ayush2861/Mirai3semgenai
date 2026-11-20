import re
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile
from app.core.exceptions import FileValidationError, FileSizeExceededError
from app.core.config import settings

PDF_MAGIC_BYTES = b"%PDF-"

def sanitize_filename(filename: str) -> str:
    """
    Strips directory paths and dangerous characters, leaving a clean safe basename.
    """
    if not filename:
        raise FileValidationError("Filename cannot be empty.")
    
    # Extract only the name component (removes any directory traversal attempts)
    clean_name = Path(filename).name
    # Replace non-alphanumeric (except . - _) with underscore
    clean_name = re.sub(r"[^\w\.-]", "_", clean_name)
    # Prevent hidden files
    if clean_name.startswith("."):
        clean_name = "doc" + clean_name
    return clean_name

def generate_stored_filename(original_filename: str) -> str:
    safe_name = sanitize_filename(original_filename)
    return f"{uuid.uuid4().hex}_{safe_name}"

async def validate_pdf_upload(file: UploadFile) -> Tuple[str, bytes]:
    """
    Validates file extension, content-type header, size limits, and PDF magic bytes.
    Returns (sanitized_original_filename, header_bytes).
    """
    if not file.filename:
        raise FileValidationError("No filename provided.")

    safe_name = sanitize_filename(file.filename)

    # 1. Extension check
    if not safe_name.lower().endswith(".pdf"):
        raise FileValidationError(
            f"Invalid file type '{Path(safe_name).suffix}'. Only PDF documents (.pdf) are permitted."
        )

    # 2. Content-type check
    if file.content_type and file.content_type.lower() != "application/pdf":
        raise FileValidationError(
            f"Invalid content type '{file.content_type}'. Expected 'application/pdf'."
        )

    # 3. Read initial chunk to inspect magic bytes
    initial_chunk = await file.read(1024)
    if not initial_chunk or not initial_chunk.startswith(PDF_MAGIC_BYTES):
        raise FileValidationError(
            "File header verification failed: The uploaded file is not a valid PDF document."
        )

    # Reset file cursor for subsequent streaming writes
    await file.seek(0)
    return safe_name, initial_chunk
