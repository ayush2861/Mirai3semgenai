import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pymupdf

from app.core.exceptions import (
    FileCorruptedError,
    FileEncryptedError,
    DocumentProcessingError
)
from app.schemas.universal_pdf import ProcessedPage, DocumentAnalysis
from app.services.pdf.ocr_service import ocr_service
from app.services.pdf.table_extractor import table_extractor
from app.services.pdf.document_analyzer import document_analyzer
from app.services.pdf.text_cleaner import universal_text_cleaner

logger = logging.getLogger(__name__)

class UniversalPDFExtractor:
    """
    Universal PDF extraction engine that handles:
    - Digital text-based PDFs (multi-column, headings, articles, runbooks)
    - Scanned PDFs (automatic OCR fallback via Tesseract)
    - Hybrid PDFs (pages with both digital text and scanned images)
    - Structured tables with Markdown reconstruction
    - Encrypted / corrupted PDF safety handling
    """

    def extract_document(
        self,
        file_path: Path,
        document_id: str,
        document_name: str
    ) -> Tuple[List[ProcessedPage], DocumentAnalysis]:
        """
        Extracts, classifies, and structures content from a PDF document.
        """
        start_time = time.time()
        if not file_path.exists():
            raise DocumentProcessingError(f"Target PDF file does not exist: {file_path}")

        try:
            doc = pymupdf.open(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open PDF file {file_path.name}: {e}")
            raise FileCorruptedError(f"Unable to read or parse PDF file: {str(e)}")

        try:
            if doc.is_encrypted:
                # Attempt default empty password
                if not doc.authenticate(""):
                    raise FileEncryptedError("The PDF document is password-protected and cannot be processed.")

            total_pages = len(doc)
            raw_pages_info: List[Dict[str, Any]] = []

            # Pass 1: Extraction & Layout Analysis
            for page_idx in range(total_pages):
                page_number = page_idx + 1
                try:
                    page = doc[page_idx]

                    # Extract layout, headings, and ordered reading blocks
                    layout_info = document_analyzer.analyze_page_layout(page, page_number)
                    tables = table_extractor.extract_tables_from_page(page, page_number)

                    ordered_blocks = layout_info["ordered_blocks"]
                    native_text = "\n\n".join(ordered_blocks) if ordered_blocks else page.get_text("text") or ""
                    native_char_count = len(native_text.strip())

                    has_images = layout_info["has_images"]
                    drawing_count = len(page.get_drawings())

                    extraction_method = "native"
                    is_scanned = False
                    is_empty = False
                    extracted_text = native_text

                    # Trigger OCR condition: low text count (< 50 chars) and page contains images/drawings
                    if native_char_count < 50 and (has_images or drawing_count > 0):
                        if ocr_service.is_available():
                            logger.info(f"Page {page_number} has low digital text ({native_char_count} chars). Triggering OCR...")
                            ocr_text = ocr_service.ocr_page(page)
                            if len(ocr_text.strip()) > native_char_count:
                                extracted_text = ocr_text
                                extraction_method = "ocr"
                                is_scanned = True
                                logger.info(f"Page {page_number}: OCR succeeded with {len(ocr_text)} characters.")
                        else:
                            logger.warning(f"Page {page_number}: OCR requested but Tesseract not available.")

                    if len(extracted_text.strip()) == 0:
                        is_empty = True
                        extraction_method = "empty"

                    raw_pages_info.append({
                        "page_number": page_number,
                        "raw_text": extracted_text,
                        "headings": layout_info["headings"],
                        "tables": tables,
                        "columns_detected": layout_info["columns_detected"],
                        "has_images": has_images,
                        "is_scanned": is_scanned,
                        "is_empty": is_empty,
                        "extraction_method": extraction_method,
                        "failed": False,
                        "error": None
                    })

                except Exception as page_err:
                    logger.error(f"Error processing page {page_number} of {document_name}: {page_err}")
                    raw_pages_info.append({
                        "page_number": page_number,
                        "raw_text": "",
                        "headings": [],
                        "tables": [],
                        "columns_detected": 1,
                        "has_images": False,
                        "is_scanned": False,
                        "is_empty": True,
                        "extraction_method": "failed",
                        "failed": True,
                        "error": str(page_err)
                    })

            # Pass 2: Discover recurring headers/footers dynamically
            all_raw_texts = [p["raw_text"] for p in raw_pages_info]
            dynamic_headers = universal_text_cleaner.identify_recurring_headers_footers(all_raw_texts)

            # Pass 3: Text Cleaning & Table Integration
            now_iso = datetime.now(timezone.utc).isoformat()
            processed_pages: List[ProcessedPage] = []

            native_pages_count = 0
            ocr_pages_count = 0
            empty_pages_count = 0
            failed_pages_count = 0
            total_characters = 0
            total_words = 0
            total_tables = 0
            total_headings = 0

            for p_info in raw_pages_info:
                raw_text = p_info["raw_text"]
                cleaned_text = universal_text_cleaner.clean_page_text(raw_text, dynamic_headers)

                # Append table markdown representations if tables are present on page
                # so chunks capture both running narrative and tabular metrics
                tables = p_info["tables"]
                table_mds = [t.markdown for t in tables if t.markdown.strip()]
                
                final_page_text = cleaned_text
                if table_mds:
                    # Append cleanly separated tables
                    table_section = "\n\n### Tables\n" + "\n\n".join(table_mds)
                    final_page_text = (cleaned_text + table_section).strip()

                char_count = len(final_page_text)
                word_count = len(final_page_text.split())

                # Statistics updates
                method = p_info["extraction_method"]
                if p_info["failed"]:
                    failed_pages_count += 1
                elif p_info["is_empty"] and char_count == 0:
                    empty_pages_count += 1
                elif method == "ocr":
                    ocr_pages_count += 1
                else:
                    native_pages_count += 1

                total_characters += char_count
                total_words += word_count
                total_tables += len(tables)
                total_headings += len(p_info["headings"])

                processed_pages.append(ProcessedPage(
                    document_id=document_id,
                    document_name=document_name,
                    page_number=p_info["page_number"],
                    page_text=final_page_text,
                    raw_text=raw_text,
                    cleaned_text=cleaned_text,
                    headings=p_info["headings"],
                    tables=tables,
                    extraction_method=method,
                    char_count=char_count,
                    word_count=word_count,
                    has_images=p_info["has_images"],
                    is_scanned=p_info["is_scanned"],
                    is_empty=p_info["is_empty"] and char_count == 0,
                    columns_detected=p_info["columns_detected"],
                    extraction_timestamp=now_iso
                ))

            processing_time = time.time() - start_time

            analysis = document_analyzer.classify_document(
                document_id=document_id,
                document_name=document_name,
                total_pages=total_pages,
                native_pages=native_pages_count,
                ocr_pages=ocr_pages_count,
                empty_pages=empty_pages_count,
                failed_pages=failed_pages_count,
                total_chars=total_characters,
                total_words=total_words,
                total_tables=total_tables,
                total_headings=total_headings,
                processing_time=processing_time
            )

            logger.info(
                f"Completed universal extraction for {document_name} ({total_pages} pages, "
                f"type={analysis.document_type}, tables={total_tables}, headings={total_headings}, "
                f"time={processing_time:.2f}s)"
            )
            return processed_pages, analysis

        finally:
            doc.close()

universal_pdf_extractor = UniversalPDFExtractor()
