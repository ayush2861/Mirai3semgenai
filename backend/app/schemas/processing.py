from typing import List, Optional
from pydantic import BaseModel, Field

class ExtractedPage(BaseModel):
    page_number: int = Field(..., description="1-based original PDF page number")
    raw_text: str
    char_count: int
    is_empty: bool = False
    error: Optional[str] = None

class DocumentChunk(BaseModel):
    chunk_id: str = Field(..., description="Unique ID for this chunk")
    document_id: str
    document_name: str
    page_number: int = Field(..., description="Original PDF page number")
    chunk_index: int = Field(..., description="0-based index of this chunk within the page/document")
    content: str
    char_count: int
    extraction_timestamp: str

class DocumentProcessingStatusResponse(BaseModel):
    document_id: str
    filename: str
    status: str  # "uploaded", "processing", "processed", "failed"
    total_pages: Optional[int] = None
    extracted_pages: Optional[int] = None
    empty_pages: Optional[int] = None
    failed_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    total_characters: Optional[int] = None
    processed_at: Optional[str] = None
    error_message: Optional[str] = None

class DocumentProcessingResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str
    total_pages: int
    extracted_pages: int
    empty_pages: int
    failed_pages: int
    total_chunks: int
    total_characters: int
    chunks: Optional[List[DocumentChunk]] = None
