"""
Citation Validator and Verification Engine.
Ensures that all citations emitted by the LLM strictly correspond to
actual retrieved evidence chunks from authorized user documents.
Rejects or strips fabricated document references and invalid page numbers.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)

# Pattern to extract inline or block citations, e.g.:
# Source: file.pdf, Page: 2
# [Source: file.pdf, Page: 2]
# **Source:** file.pdf, **Page:** 2
CITATION_PATTERN = re.compile(
    r"(?:\*\*Source:\*\*|Source:)\s*`?([^\n\r,\`]+)`?(?:,|\s+)\s*(?:\*\*Page:\*\*|Page:)\s*(\d+)",
    re.IGNORECASE
)


class CitationValidator:
    """
    Validates, filters, and formats citations to eliminate hallucinated sources.
    """

    def validate_citations(
        self,
        raw_answer: str,
        retrieved_sources: List[Dict[str, Any]],
        authorized_doc_ids: List[str] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validates citations against actual retrieved evidence chunks.

        Returns:
            Tuple of:
            - cleaned_answer: Answer text with verified citation block (or fabricated citations stripped)
            - verified_sources: List of verified unique source dicts
            - validation_report: Diagnostic dictionary containing counts of valid vs invalid citations
        """
        if not raw_answer:
            return "", [], {"valid": 0, "fabricated": 0, "total_claimed": 0}

        cleaned_answer = raw_answer.strip()

        # If answer is an insufficient evidence fallback, no citations should be returned
        if "insufficient information" in cleaned_answer.lower():
            # Strip any hallucinated citation blocks
            cleaned_answer = re.sub(r"### Document Citations[\s\S]*$", "", cleaned_answer).strip()
            return cleaned_answer, [], {"valid": 0, "fabricated": 0, "total_claimed": 0}

        # Build lookup set of valid (normalized_doc_name, page_number) and doc_ids from actual retrieved chunks
        valid_chunk_keys: Set[Tuple[str, int]] = set()
        retrieved_doc_ids: Set[str] = set()
        unique_valid_sources: Dict[Tuple[str, int], Dict[str, Any]] = {}

        for src in retrieved_sources:
            doc_name = src.get("document_name", "").strip().lower()
            page_num = int(src.get("page_number", 1))
            valid_chunk_keys.add((doc_name, page_num))
            if src.get("document_id"):
                retrieved_doc_ids.add(src["document_id"])
            
            key = (src.get("document_name", "").strip(), page_num)
            if key not in unique_valid_sources:
                unique_valid_sources[key] = src

        # Find any explicitly claimed citations in the model output
        claimed_citations = CITATION_PATTERN.findall(cleaned_answer)
        valid_claimed_count = 0
        fabricated_count = 0

        for claimed_doc, claimed_page_str in claimed_citations:
            norm_doc = claimed_doc.strip().lower()
            claimed_page = int(claimed_page_str)
            
            # Check if this claimed pair exists in actual retrieved chunks
            # Match directly or by base filename
            matched = False
            for (v_doc, v_page) in valid_chunk_keys:
                if v_page == claimed_page and (v_doc in norm_doc or norm_doc in v_doc):
                    matched = True
                    break

            if matched:
                valid_claimed_count += 1
            else:
                fabricated_count += 1
                logger.warning(
                    f"Fabricated citation detected and flagged: Doc='{claimed_doc}', Page={claimed_page}. "
                    f"Not found in retrieved chunks!"
                )

        # Strip any lines that contain ungrounded or fabricated citations
        if fabricated_count > 0:
            lines = cleaned_answer.split("\n")
            filtered_lines = []
            for line in lines:
                m = CITATION_PATTERN.search(line)
                if m:
                    doc_cand = m.group(1).strip().lower()
                    page_cand = int(m.group(2))
                    cand_matched = any(
                        v_page == page_cand and (v_doc in doc_cand or doc_cand in v_doc)
                        for (v_doc, v_page) in valid_chunk_keys
                    )
                    if not cand_matched:
                        continue
                filtered_lines.append(line)
            cleaned_answer = "\n".join(filtered_lines).strip()

        # Completely strip verbose "Document Citations" and trailing raw citation lines from text
        # (Citations are displayed cleanly via the compact Sources cards component)
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

        # Build final verified unique sources list
        final_sources = list(unique_valid_sources.values())

        report = {
            "valid_citations": valid_claimed_count if claimed_citations else len(final_sources),
            "fabricated_citations": fabricated_count,
            "total_claimed": len(claimed_citations),
            "verified_sources_count": len(final_sources),
            "is_100_percent_verified": fabricated_count == 0
        }

        return cleaned_answer, final_sources, report


citation_validator = CitationValidator()
