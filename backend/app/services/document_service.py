import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import (
    FileValidationError,
    FileSizeExceededError,
    DocumentNotFoundError
)
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentMetadata,
    DocumentDeleteResponse
)
from app.utils.file_validation import (
    validate_pdf_upload,
    generate_stored_filename
)

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.metadata_file = settings.DATA_DIR / "documents_index.json"
        self._ensure_storage()

    def _ensure_storage(self):
        settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.metadata_file.exists():
            self._save_metadata({})

    def _load_metadata(self) -> Dict[str, dict]:
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load document metadata: {e}")
        return {}

    def _save_metadata(self, data: Dict[str, dict]):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def save_uploaded_file(self, file: UploadFile, user_id: str = "default_user") -> DocumentUploadResponse:
        # 1. Validate extension, mime, and magic bytes
        clean_filename, _ = await validate_pdf_upload(file)

        # 2. Generate unique storage filename to prevent collisions
        doc_id = uuid.uuid4().hex
        stored_filename = f"{doc_id}_{clean_filename}"
        target_path = settings.UPLOADS_DIR / stored_filename

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB chunks

        try:
            with open(target_path, "wb") as buffer:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)

                    if total_bytes > settings.max_upload_size_bytes:
                        raise FileSizeExceededError(
                            f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                        )
                    buffer.write(chunk)
        except Exception as e:
            # Clean up partial file on failure
            if target_path.exists():
                target_path.unlink()
            raise e

        # 3. Record metadata
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata_entry = {
            "document_id": doc_id,
            "filename": clean_filename,
            "stored_filename": stored_filename,
            "size_bytes": total_bytes,
            "content_type": "application/pdf",
            "status": "uploaded",
            "user_id": user_id,
            "uploaded_at": now_iso
        }

        all_meta = self._load_metadata()
        all_meta[doc_id] = metadata_entry
        self._save_metadata(all_meta)

        logger.info(f"Successfully uploaded document: {clean_filename} (ID: {doc_id}, size: {total_bytes} bytes)")

        return DocumentUploadResponse(
            document_id=doc_id,
            filename=clean_filename,
            status="uploaded",
            message="Document uploaded successfully"
        )

    def list_documents(self) -> List[DocumentMetadata]:
        all_meta = self._load_metadata()
        return [
            DocumentMetadata(
                document_id=m["document_id"],
                filename=m["filename"],
                size_bytes=m["size_bytes"],
                content_type=m.get("content_type", "application/pdf"),
                status=m.get("status", "uploaded"),
                uploaded_at=m["uploaded_at"]
            )
            for m in all_meta.values()
        ]

    def get_document(self, document_id: str) -> DocumentMetadata:
        all_meta = self._load_metadata()
        if document_id not in all_meta:
            raise DocumentNotFoundError(document_id)
        m = all_meta[document_id]
        return DocumentMetadata(
            document_id=m["document_id"],
            filename=m["filename"],
            size_bytes=m["size_bytes"],
            content_type=m.get("content_type", "application/pdf"),
            status=m.get("status", "uploaded"),
            uploaded_at=m["uploaded_at"]
        )

    def delete_document(self, document_id: str, user_id: Optional[str] = None) -> DocumentDeleteResponse:
        all_meta = self._load_metadata()
        if document_id not in all_meta:
            raise DocumentNotFoundError(document_id)

        doc_info = all_meta[document_id]
        if user_id and doc_info.get("user_id", settings.DEFAULT_USER_ID) != user_id:
            from app.core.exceptions import UnauthorizedAccessError
            raise UnauthorizedAccessError(f"You do not have permission to delete document '{document_id}'.")

        doc_info = all_meta.pop(document_id)
        self._save_metadata(all_meta)

        # Remove physical file safely
        stored_filename = doc_info.get("stored_filename")
        if stored_filename:
            file_path = settings.UPLOADS_DIR / stored_filename
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete physical file {file_path}: {e}")

        # Also purge vector embeddings and BM25 index
        try:
            from app.services.vector.chroma_service import chroma_service
            from app.services.vector.retrieval_service import hybrid_retrieval_service
            chroma_service.delete_document(document_id)
            hybrid_retrieval_service.bm25_manager.remove_document(
                doc_info.get("user_id", settings.DEFAULT_USER_ID),
                document_id
            )
        except Exception as ve:
            logger.warning(f"Could not purge vector index for {document_id}: {ve}")

        logger.info(f"Deleted document: {document_id} ({doc_info.get('filename')})")
        return DocumentDeleteResponse(
            document_id=document_id,
            status="deleted",
            message="Document deleted successfully"
        )

document_service = DocumentService()
