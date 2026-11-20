import re
import logging

logger = logging.getLogger(__name__)

class TextCleaner:
    """
    Cleans extracted PDF text while strictly preserving:
    - CLI commands (kubectl, etcdctl, patronictl, psql, curl, etc.)
    - Error codes (ERR_PG_REPLICA_LAG, 502, 504, Exit Code 137, OOMKilled, etc.)
    - Percentages and SLA thresholds (99.95%, 99.50%, 99.00%, 10%, 25%, 50%)
    - Timelines and escalation contacts (5 minutes, 15 minutes, L1 On-Call, L2 Staff SRE, VP of Infrastructure)
    - Metrics, mathematical formulas, and tabular technical data.
    """

    RUNNING_HEADER_PATTERNS = [
        re.compile(r"^TitanCloud Global Infrastructure\s+[—–-]\s+SRE Operational Runbook\s*$", re.IGNORECASE),
        re.compile(r"^TitanCloud Enterprise SRE\s*&?\s*Incident Response Runbook\s*-\s*Official Reference Corpus\s*$", re.IGNORECASE),
        re.compile(r"^Document Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
        re.compile(r"^Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
        re.compile(r"^Page\s+\d+\s+of\s+\d+\s*\|\s*Confidential Assessment Corpus\s*-\s*Do Not Distribute\s*$", re.IGNORECASE)
    ]

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line_str = line.strip()

            # Skip recognizable running page headers/footers
            if any(pattern.match(line_str) for pattern in self.RUNNING_HEADER_PATTERNS):
                continue

            # Normalize horizontal whitespace within the line (convert tabs and multiple spaces to single space)
            normalized_line = re.sub(r"[ \t]+", " ", line_str)
            cleaned_lines.append(normalized_line)

        # Join back with newlines
        processed_text = "\n".join(cleaned_lines)

        # Fix hyphenated word breaks at line ends (e.g., "distrib-\nuted" -> "distributed")
        processed_text = re.sub(r"([a-zA-Z]{3,})-\n([a-zA-Z]{3,})", r"\1\2", processed_text)

        # Collapse excessive consecutive blank lines (3+ newlines -> 2 newlines)
        processed_text = re.sub(r"\n{3,}", "\n\n", processed_text)

        return processed_text.strip()

text_cleaner = TextCleaner()
