import logging
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.schemas.search import SearchResultChunk

logger = logging.getLogger(__name__)

class ContextBuilder:
    """
    Assembles, deduplicates, and limits retrieved chunks into structured evidence blocks
    for LLM prompt grounding.
    """

    def __init__(
        self,
        max_chunks: int = None,
        max_chars: int = None
    ):
        self.max_chunks = max_chunks or settings.MAX_CONTEXT_CHUNKS
        self.max_chars = max_chars or settings.MAX_CONTEXT_CHARS

    def build_evidence_context(
        self,
        chunks: List[SearchResultChunk]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Organizes retrieved chunks into formatted evidence text and structured source references.
        """
        if not chunks:
            return "", []

        evidence_parts: List[str] = []
        structured_sources: List[Dict[str, Any]] = []
        seen_chunks = set()
        total_chars = 0

        for idx, chunk in enumerate(chunks[:self.max_chunks]):
            if chunk.chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk.chunk_id)

            content_snippet = chunk.content.strip()
            chunk_length = len(content_snippet)

            # Enforce max character budget
            if total_chars + chunk_length > self.max_chars and evidence_parts:
                logger.info(f"Context budget reached ({total_chars} chars). Truncating remaining chunks.")
                break

            total_chars += chunk_length

            evidence_block = (
                f"--- EVIDENCE CHUNK [{len(evidence_parts) + 1}] ---\n"
                f"Source Document: {chunk.document_name}\n"
                f"Page Number: {chunk.page_number}\n"
                f"Section: {chunk.section_title or 'General'}\n"
                f"Content:\n{content_snippet}\n"
            )
            evidence_parts.append(evidence_block)

            structured_sources.append({
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "page": chunk.page_number,
                "page_number": chunk.page_number,
                "section": chunk.section_title or "General",
                "content_type": chunk.content_type,
                "snippet": content_snippet[:220] + "..." if len(content_snippet) > 220 else content_snippet,
                "score": chunk.score
            })

        formatted_evidence = "\n".join(evidence_parts)
        return formatted_evidence, structured_sources

context_builder = ContextBuilder()
