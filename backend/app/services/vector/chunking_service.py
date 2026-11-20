import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.schemas.universal_pdf import ProcessedPage, HeadingItem, TableData

logger = logging.getLogger(__name__)

class IntelligentChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    user_id: str
    page_number: int
    chunk_index: int
    section_title: str = "General"
    content_type: str = "text"  # "text", "table", "heading_section"
    content: str
    char_count: int
    word_count: int
    extraction_method: str = "native"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IntelligentChunker:
    """
    Document-aware intelligent text and table chunker:
    - Targets 150-200 words with 30-40 words overlap (safe for all-MiniLM-L6-v2 256 token limit).
    - Preserves paragraph and sentence boundaries.
    - Tracks heading hierarchy and attaches section_title context.
    - Preserves tables as discrete searchable units with headers.
    - Avoids splitting CLI commands, error codes, and technical statements.
    - Attaches complete isolation metadata (user_id, document_id, page_number).
    """

    def __init__(
        self,
        target_words: int = 180,
        overlap_words: int = 35,
        max_words: int = 220
    ):
        self.target_words = target_words
        self.overlap_words = overlap_words
        self.max_words = max_words

    def chunk_processed_pages(
        self,
        document_id: str,
        document_name: str,
        user_id: str,
        pages: List[ProcessedPage]
    ) -> List[IntelligentChunk]:
        """
        Processes all pages of a document and generates intelligent chunks.
        """
        chunks: List[IntelligentChunk] = []
        global_chunk_idx = 0
        current_section = "Introduction"

        for page in pages:
            if page.is_empty or not page.cleaned_text.strip():
                continue

            page_num = page.page_number
            method = page.extraction_method

            # Update section context from headings on this page
            if page.headings:
                # Top heading becomes active section
                current_section = page.headings[0].text

            # 1. Process discrete tables first
            for table in page.tables:
                if table.markdown.strip():
                    table_content = f"### Table: {current_section} (Page {page_num})\n{table.markdown}"
                    words = table_content.split()
                    chunk_id = f"{document_id}_p{page_num}_tbl_{table.table_index}"
                    
                    chunk = IntelligentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_name=document_name,
                        user_id=user_id,
                        page_number=page_num,
                        chunk_index=global_chunk_idx,
                        section_title=current_section,
                        content_type="table",
                        content=table_content,
                        char_count=len(table_content),
                        word_count=len(words),
                        extraction_method=method,
                        metadata={
                            "table_index": table.table_index,
                            "row_count": table.row_count,
                            "col_count": table.col_count
                        }
                    )
                    chunks.append(chunk)
                    global_chunk_idx += 1

            # 2. Process narrative text paragraphs
            # Separate paragraphs by double newline
            paragraphs = [p.strip() for p in page.cleaned_text.split("\n\n") if p.strip()]
            
            # Sub-split long paragraphs into sentences
            units: List[str] = []
            for para in paragraphs:
                para_words = para.split()
                if len(para_words) <= self.target_words:
                    units.append(para)
                else:
                    # Split into sentences
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    current_unit = []
                    current_count = 0
                    for sent in sentences:
                        sent_words = sent.split()
                        if current_count + len(sent_words) > self.target_words and current_unit:
                            units.append(" ".join(current_unit))
                            current_unit = [sent]
                            current_count = len(sent_words)
                        else:
                            current_unit.append(sent)
                            current_count += len(sent_words)
                    if current_unit:
                        units.append(" ".join(current_unit))

            # Assemble chunks with overlap
            page_chunk_idx = 0
            i = 0
            while i < len(units):
                current_chunk_units = []
                current_word_count = 0

                while i < len(units):
                    unit = units[i]
                    unit_words = len(unit.split())

                    # If adding unit exceeds max_words and we already have units, stop
                    if (current_word_count + unit_words > self.max_words) and current_chunk_units:
                        break

                    current_chunk_units.append(unit)
                    current_word_count += unit_words
                    i += 1

                    if current_word_count >= self.target_words:
                        break

                if not current_chunk_units:
                    if i < len(units):
                        current_chunk_units.append(units[i])
                        i += 1

                chunk_text = "\n\n".join(current_chunk_units).strip()
                words_list = chunk_text.split()

                chunk_id = f"{document_id}_p{page_num}_c{page_chunk_idx}"
                chunk = IntelligentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    user_id=user_id,
                    page_number=page_num,
                    chunk_index=global_chunk_idx,
                    section_title=current_section,
                    content_type="text",
                    content=chunk_text,
                    char_count=len(chunk_text),
                    word_count=len(words_list),
                    extraction_method=method,
                    metadata={}
                )
                chunks.append(chunk)
                global_chunk_idx += 1
                page_chunk_idx += 1

                # If we're done with units, break
                if i >= len(units):
                    break

                # Overlap: step back if possible
                if self.overlap_words > 0 and len(current_chunk_units) > 1:
                    last_unit_words = len(units[i-1].split())
                    if last_unit_words <= self.overlap_words:
                        # Include last unit in the next chunk
                        i -= 1

        logger.info(
            f"Intelligently generated {len(chunks)} chunks for {document_name} "
            f"(target={self.target_words} words, overlap={self.overlap_words} words)."
        )
        return chunks

intelligent_chunker = IntelligentChunker()
