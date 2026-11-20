import re
import unicodedata
import logging
from typing import List, Set, Dict
from collections import Counter

logger = logging.getLogger(__name__)

class UniversalTextCleaner:
    """
    Normalizes extracted PDF text for any document type (runbooks, research papers,
    reports, policies) while strictly preserving:
    - Percentages (99.95%, 99.5%, 10%)
    - Numerical thresholds and units (15m, 100ms, 10Gi, 32GB)
    - Technical commands (kubectl, curl, etcdctl, patronictl, psql, systemctl)
    - Command flags (--namespace, -n, -v, --all)
    - Error codes (ERR_PG_REPLICA_LAG, 502, 504, Exit Code 137, OOMKilled)
    - URLs, file paths, IP addresses, and tabular data.
    """

    GENERIC_PAGE_PATTERNS = [
        re.compile(r"^\s*page\s+\d+\s*(?:of|/)\s*\d+\s*$", re.IGNORECASE),
        re.compile(r"^\s*-\s*\d+\s*-\s*$"),
        re.compile(r"^\s*document\s+page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
        re.compile(r"^\s*\d+\s*\|\s*page\s*$", re.IGNORECASE),
        re.compile(r"^\s*page\s+\d+\s*$", re.IGNORECASE),
    ]

    def normalize_unicode(self, text: str) -> str:
        """Applies NFKC normalization and removes non-printable control characters."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        # Strip zero-width spaces and BOM
        normalized = normalized.replace("\u200b", "").replace("\ufeff", "")
        return normalized

    def clean_page_text(self, text: str, dynamic_headers: Set[str] = None) -> str:
        """
        Cleans a single page text string.
        """
        if not text:
            return ""

        headers_to_remove = dynamic_headers or set()
        text = self.normalize_unicode(text)
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line_str = line.strip()

            if not line_str:
                cleaned_lines.append("")
                continue

            # Check generic page number footers
            if any(pat.match(line_str) for pat in self.GENERIC_PAGE_PATTERNS):
                continue

            # Check recurring document headers/footers
            if line_str.lower() in headers_to_remove:
                continue

            # Collapse internal tab/spaces without destroying indentation
            # If line starts with spaces (like code indentation), preserve up to 4 spaces
            leading_spaces = len(line) - len(line.lstrip(" "))
            indent = " " * min(leading_spaces, 4) if leading_spaces > 1 else ""
            normalized_content = re.sub(r"[ \t]+", " ", line_str)
            cleaned_lines.append(indent + normalized_content)

        processed_text = "\n".join(cleaned_lines)

        # Fix hyphenated word breaks across lines (e.g., "distrib-\nuted" -> "distributed")
        # Ensure we do NOT un-hyphenate command flags (e.g., "--\nnamespace") or negative numbers
        processed_text = re.sub(r"(?<!-)\b([a-zA-Z]{3,})-\n([a-zA-Z]{3,})\b", r"\1\2", processed_text)

        # Collapse 3+ consecutive newlines into 2 (paragraph break)
        processed_text = re.sub(r"\n{3,}", "\n\n", processed_text)

        return processed_text.strip()

    def identify_recurring_headers_footers(self, raw_page_texts: List[str]) -> Set[str]:
        """
        Dynamically discovers recurring headers and footers across pages.
        Identifies non-empty top and bottom lines that appear across >= 3 pages
        (or > 30% of pages) without requiring hardcoded strings.
        """
        if len(raw_page_texts) < 3:
            return set()

        top_lines = []
        bottom_lines = []

        for pt in raw_page_texts:
            lines = [l.strip().lower() for l in pt.split("\n") if l.strip()]
            if lines:
                top_lines.append(lines[0])
            if len(lines) > 1:
                bottom_lines.append(lines[-1])

        threshold = max(3, int(len(raw_page_texts) * 0.30))
        recurring: Set[str] = set()

        for line, count in Counter(top_lines).items():
            if count >= threshold and len(line) > 3 and not line.isdigit():
                recurring.add(line)

        for line, count in Counter(bottom_lines).items():
            if count >= threshold and len(line) > 3 and not line.isdigit():
                recurring.add(line)

        logger.debug(f"Identified {len(recurring)} recurring headers/footers across {len(raw_page_texts)} pages.")
        return recurring

universal_text_cleaner = UniversalTextCleaner()
