from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User search question or keyword query")
    document_ids: Optional[List[str]] = Field(None, description="Optional document IDs scope to search within")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to retrieve")
    mode: str = Field("hybrid", description="Retrieval mode: 'hybrid', 'semantic', or 'bm25'")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters")

class SearchResultChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    section_title: Optional[str] = None
    content_type: str = "text"
    content: str
    score: float
    semantic_score: Optional[float] = None
    bm25_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    query: str
    total_results: int
    mode: str
    results: List[SearchResultChunk]
    latency_ms: float

class IndexDocumentResponse(BaseModel):
    document_id: str
    document_name: str
    status: str
    total_chunks_indexed: int
    collection_name: str
    message: str

class IndexStatusResponse(BaseModel):
    document_id: str
    indexed: bool
    chunk_count: int
    indexed_at: Optional[str] = None
    collection_name: str
