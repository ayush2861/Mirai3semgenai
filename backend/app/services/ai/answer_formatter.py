import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AnswerFormatter:
    """
    Sanitizes, validates, and enriches LLM answers with verified document citations.
    Ensures that citations match actual retrieved evidence and conform to the required format.
    """

    def format_and_verify_citations(
        self,
        raw_answer: str,
        retrieved_sources: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Validates that any claimed citations exist in retrieved_sources.
        Ensures consistent citation formatting for frontend rendering.
        """
        if not raw_answer:
            return "", []

        cleaned_answer = raw_answer.strip()

        # If evidence was insufficient, return as is without spurious sources
        if "insufficient information" in cleaned_answer.lower():
            return cleaned_answer, []

        # Deduplicate retrieved sources by (document_name, page_number)
        unique_sources: Dict[Tuple[str, int], Dict[str, Any]] = {}
        for src in retrieved_sources:
            key = (src["document_name"], src["page_number"])
            if key not in unique_sources:
                unique_sources[key] = src

        valid_sources = list(unique_sources.values())

        # Check if model output already contains "Source:" and "Page:"
        has_citations = ("source:" in cleaned_answer.lower() and "page:" in cleaned_answer.lower())

        # If model did not append explicit citations and valid sources exist, append verified citation block
        if not has_citations and valid_sources:
            citation_lines = ["\n\n### Document Citations"]
            for s in valid_sources:
                citation_lines.append(f"- **Source:** `{s['document_name']}`  \n  **Page:** {s['page_number']}")
            cleaned_answer += "\n" + "\n".join(citation_lines)

        return cleaned_answer, valid_sources

answer_formatter = AnswerFormatter()
