from typing import Dict, Any, Optional
from datetime import datetime, timezone


class DocumentStageTracker:
    """
    Tracks real-time granular processing events for PDF documents:
    1. uploading (15%) -> 'Uploading PDF...'
    2. extracting_text (30%) -> 'Extracting text...'
    3. analyzing_pages (48%) -> 'Analyzing pages...'
    4. chunking_document (62%) -> 'Chunking document...'
    5. generating_embeddings (78%) -> 'Generating embeddings...'
    6. indexing_document (92%) -> 'Indexing document...'
    7. ready (100%) -> 'Ready to chat'
    or failed (0%) -> 'Processing failed'
    """

    def __init__(self):
        self._stages: Dict[str, Dict[str, Any]] = {}

    def set_stage(
        self,
        document_id: str,
        stage: str,
        progress: int,
        message: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        info = {
            "document_id": document_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "error": error,
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
                    "message": "Ready to chat",
                    "error": None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            if default_meta.get("status") == "failed":
                return {
                    "document_id": document_id,
                    "stage": "failed",
                    "progress": 0,
                    "message": "Processing failed",
                    "error": default_meta.get("error_message"),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            if default_meta.get("status") == "processing":
                return {
                    "document_id": document_id,
                    "stage": "extracting_text",
                    "progress": 30,
                    "message": "Extracting text...",
                    "error": None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

        return {
            "document_id": document_id,
            "stage": "uploading",
            "progress": 15,
            "message": "Uploading PDF...",
            "error": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }


document_stage_tracker = DocumentStageTracker()
