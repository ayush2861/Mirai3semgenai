from typing import Dict, Any, Optional
from datetime import datetime, timezone


class DocumentStageTracker:
    """
    Tracks real-time granular processing events for PDF documents:
    1. uploading (10%) -> 'Uploading PDF...'
    2. validating (20%) -> 'Validating PDF...'
    3. extracting_text (40%) -> 'Extracting text...'
    4. chunking_document (60%) -> 'Chunking document...'
    5. generating_embeddings (80%) -> 'Generating embeddings...'
    6. indexing_document (95%) -> 'Indexing document...'
    7. ready (100%) -> 'Document ready!'
    or failed (0%) -> 'Processing failed' (with failed_stage and exact error reason)
    """

    def __init__(self):
        self._stages: Dict[str, Dict[str, Any]] = {}

    def set_stage(
        self,
        document_id: str,
        stage: str,
        progress: int,
        message: str,
        error: Optional[str] = None,
        failed_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        info = {
            "document_id": document_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "error": error,
            "failed_stage": failed_stage,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self._stages[document_id] = info
        return info

    def get_stage(self, document_id: str, default_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if document_id in self._stages:
            return self._stages[document_id]

        if default_meta:
            if default_meta.get("is_indexed"):
                return {
                    "document_id": document_id,
                    "stage": "ready",
                    "progress": 100,
                    "message": "Document ready!",
                    "error": None,
                    "failed_stage": None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            if default_meta.get("status") == "failed":
                return {
                    "document_id": document_id,
                    "stage": "failed",
                    "progress": 0,
                    "message": "Processing failed",
                    "error": default_meta.get("error_message") or "Document processing failed.",
                    "failed_stage": default_meta.get("failed_stage"),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            if default_meta.get("status") == "processing":
                return {
                    "document_id": document_id,
                    "stage": "extracting_text",
                    "progress": 40,
                    "message": "Extracting text...",
                    "error": None,
                    "failed_stage": None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

        return {
            "document_id": document_id,
            "stage": "uploading",
            "progress": 10,
            "message": "Uploading PDF...",
            "error": None,
            "failed_stage": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }


document_stage_tracker = DocumentStageTracker()
