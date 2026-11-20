import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pymupdf

from app.core.exceptions import (
    FileCorruptedError,
    FileEncryptedError,
    DocumentProcessingError
)
from app.schemas.processing import ExtractedPage

logger = logging.getLogger(__name__)

class PDFExtractor:
    """
    Extracts text page by page from PDF documents using PyMuPDF (fitz).
    Preserves original 1-based page numbers and detects empty pages.
    """

    def extract_pdf(self, file_path: Path) -> Tuple[List[ExtractedPage], Dict[str, Any]]:
        """
        Extracts all pages from the target PDF file.
        Returns a tuple of (list of ExtractedPage, extraction_statistics).
        """
        if not file_path.exists():
            raise DocumentProcessingError("Target PDF file does not exist on storage.")

        try:
            doc = pymupdf.open(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open PDF file {file_path.name}: {e}")
            raise FileCorruptedError(f"Unable to read PDF file: {str(e)}")

        try:
            if doc.is_encrypted:
                # Attempt empty password authentication
                if not doc.authenticate(""):
                    raise FileEncryptedError("The PDF document is password-protected and cannot be processed.")

            total_pages = len(doc)
            extracted_pages: List[ExtractedPage] = []
            empty_count = 0
            failed_count = 0
            total_chars = 0

            for page_idx in range(total_pages):
                page_number = page_idx + 1
                try:
                    page = doc[page_idx]
                    page_text = page.get_text("text") or ""
                    cleaned_strip = page_text.strip()
                    is_empty = len(cleaned_strip) == 0

                    if is_empty:
                        empty_count += 1

                    char_count = len(page_text)
                    total_chars += char_count

                    extracted_pages.append(ExtractedPage(
                        page_number=page_number,
                        raw_text=page_text,
                        char_count=char_count,
                        is_empty=is_empty,
                        error=None
                    ))
                except Exception as page_err:
                    logger.warning(f"Error extracting page {page_number} from {file_path.name}: {page_err}")
                    failed_count += 1
                    extracted_pages.append(ExtractedPage(
                        page_number=page_number,
                        raw_text="",
                        char_count=0,
                        is_empty=True,
                        error=str(page_err)
                    ))

            stats = {
                "total_pages": total_pages,
                "extracted_pages": total_pages - failed_count - empty_count,
                "empty_pages": empty_count,
                "failed_pages": failed_count,
                "total_characters": total_chars
            }

            logger.info(
                f"Extracted {total_pages} pages from {file_path.name}: "
                f"{stats['extracted_pages']} with text, {empty_count} empty, {failed_count} failed."
            )
            return extracted_pages, stats

        finally:
            doc.close()

pdf_extractor = PDFExtractor()
