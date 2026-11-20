import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
    FileCorruptedError,
    FileEncryptedError
)
from app.schemas.processing import (
    DocumentProcessingResponse,
    DocumentProcessingStatusResponse,
    DocumentChunk,
    ExtractedPage
)
from app.schemas.universal_pdf import (
    UniversalProcessingResponse,
    UniversalProcessingStatus,
    ProcessedPage,
    DocumentAnalysis
)
from app.services.document_service import document_service
from app.services.pdf.pdf_extractor import universal_pdf_extractor
from app.services.text_chunker import text_chunker
from app.services.stage_tracker import document_stage_tracker

logger = logging.getLogger(__name__)

class UniversalProcessingService:
    """
    Universal PDF Processing Orchestrator:
    - Coordinates extraction, OCR, table parsing, cleaning, and chunking.
    - Manages processing state transitions and concurrency checks.
    - Saves structured outputs in backend/data/processed/{document_id}/ (document.json & pages.jsonl).
    - Maintains backward compatibility with legacy endpoints and test suites.
    """

    def __init__(self):
        settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    def _get_document_storage_dir(self, document_id: str) -> Path:
        doc_dir = settings.PROCESSED_DIR / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    def _get_legacy_processed_file(self, document_id: str) -> Path:
        return settings.PROCESSED_DIR / f"{document_id}.json"

    async def process_document(self, document_id: str, force: bool = False) -> DocumentProcessingResponse:
        """
        Executes the universal extraction and chunking pipeline for a document.
        """
        all_meta = document_service._load_metadata()
        if document_id not in all_meta:
            raise DocumentNotFoundError(document_id)

        doc_meta = all_meta[document_id]
        current_status = doc_meta.get("status", "uploaded")

        # Prevent duplicate concurrent processing with stale-lock breaker (3 minutes TTL)
        if current_status == "processing" and not force:
            started_at_str = doc_meta.get("processing_started_at")
            is_stale = False
            if started_at_str:
                try:
                    dt = datetime.fromisoformat(started_at_str)
                    age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
                    if age_seconds > 180:
                        is_stale = True
                        logger.warning(f"Breaking stale processing lock on document {document_id} (age: {age_seconds:.1f}s)")
                except Exception:
                    is_stale = True
            else:
                is_stale = True

            if not is_stale:
                raise DocumentProcessingError(
                    "Document is currently being processed by another worker. Please wait."
                )

        stored_filename = doc_meta.get("stored_filename")
        if not stored_filename:
            raise DocumentProcessingError("Stored file mapping is missing for this document.")

        file_path = settings.UPLOADS_DIR / stored_filename
        if not file_path.exists():
            raise DocumentProcessingError("Uploaded PDF file could not be found on disk.")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Update status to 'processing'
        doc_meta["status"] = "processing"
        doc_meta["processing_started_at"] = now_iso
        doc_meta["error_message"] = None
        doc_meta["failed_stage"] = None
        all_meta[document_id] = doc_meta
        document_service._save_metadata(all_meta)

        try:
            # Stage 1: Validating PDF...
            document_stage_tracker.set_stage(document_id, "validating", 20, "Validating PDF...")

            # Validate openability and encryption upfront
            try:
                import pymupdf
                test_doc = pymupdf.open(str(file_path))
                if test_doc.is_encrypted:
                    if not test_doc.authenticate(""):
                        test_doc.close()
                        raise FileEncryptedError("PDF is password-protected. Please remove the password and try again.")
                if len(test_doc) == 0:
                    test_doc.close()
                    raise FileCorruptedError("PDF document is empty (0 pages).")
                test_doc.close()
            except (FileEncryptedError, FileCorruptedError):
                raise
            except Exception as ve:
                raise FileCorruptedError(f"PDF file is corrupted or unreadable: {str(ve)}")

            # Stage 2: Extracting text...
            document_stage_tracker.set_stage(document_id, "extracting_text", 40, "Extracting text...")

            # 1. Run Universal PDF extraction offloaded to worker thread (prevents event loop starvation)
            processed_pages, analysis = await asyncio.to_thread(
                universal_pdf_extractor.extract_document,
                file_path=file_path,
                document_id=document_id,
                document_name=doc_meta["filename"]
            )

            # Stage 3: Chunking document...
            document_stage_tracker.set_stage(document_id, "chunking_document", 60, "Chunking document...")

            # 2. Chunk text with LangChain RecursiveCharacterTextSplitter
            # Map ProcessedPage to ExtractedPage for text_chunker compatibility
            chunker_input_pages = [
                ExtractedPage(
                    page_number=p.page_number,
                    raw_text=p.page_text,
                    char_count=p.char_count,
                    is_empty=p.is_empty,
                    error=None
                )
                for p in processed_pages
            ]

            chunks = text_chunker.chunk_document(
                document_id=document_id,
                document_name=doc_meta["filename"],
                pages=chunker_input_pages,
                timestamp=now_iso
            )

            # 3. Save modular storage under backend/data/processed/{document_id}/
            doc_dir = self._get_document_storage_dir(document_id)
            doc_json_file = doc_dir / "document.json"
            pages_jsonl_file = doc_dir / "pages.jsonl"

            # Write document.json
            doc_summary_data = {
                "document_id": document_id,
                "document_name": doc_meta["filename"],
                "processed_at": now_iso,
                "analysis": analysis.model_dump(),
                "chunks_count": len(chunks),
                "storage_directory": str(doc_dir)
            }
            with open(doc_json_file, "w", encoding="utf-8") as f:
                json.dump(doc_summary_data, f, indent=2, ensure_ascii=False)

            # Write pages.jsonl (line-by-line JSON)
            with open(pages_jsonl_file, "w", encoding="utf-8") as f:
                for page in processed_pages:
                    f.write(json.dumps(page.model_dump(), ensure_ascii=False) + "\n")

            # 4. Write legacy processed file backend/data/processed/{document_id}.json
            legacy_data = {
                "document_id": document_id,
                "document_name": doc_meta["filename"],
                "processed_at": now_iso,
                "stats": {
                    "total_pages": analysis.total_pages,
                    "extracted_pages": analysis.native_text_pages + analysis.ocr_pages,
                    "empty_pages": analysis.empty_pages,
                    "failed_pages": analysis.failed_pages,
                    "total_characters": analysis.total_characters
                },
                "analysis": analysis.model_dump(),
                "chunks_count": len(chunks),
                "chunks": [c.model_dump() for c in chunks]
            }
            legacy_file = self._get_legacy_processed_file(document_id)
            with open(legacy_file, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f, indent=2, ensure_ascii=False)

            # 5. Update document metadata registry
            doc_meta["status"] = "processed"
            doc_meta["total_pages"] = analysis.total_pages
            doc_meta["extracted_pages"] = analysis.native_text_pages + analysis.ocr_pages
            doc_meta["empty_pages"] = analysis.empty_pages
            doc_meta["failed_pages"] = analysis.failed_pages
            doc_meta["total_chunks"] = len(chunks)
            doc_meta["total_characters"] = analysis.total_characters
            doc_meta["total_tables"] = analysis.total_tables
            doc_meta["total_headings"] = analysis.total_headings
            doc_meta["document_type"] = analysis.document_type
            doc_meta["processed_at"] = now_iso
            doc_meta["error_message"] = None

            all_meta[document_id] = doc_meta
            document_service._save_metadata(all_meta)

            logger.info(
                f"Document {document_id} ({doc_meta['filename']}) processed successfully: "
                f"{analysis.total_pages} pages, {len(chunks)} chunks, {analysis.total_tables} tables."
            )

            return DocumentProcessingResponse(
                document_id=document_id,
                filename=doc_meta["filename"],
                status="processed",
                message="Document processed and chunked successfully.",
                total_pages=analysis.total_pages,
                extracted_pages=analysis.native_text_pages + analysis.ocr_pages,
                empty_pages=analysis.empty_pages,
                failed_pages=analysis.failed_pages,
                total_chunks=len(chunks),
                total_characters=analysis.total_characters,
                chunks=chunks
            )

        except (FileCorruptedError, FileEncryptedError) as e:
            failed_stage = "Validating PDF"
            document_stage_tracker.set_stage(document_id, "failed", 0, "Processing failed", error=e.message, failed_stage=failed_stage)
            doc_meta["status"] = "failed"
            doc_meta["failed_stage"] = failed_stage
            doc_meta["error_message"] = e.message
            all_meta[document_id] = doc_meta
            document_service._save_metadata(all_meta)
            raise e
        except Exception as e:
            logger.error(f"Unexpected processing error for document {document_id}: {e}")
            err_msg = f"An error occurred during text extraction: {str(e)}"
            failed_stage = "Extracting text"
            document_stage_tracker.set_stage(document_id, "failed", 0, "Processing failed", error=err_msg, failed_stage=failed_stage)
            doc_meta["status"] = "failed"
            doc_meta["failed_stage"] = failed_stage
            doc_meta["error_message"] = err_msg
            all_meta[document_id] = doc_meta
            document_service._save_metadata(all_meta)
            raise DocumentProcessingError(doc_meta["error_message"])

    def get_processing_status(self, document_id: str) -> DocumentProcessingStatusResponse:
        all_meta = document_service._load_metadata()
        if document_id not in all_meta:
            raise DocumentNotFoundError(document_id)

        m = all_meta[document_id]
        return DocumentProcessingStatusResponse(
            document_id=m["document_id"],
            filename=m["filename"],
            status=m.get("status", "uploaded"),
            total_pages=m.get("total_pages"),
            extracted_pages=m.get("extracted_pages"),
            empty_pages=m.get("empty_pages"),
            failed_pages=m.get("failed_pages"),
            total_chunks=m.get("total_chunks"),
            total_characters=m.get("total_characters"),
            processed_at=m.get("processed_at"),
            error_message=m.get("error_message")
        )

    def get_processed_chunks(self, document_id: str) -> List[DocumentChunk]:
        all_meta = document_service._load_metadata()
        if document_id not in all_meta:
            raise DocumentNotFoundError(document_id)

        legacy_file = self._get_legacy_processed_file(document_id)
        if not legacy_file.exists():
            return []

        try:
            with open(legacy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [DocumentChunk(**c) for c in data.get("chunks", [])]
        except Exception as e:
            logger.error(f"Failed to load processed chunks for {document_id}: {e}")
            return []

    def get_processed_pages(self, document_id: str) -> List[ProcessedPage]:
        """Loads all processed pages from pages.jsonl."""
        doc_dir = settings.PROCESSED_DIR / document_id
        pages_file = doc_dir / "pages.jsonl"
        if not pages_file.exists():
            return []

        pages: List[ProcessedPage] = []
        try:
            with open(pages_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        pages.append(ProcessedPage(**json.loads(line)))
            return pages
        except Exception as e:
            logger.error(f"Failed to load processed pages for {document_id}: {e}")
            return []

universal_processing_service = UniversalProcessingService()
