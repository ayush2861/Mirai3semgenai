"""
Numerical Accuracy & Entity Guard.
Ensures that numerical values, percentages, error codes, currency, and technical thresholds
in generated answers are strictly grounded in retrieved evidence.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)

# Regex patterns for high-risk factual tokens
PERCENTAGE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%\b")
CURRENCY_PATTERN = re.compile(r"\$\d+(?:,\d+)*(?:\.\d+)?(?:[MBKmbk])?\b")
ERROR_CODE_PATTERN = re.compile(r"\b(?:ERR_[A-Z0-9_]+|HTTP\s+[45]\d\d|[45]\d\d\s+error)\b", re.IGNORECASE)
LATENCY_TIME_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|nanoseconds|ns|seconds|sec|minutes|min|hours|hr|days)\b", re.IGNORECASE)
METRIC_UNITS_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:MB|GB|TB|KB|Gbps|Tbps)\b", re.IGNORECASE)


class NumericalGuard:
    """
    Validates that numerical values, currency, percentages, error codes, and time limits
    present in the model answer actually appear in the retrieved evidence text.
    """

    def extract_critical_tokens(self, text: str) -> Dict[str, Set[str]]:
        """Extracts percentages, currencies, error codes, and metric limits from text."""
        return {
            "percentages": set(PERCENTAGE_PATTERN.findall(text)),
            "currencies": set(CURRENCY_PATTERN.findall(text)),
            "error_codes": set(re.findall(r"\bERR_[A-Z0-9_]+\b", text)),
            "time_units": set(LATENCY_TIME_PATTERN.findall(text)),
            "metric_units": set(METRIC_UNITS_PATTERN.findall(text)),
        }

    def verify_numerical_fidelity(
        self,
        answer: str,
        retrieved_evidence_text: str
    ) -> Dict[str, Any]:
        """
        Compares numerical and entity tokens in the answer against evidence text.
        Returns a verification summary and flags any hallucinations.
        """
        answer_tokens = self.extract_critical_tokens(answer)
        evidence_lower = retrieved_evidence_text.lower()

        unsupported_tokens: Dict[str, List[str]] = {}
        total_tokens_checked = 0
        supported_tokens_count = 0

        for category, tokens in answer_tokens.items():
            unsupported_in_cat = []
            for token in tokens:
                total_tokens_checked += 1
                # Check normalized token presence in evidence
                clean_token = token.strip().lower()
                # Also check without leading dollar sign or % if applicable
                token_val = clean_token.replace("$", "").replace("%", "").strip()

                if clean_token in evidence_lower or token_val in evidence_lower:
                    supported_tokens_count += 1
                else:
                    unsupported_in_cat.append(token)

            if unsupported_in_cat:
                unsupported_tokens[category] = unsupported_in_cat

        is_faithful = len(unsupported_tokens) == 0
        accuracy_score = (supported_tokens_count / total_tokens_checked) if total_tokens_checked > 0 else 1.0

        if not is_faithful:
            logger.warning(
                f"Numerical Guard detected ungrounded entities in answer: {unsupported_tokens}"
            )

        return {
            "is_faithful": is_faithful,
            "accuracy_score": accuracy_score,
            "total_critical_tokens": total_tokens_checked,
            "supported_tokens_count": supported_tokens_count,
            "unsupported_tokens": unsupported_tokens
        }


numerical_guard = NumericalGuard()
