from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class TableData(BaseModel):
    page_number: int
    table_index: int
    bbox: List[float] = Field(default_factory=list)
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    markdown: str
    row_count: int
    col_count: int

class HeadingItem(BaseModel):
    level: int = 1
    text: str
    page_number: int
    font_size: float = 0.0
    bbox: Optional[List[float]] = None

class ProcessedPage(BaseModel):
    document_id: str
    document_name: str
    page_number: int = Field(..., description="1-based original PDF page number")
    page_text: str
    raw_text: str
    cleaned_text: str
    headings: List[HeadingItem] = Field(default_factory=list)
    tables: List[TableData] = Field(default_factory=list)
    extraction_method: str = Field("native", description="'native', 'ocr', or 'empty'")
    char_count: int
    word_count: int
    has_images: bool = False
    is_scanned: bool = False
    is_empty: bool = False
    columns_detected: int = 1
    extraction_timestamp: str

class DocumentAnalysis(BaseModel):
    document_id: str
    document_name: str
    total_pages: int
    native_text_pages: int
    ocr_pages: int
    empty_pages: int
    failed_pages: int
    total_characters: int
    total_words: int
    total_tables: int
    total_headings: int
    document_type: str = Field("text_native", description="'text_native', 'scanned', 'hybrid', or 'empty'")
    processing_time_seconds: float = 0.0

class UniversalProcessingResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str
    analysis: DocumentAnalysis
    storage_path: str
    pages: Optional[List[ProcessedPage]] = None

class UniversalProcessingStatus(BaseModel):
    document_id: str
    filename: str
    status: str  # "uploaded", "processing", "processed", "failed"
    analysis: Optional[DocumentAnalysis] = None
    processed_at: Optional[str] = None
    error_message: Optional[str] = None
    storage_path: Optional[str] = None
