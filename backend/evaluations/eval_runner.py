"""
Evaluation Runner for InfraMind Phase 6 QA & Benchmark.
Executes the 52-question evaluation dataset against all 6 multi-category PDFs.
Computes retrieval metrics, factual accuracy, numerical fidelity, citation accuracy,
unsupported rejection rate, and latency benchmarks.
Outputs structured JSON and human-readable reports.
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure app is in python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.ai.ai_service import ai_service
from app.services.vector.indexing_service import indexing_service
from app.services.document_service import document_service
from app.services.vector.retrieval_service import hybrid_retrieval_service
from evaluations.metrics import (
    calculate_retrieval_metrics,
    evaluate_answer_quality,
    evaluate_citations
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval_runner")

EVAL_USER_ID = "eval_user_phase6"
DATA_DIR = Path(__file__).parent / "data"
GROUND_TRUTH_FILE = DATA_DIR / "ground_truth.json"
REPORT_OUTPUT_FILE = Path(__file__).parent / "evaluation_report.json"


async def setup_and_index_documents(client: TestClient) -> Dict[str, str]:
    """
    Uploads and indexes the 6 evaluation PDF documents under the dedicated eval user.
    Returns mapping of filename -> document_id.
    """
    logger.info("--- Ingesting and Indexing Evaluation PDFs ---")
    doc_mapping = {}

    pdf_files = list(DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"No PDF files found in {DATA_DIR}. Run generate_eval_dataset.py first!")

    for pdf_path in sorted(pdf_files):
        filename = pdf_path.name
        logger.info(f"Uploading {filename} ({pdf_path.stat().st_size} bytes)...")
        with open(pdf_path, "rb") as f:
            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": (filename, f.read(), "application/pdf")},
                headers={"X-User-ID": EVAL_USER_ID}
            )
        assert resp.status_code == 201, f"Failed to upload {filename}: {resp.text}"
        doc_id = resp.json()["document_id"]
        doc_mapping[filename] = doc_id

        # Trigger indexing
        t0 = time.perf_counter()
        idx_resp = client.post(
            f"/api/v1/documents/{doc_id}/index",
            headers={"X-User-ID": EVAL_USER_ID}
        )
        idx_time = time.perf_counter() - t0
        assert idx_resp.status_code == 200, f"Failed to index {filename}: {idx_resp.text}"
        chunk_count = idx_resp.json().get("chunks_indexed", 0)
        logger.info(f"Indexed {filename} -> {chunk_count} chunks in {idx_time:.2f}s (Doc ID: {doc_id})")

    return doc_mapping


async def run_evaluation():
    client = TestClient(app)

    # 1. Index all evaluation PDFs
    doc_mapping = await setup_and_index_documents(client)
    all_doc_ids = list(doc_mapping.values())

    # 2. Load ground truth questions
    with open(GROUND_TRUTH_FILE, "r") as f:
        ground_truth = json.load(f)

    logger.info(f"Loaded {len(ground_truth)} evaluation questions from {GROUND_TRUTH_FILE}.")

    results = []
    category_stats: Dict[str, Dict[str, Any]] = {}

    total_eval_start = time.perf_counter()

    for idx, item in enumerate(ground_truth, start=1):
        q_id = item["id"]
        category = item["category"]
        question = item["question"]
        doc_name = item.get("document")
        expected_pages = item.get("expected_pages", [])
        target_tokens = item.get("target_tokens", [])
        forbidden = item.get("forbidden_hallucinations", [])
        is_supported = item.get("is_supported", True)

        # Target specific doc_id if specified, or all docs
        target_doc_id = [doc_mapping[doc_name]] if doc_name in doc_mapping else all_doc_ids

        logger.info(f"[{idx}/{len(ground_truth)}] [{category.upper()}] Evaluating {q_id}: {question[:60]}...")

        # Execute RAG pipeline via AIService
        t_start = time.perf_counter()
        rag_response = await ai_service.generate_rag_answer(
            question=question,
            conversation_id=f"eval-conv-{q_id}",
            user_id=EVAL_USER_ID,
            document_ids=target_doc_id,
            top_k=5
        )
        total_time_ms = (time.perf_counter() - t_start) * 1000

        generated_answer = rag_response.answer
        retrieved_sources = [s.model_dump() if hasattr(s, "model_dump") else s for s in rag_response.sources]

        # Calculate metrics
        retrieval_m = calculate_retrieval_metrics(retrieved_sources, expected_pages, k=5)
        quality_m = evaluate_answer_quality(generated_answer, target_tokens, forbidden, is_supported)
        citation_m = evaluate_citations(retrieved_sources, generated_answer, expected_pages, is_supported)

        eval_record = {
            "id": q_id,
            "category": category,
            "document": doc_name,
            "question": question,
            "expected_pages": expected_pages,
            "retrieved_sources_count": len(retrieved_sources),
            "retrieval_metrics": retrieval_m,
            "quality_metrics": quality_m,
            "citation_metrics": citation_m,
            "latency_ms": round(total_time_ms, 2),
            "generated_answer_snippet": generated_answer[:160] + "..." if len(generated_answer) > 160 else generated_answer
        }
        results.append(eval_record)

        # Aggregate category statistics
        if category not in category_stats:
            category_stats[category] = {
                "total": 0,
                "correct_answers": 0,
                "recall_sum": 0.0,
                "mrr_sum": 0.0,
                "citation_acc_sum": 0.0,
                "latency_sum": 0.0
            }

        cs = category_stats[category]
        cs["total"] += 1
        if quality_m["is_correct"]:
            cs["correct_answers"] += 1
        cs["recall_sum"] += retrieval_m["recall_at_k"]
        cs["mrr_sum"] += retrieval_m["mrr"]
        cs["citation_acc_sum"] += citation_m["citation_accuracy"]
        cs["latency_sum"] += total_time_ms

    total_eval_duration = time.perf_counter() - total_eval_start

    # Compute overall aggregates
    total_q = len(results)
    total_correct = sum(1 for r in results if r["quality_metrics"]["is_correct"])
    overall_accuracy = (total_correct / total_q) * 100 if total_q > 0 else 0.0

    supported_records = [r for r in results if r["id"] not in [f"eval_{i:03d}" for i in range(43, 53)]]
    unsupported_records = [r for r in results if r["id"] in [f"eval_{i:03d}" for i in range(43, 53)]]

    avg_recall = (sum(r["retrieval_metrics"]["recall_at_k"] for r in supported_records) / len(supported_records)) * 100 if supported_records else 100.0
    avg_mrr = (sum(r["retrieval_metrics"]["mrr"] for r in supported_records) / len(supported_records)) * 100 if supported_records else 100.0
    avg_citation_acc = (sum(r["citation_metrics"]["citation_accuracy"] for r in results) / total_q) * 100 if total_q > 0 else 100.0
    unsupported_rejection_rate = (sum(1 for r in unsupported_records if r["quality_metrics"]["correct_refusal"]) / len(unsupported_records)) * 100 if unsupported_records else 100.0
    avg_latency = sum(r["latency_ms"] for r in results) / total_q if total_q > 0 else 0.0

    numerical_records = [r for r in results if r["category"] == "numerical"]
    numerical_accuracy = (sum(1 for r in numerical_records if r["quality_metrics"]["is_correct"]) / len(numerical_records)) * 100 if numerical_records else 100.0

    # Build final report
    summary_report = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "dataset": "InfraMind Phase 6 Multi-Domain QA Evaluation",
            "eval_user": EVAL_USER_ID,
            "total_documents": len(doc_mapping),
            "documents_tested": list(doc_mapping.keys()),
            "total_questions": total_q,
            "total_runtime_seconds": round(total_eval_duration, 2)
        },
        "overall_metrics": {
            "retrieval_recall_at_5": round(avg_recall, 2),
            "retrieval_mrr": round(avg_mrr, 2),
            "overall_answer_accuracy": round(overall_accuracy, 2),
            "numerical_accuracy": round(numerical_accuracy, 2),
            "citation_accuracy": round(avg_citation_acc, 2),
            "unsupported_question_rejection_rate": round(unsupported_rejection_rate, 2),
            "average_response_time_ms": round(avg_latency, 2)
        },
        "category_breakdown": {
            cat: {
                "questions": s["total"],
                "accuracy_percentage": round((s["correct_answers"] / s["total"]) * 100, 2),
                "avg_recall_at_5": round((s["recall_sum"] / s["total"]) * 100, 2),
                "avg_mrr": round((s["mrr_sum"] / s["total"]) * 100, 2),
                "citation_accuracy": round((s["citation_acc_sum"] / s["total"]) * 100, 2),
                "avg_latency_ms": round(s["latency_sum"] / s["total"], 2)
            }
            for cat, s in category_stats.items()
        },
        "detailed_results": results
    }

    # Save to file
    with open(REPORT_OUTPUT_FILE, "w") as f:
        json.dump(summary_report, f, indent=2)

    logger.info(f"Evaluation report written to {REPORT_OUTPUT_FILE}")

    # Clean up test documents
    logger.info("Cleaning up evaluation documents...")
    for filename, doc_id in doc_mapping.items():
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": EVAL_USER_ID})

    # Print summary table
    print("\n" + "=" * 80)
    print("                     INFRAMIND PHASE 6 EVALUATION REPORT")
    print("=" * 80)
    print(f"Total Documents Tested:         {len(doc_mapping)} PDFs (Multi-category)")
    print(f"Total Questions Evaluated:      {total_q}")
    print(f"Retrieval Recall@5:             {avg_recall:.2f}%")
    print(f"Retrieval MRR:                  {avg_mrr:.2f}%")
    print(f"Overall Answer Accuracy:        {overall_accuracy:.2f}%")
    print(f"Numerical Accuracy:             {numerical_accuracy:.2f}%")
    print(f"Citation Accuracy:              {avg_citation_acc:.2f}%")
    print(f"Unsupported Rejection Rate:     {unsupported_rejection_rate:.2f}%")
    print(f"Average Response Latency:       {avg_latency:.2f} ms")
    print("=" * 80)
    print("Category Breakdown:")
    for cat, data in summary_report["category_breakdown"].items():
        print(f"  - {cat.upper().ljust(18)}: {data['accuracy_percentage']}% correct ({data['questions']} Qs) | Latency: {data['avg_latency_ms']:.1f}ms")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
