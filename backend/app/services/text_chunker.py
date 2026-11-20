import logging
from datetime import datetime, timezone
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.schemas.processing import ExtractedPage, DocumentChunk

logger = logging.getLogger(__name__)

class TextChunker:
    """
    Chunks document page texts using LangChain's RecursiveCharacterTextSplitter.
    Preserves exact 1-based page numbers and complete document metadata.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False
        )

    def chunk_document(
        self,
        document_id: str,
        document_name: str,
        pages: List[ExtractedPage],
        timestamp: str = None
    ) -> List[DocumentChunk]:
        """
        Takes extracted and cleaned pages and splits them into chunks with metadata.
        """
        chunks: List[DocumentChunk] = []
        now_iso = timestamp or datetime.now(timezone.utc).isoformat()
        global_chunk_idx = 0

        for page in pages:
            if page.is_empty or not page.raw_text.strip():
                continue

            page_text = page.raw_text.strip()
            # Split this page's text
            page_splits = self.splitter.split_text(page_text)

            for page_chunk_idx, split_content in enumerate(page_splits):
                chunk_id = f"{document_id}_p{page.page_number}_c{page_chunk_idx}"
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page.page_number,
                    chunk_index=global_chunk_idx,
                    content=split_content,
                    char_count=len(split_content),
                    extraction_timestamp=now_iso
                )
                chunks.append(chunk)
                global_chunk_idx += 1

        logger.info(
            f"Generated {len(chunks)} chunks for document {document_name} ({document_id}) "
            f"across {len(pages)} pages (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})."
        )
        return chunks

text_chunker = TextChunker()
