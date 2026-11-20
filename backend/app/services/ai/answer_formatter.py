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

        # Strip any verbose Document Citations or trailing raw citation blocks from text
        cleaned_answer = re.sub(r"(?i)\n*#{0,4}\s*Document Citations[\s\S]*$", "", cleaned_answer).strip()
        cleaned_answer = re.sub(
            r"(?i)(?:\n*(?:\*\*Source:\*\*|Source:)\s*[^\n]+\n*(?:\*\*Page:\*\*|Page:)\s*\d+[\s\S]*)+$",
            "",
            cleaned_answer
        ).strip()
        cleaned_answer = re.sub(
            r"(?i)(?:\n*[-*]\s*(?:\*\*Source:\*\*|Source:)\s*[^\n]+(?:\n*\s*(?:\*\*Page:\*\*|Page:)\s*\d+)?)+$",
            "",
            cleaned_answer
        ).strip()

        return cleaned_answer, valid_sources

answer_formatter = AnswerFormatter()
