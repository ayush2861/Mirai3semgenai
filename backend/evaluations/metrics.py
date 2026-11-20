"""
Evaluation Metrics Computation for InfraMind RAG QA (Phase 6).
Calculates:
- Retrieval: Recall@K, Precision@K, Mean Reciprocal Rank (MRR), Hit Rate.
- Answer Quality: Factual Accuracy, Numerical Accuracy, Forbidden Hallucinations.
- Citations: Citation Validity Rate (% citations referencing true evidence).
- Rejection: Unsupported Question Rejection Rate (safe refusal without hallucination).
"""

from typing import List, Dict, Any, Set, Tuple


def calculate_retrieval_metrics(
    retrieved_sources: List[Dict[str, Any]],
    expected_pages: List[int],
    k: int = 5
) -> Dict[str, float]:
    """
    Computes Recall@K, Precision@K, and MRR for retrieved chunks against expected pages.
    """
    if not expected_pages:
        # If question is unsupported, retrieval metrics are not applicable
        return {"recall_at_k": 1.0, "precision_at_k": 1.0, "mrr": 1.0, "hit": 1.0}

    top_sources = retrieved_sources[:k]
    if not top_sources:
        return {"recall_at_k": 0.0, "precision_at_k": 0.0, "mrr": 0.0, "hit": 0.0}

    expected_set = set(expected_pages)
    retrieved_pages = [int(s.get("page_number", -1)) for s in top_sources]

    # Hits: retrieved pages that are in expected_pages
    hits = [p for p in retrieved_pages if p in expected_set]
    unique_hits = set(hits)

    recall = len(unique_hits) / len(expected_set) if expected_set else 1.0
    precision = len(hits) / len(top_sources) if top_sources else 0.0
    hit_rate = 1.0 if hits else 0.0

    # MRR: reciprocal rank of first relevant page
    mrr = 0.0
    for idx, page in enumerate(retrieved_pages, start=1):
        if page in expected_set:
            mrr = 1.0 / idx
            break

    return {
        "recall_at_k": round(recall, 4),
        "precision_at_k": round(precision, 4),
        "mrr": round(mrr, 4),
        "hit": hit_rate
    }


def evaluate_answer_quality(
    generated_answer: str,
    target_tokens: List[str],
    forbidden_hallucinations: List[str],
    is_supported: bool
) -> Dict[str, Any]:
    """
    Evaluates factual correctness, numerical accuracy, and hallucination absence.
    """
    answer_lower = generated_answer.lower()

    # 1. Unsupported Question Evaluation
    if not is_supported:
        correct_refusal = (
            "sufficient information" in answer_lower or
            "not found" in answer_lower or
            "cannot find" in answer_lower or
            "does not contain" in answer_lower
        )
        # Check that no forbidden hallucinations appeared
        hallucination_detected = any(fh.lower() in answer_lower for fh in forbidden_hallucinations)
        return {
            "is_correct": correct_refusal and not hallucination_detected,
            "correct_refusal": correct_refusal,
            "hallucination_detected": hallucination_detected,
            "token_coverage": 1.0 if correct_refusal else 0.0,
            "missing_tokens": []
        }

    # 2. Supported Question Evaluation
    # Check for presence of required target tokens (exact facts, codes, numbers)
    missing_tokens = []
    for token in target_tokens:
        clean_tok = token.strip().lower()
        if clean_tok not in answer_lower:
            missing_tokens.append(token)

    token_coverage = (
        (len(target_tokens) - len(missing_tokens)) / len(target_tokens)
        if target_tokens else 1.0
    )

    # Check for forbidden hallucinations
    hallucination_detected = any(fh.lower() in answer_lower for fh in forbidden_hallucinations)

    # Consider correct if coverage >= 80% (or all primary tokens present) and no forbidden hallucinations
    is_correct = (token_coverage >= 0.8) and (not hallucination_detected)

    return {
        "is_correct": is_correct,
        "token_coverage": round(token_coverage, 4),
        "missing_tokens": missing_tokens,
        "hallucination_detected": hallucination_detected
    }


def evaluate_citations(
    retrieved_sources: List[Dict[str, Any]],
    generated_answer: str,
    expected_pages: List[int],
    is_supported: bool
) -> Dict[str, Any]:
    """
    Evaluates whether generated citations are valid and grounded in retrieved chunks.
    """
    if not is_supported:
        # Unsupported queries should have 0 citations
        has_citations = "### document citations" in generated_answer.lower()
        return {
            "citation_accuracy": 1.0 if not has_citations else 0.0,
            "valid_citation_count": 0,
            "invalid_citation_count": 1 if has_citations else 0
        }

    # For supported questions, verify that cited pages match retrieved sources
    retrieved_pages = {int(s.get("page_number", -1)) for s in retrieved_sources}
    valid_count = 0
    invalid_count = 0

    # Look for page citations in text
    import re
    cited_pages = set(map(int, re.findall(r"\*\*Page:\*\*\s*(\d+)", generated_answer)))

    for p in cited_pages:
        if p in retrieved_pages:
            valid_count += 1
        else:
            invalid_count += 1

    total_cited = valid_count + invalid_count
    accuracy = (valid_count / total_cited) if total_cited > 0 else 1.0

    return {
        "citation_accuracy": round(accuracy, 4),
        "valid_citation_count": valid_count,
        "invalid_citation_count": invalid_count,
        "cited_pages": list(cited_pages)
    }
