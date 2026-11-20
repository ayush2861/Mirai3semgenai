import io
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import pymupdf

from app.main import app
from app.core.config import settings
from app.services.vector.embedding_service import embedding_service
from app.services.vector.chroma_service import chroma_service
from app.services.vector.retrieval_service import hybrid_retrieval_service
from app.services.vector.indexing_service import indexing_service
from app.services.document_service import document_service

client = TestClient(app)

def create_sample_pdf(pages_text: list) -> bytes:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

@pytest.fixture(autouse=True)
def clean_test_collections():
    yield

def test_1_embedding_generation_local_and_normalized():
    """Validates local embedding model loading, dimension, and normalization."""
    assert embedding_service.dimension == 384
    query = "How to triage Kubernetes node memory pressure?"
    vec = embedding_service.embed_query(query, normalize=True)
    assert len(vec) == 384
    
    # Check L2 normalization (sum of squares ~ 1.0)
    norm = sum(x * x for x in vec)
    assert abs(norm - 1.0) < 1e-3

def test_2_end_to_end_indexing_and_status():
    """Tests document upload, indexing into ChromaDB + BM25, and status check."""
    p1 = (
        "PostgreSQL High Availability and Disaster Recovery Runbook.\n"
        "When replica lag exceeds 100ms or error ERR_PG_REPLICA_LAG is detected,\n"
        "the L2 Staff SRE must run patronictl -c /etc/patroni/db.yml switchover.\n"
        "Target availability SLA is 99.95% uptime."
    )
    pdf_bytes = create_sample_pdf([p1])
    
    # Upload as user_alice
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("postgres_runbook.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_alice"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    try:
        # Index document
        index_res = client.post(
            f"/api/v1/documents/{doc_id}/index",
            headers={"X-User-ID": "user_alice"}
        )
        assert index_res.status_code == 200
        idx_data = index_res.json()
        assert idx_data["status"] == "indexed"
        assert idx_data["total_chunks_indexed"] >= 1

        # Check index status
        status_res = client.get(
            f"/api/v1/documents/{doc_id}/index-status",
            headers={"X-User-ID": "user_alice"}
        )
        assert status_res.status_code == 200
        assert status_res.json()["indexed"] is True
        assert status_res.json()["chunk_count"] >= 1

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_alice"})

def test_3_duplicate_indexing_prevention_and_reindex():
    """Ensures duplicate indexing requests do not duplicate chunks unless reindex=True."""
    p1 = "Kafka broker partition rebalance procedures for partition desync."
    pdf_bytes = create_sample_pdf([p1])

    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("kafka_test.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_bob"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        # 1st index
        r1 = client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_bob"})
        assert r1.status_code == 200
        count1 = r1.json()["total_chunks_indexed"]

        # 2nd index without reindex flag -> idempotent return
        r2 = client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_bob"})
        assert r2.status_code == 200
        assert r2.json()["total_chunks_indexed"] == count1
        assert "already indexed" in r2.json()["message"]

        # 3rd index with reindex=True
        r3 = client.post(f"/api/v1/documents/{doc_id}/index?reindex=true", headers={"X-User-ID": "user_bob"})
        assert r3.status_code == 200
        assert r3.json()["total_chunks_indexed"] == count1

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_bob"})

def test_4_exact_keyword_and_error_code_retrieval():
    """Validates exact retrieval of technical error codes and CLI commands via BM25/hybrid."""
    p1 = (
        "Incident Triage: Redis Cluster Memory Exhaustion\n"
        "Error Code: ERR_REDIS_OOM_099\n"
        "Action command: redis-cli --cluster rebalance 10.0.4.15:6379 --threshold 15\n"
        "SLA degraded to 98.50% during failover."
    )
    pdf_bytes = create_sample_pdf([p1])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("redis_oom.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_alice"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_alice"})

        # Search for exact error code
        res_err = client.post(
            "/api/v1/search",
            json={"query": "ERR_REDIS_OOM_099", "mode": "hybrid", "top_k": 3},
            headers={"X-User-ID": "user_alice"}
        )
        assert res_err.status_code == 200
        hits = res_err.json()["results"]
        assert len(hits) >= 1
        assert "ERR_REDIS_OOM_099" in hits[0]["content"]

        # Search for exact CLI command
        res_cmd = client.post(
            "/api/v1/search",
            json={"query": "redis-cli --cluster rebalance", "mode": "bm25", "top_k": 3},
            headers={"X-User-ID": "user_alice"}
        )
        assert res_cmd.status_code == 200
        hits_cmd = res_cmd.json()["results"]
        assert len(hits_cmd) >= 1
        assert "redis-cli" in hits_cmd[0]["content"]

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_alice"})

def test_5_semantic_retrieval_conceptual_queries():
    """Validates conceptual semantic retrieval without exact keyword matching."""
    p1 = (
        "Database replication delays and failover protocols.\n"
        "When replicas fall significantly behind the leader instance,\n"
        "the database cluster should initiate an automated switchover\n"
        "to prevent stale reads and maintain transaction consistency."
    )
    pdf_bytes = create_sample_pdf([p1])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("db_failover.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_alice"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_alice"})

        # Conceptual query with different words
        res = client.post(
            "/api/v1/search",
            json={"query": "How to handle out of sync secondary database nodes?", "mode": "semantic", "top_k": 3},
            headers={"X-User-ID": "user_alice"}
        )
        assert res.status_code == 200
        hits = res.json()["results"]
        assert len(hits) >= 1
        assert "replication delays and failover" in hits[0]["content"]
        assert hits[0]["semantic_score"] is not None

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_alice"})

def test_6_document_isolation_and_security():
    """CRITICAL: Ensures User A can never access or retrieve User B's document chunks."""
    # User Alice uploads confidential payroll runbook
    alice_pdf = create_sample_pdf(["Confidential Executive Payroll Compensation Runbook - Strictly Alice Only."])
    res_a = client.post(
        "/api/v1/documents/upload",
        files={"file": ("alice_payroll.pdf", alice_pdf, "application/pdf")},
        headers={"X-User-ID": "alice"}
    )
    alice_doc_id = res_a.json()["document_id"]

    # User Bob uploads standard SRE runbook
    bob_pdf = create_sample_pdf(["Kubernetes Ingress Gateway Nginx configuration guide for SRE teams."])
    res_b = client.post(
        "/api/v1/documents/upload",
        files={"file": ("bob_ingress.pdf", bob_pdf, "application/pdf")},
        headers={"X-User-ID": "bob"}
    )
    bob_doc_id = res_b.json()["document_id"]

    try:
        # Index both documents under their respective owners
        client.post(f"/api/v1/documents/{alice_doc_id}/index", headers={"X-User-ID": "alice"})
        client.post(f"/api/v1/documents/{bob_doc_id}/index", headers={"X-User-ID": "bob"})

        # Security check 1: Bob tries to index Alice's document -> 403 Forbidden
        hack_index = client.post(f"/api/v1/documents/{alice_doc_id}/index", headers={"X-User-ID": "bob"})
        assert hack_index.status_code == 403

        # Security check 2: Bob tries to delete Alice's index -> 403 Forbidden
        hack_delete = client.delete(f"/api/v1/documents/{alice_doc_id}/index", headers={"X-User-ID": "bob"})
        assert hack_delete.status_code == 403

        # Security check 3: Bob explicitly requests Alice's document ID in search scope -> 403 Forbidden
        hack_search_scoped = client.post(
            "/api/v1/search",
            json={"query": "payroll", "document_ids": [alice_doc_id]},
            headers={"X-User-ID": "bob"}
        )
        assert hack_search_scoped.status_code == 403

        # Security check 4: Bob searches for "payroll compensation" generally -> returns ZERO results (Alice's chunks isolated!)
        bob_search = client.post(
            "/api/v1/search",
            json={"query": "payroll compensation", "mode": "hybrid"},
            headers={"X-User-ID": "bob"}
        )
        assert bob_search.status_code == 200
        assert bob_search.json()["total_results"] == 0
        for r in bob_search.json()["results"]:
            assert "Strictly Alice Only" not in r["content"]
            assert r["document_id"] != alice_doc_id

        # Security check 5: Alice searches for "payroll" -> returns Alice's chunk
        alice_search = client.post(
            "/api/v1/search",
            json={"query": "payroll compensation", "mode": "hybrid"},
            headers={"X-User-ID": "alice"}
        )
        assert alice_search.status_code == 200
        assert alice_search.json()["total_results"] >= 1
        assert "Strictly Alice Only" in alice_search.json()["results"][0]["content"]

    finally:
        client.delete(f"/api/v1/documents/{alice_doc_id}", headers={"X-User-ID": "alice"})
        client.delete(f"/api/v1/documents/{bob_doc_id}", headers={"X-User-ID": "bob"})

def test_7_empty_search_results_and_latency_tracking():
    """Validates response format, empty results handling, and latency tracking."""
    res = client.post(
        "/api/v1/search",
        json={"query": "xyz_unrelated_random_gibberish_9999", "mode": "hybrid"},
        headers={"X-User-ID": "user_empty_test"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] == 0
    assert len(data["results"]) == 0
    assert data["latency_ms"] >= 0.0

def test_8_index_deletion_purges_vectors_and_bm25():
    """Ensures DELETE /{doc_id}/index clears embeddings and BM25 index."""
    pdf_bytes = create_sample_pdf(["Transient test document for deletion testing."])
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("transient.pdf", pdf_bytes, "application/pdf")},
        headers={"X-User-ID": "user_del"}
    )
    doc_id = upload_res.json()["document_id"]

    try:
        # Index
        client.post(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_del"})
        
        # Verify searchable
        s1 = client.post(
            "/api/v1/search",
            json={"query": "transient test document", "mode": "hybrid"},
            headers={"X-User-ID": "user_del"}
        )
        assert s1.json()["total_results"] >= 1

        # Delete index
        del_res = client.delete(f"/api/v1/documents/{doc_id}/index", headers={"X-User-ID": "user_del"})
        assert del_res.status_code == 200

        # Verify no longer searchable
        s2 = client.post(
            "/api/v1/search",
            json={"query": "transient test document", "mode": "hybrid"},
            headers={"X-User-ID": "user_del"}
        )
        assert s2.json()["total_results"] == 0

    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "user_del"})
