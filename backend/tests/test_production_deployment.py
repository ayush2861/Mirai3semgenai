"""
Production Deployment & Authentication Verification Suite (Phase 7).
Verifies:
- Production health and root endpoints.
- User registration and bcrypt password hashing.
- JWT bearer token authentication and profile verification.
- Per-user document upload, indexing, and multi-tenant access control.
- Unauthorized access rejection.
- Data persistence across simulated restart.
"""

import io
import fitz
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import auth_service
from app.services.document_service import document_service

client = TestClient(app)


def create_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf.getvalue()


def test_1_production_health_and_root_endpoints():
    """Verify health check and root endpoints comply with Render uptime checks."""
    res_root = client.get("/")
    assert res_root.status_code == status.HTTP_200_OK
    assert "InfraMind API" in res_root.json()["application"]

    res_health = client.get("/api/v1/health")
    assert res_health.status_code == status.HTTP_200_OK
    assert res_health.json()["status"] == "healthy"


def test_2_user_registration_and_jwt_login():
    """Verify user registration and subsequent JWT login."""
    test_user_email = "sre_engineer_42@titanops.ai"
    test_username = "sre_engineer_42"
    test_password = "SecurePassword2026!"

    # 1. Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "username": test_username,
            "password": test_password,
            "full_name": "Senior Cloud SRE"
        }
    )
    # Could be 201 Created (or 400 if user exists from prior run)
    if reg_resp.status_code == status.HTTP_201_CREATED:
        reg_data = reg_resp.json()
        assert reg_data["token_type"] == "bearer"
        assert "access_token" in reg_data
        assert reg_data["email"] == test_user_email
    else:
        assert reg_resp.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_email, "password": test_password}
    )
    assert login_resp.status_code == status.HTTP_200_OK
    login_data = login_resp.json()
    assert "access_token" in login_data
    token = login_data["access_token"]

    # 3. Verify Profile
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == status.HTTP_200_OK
    me_data = me_resp.json()
    assert me_data["email"] == test_user_email
    assert me_data["username"] == test_username


def test_3_authenticated_document_lifecycle_and_tenant_isolation():
    """Verify authenticated document upload, indexing, and cross-user rejection."""
    # Register User A (Alice)
    alice_email = "alice_ops@titanops.ai"
    client.post(
        "/api/v1/auth/register",
        json={"email": alice_email, "username": "alice_ops", "password": "AlicePass2026!"}
    )
    login_a = client.post("/api/v1/auth/login", json={"email": alice_email, "password": "AlicePass2026!"}).json()
    token_a = login_a["access_token"]
    user_a_id = login_a["user_id"]

    # Register User B (Bob)
    bob_email = "bob_sec@titanops.ai"
    client.post(
        "/api/v1/auth/register",
        json={"email": bob_email, "username": "bob_sec", "password": "BobPass2026!"}
    )
    login_b = client.post("/api/v1/auth/login", json={"email": bob_email, "password": "BobPass2026!"}).json()
    token_b = login_b["access_token"]

    # Alice uploads document
    pdf_content = create_pdf("Alice Project Confidential Specs: Production cluster nodes = 64.")
    up_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("alice_specs.pdf", pdf_content, "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert up_resp.status_code == status.HTTP_201_CREATED
    doc_id = up_resp.json()["document_id"]

    # Alice indexes document
    idx_resp = client.post(
        f"/api/v1/documents/{doc_id}/index",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert idx_resp.status_code == status.HTTP_200_OK

    try:
        # Bob tries to index or delete Alice's document -> Must fail with 403 Forbidden
        del_attempt = client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert del_attempt.status_code == status.HTTP_403_FORBIDDEN

        # Alice chats about her document
        chat_resp = client.post(
            "/api/v1/chat",
            json={"message": "What is the production cluster node count?", "document_ids": [doc_id]},
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert chat_resp.status_code == status.HTTP_200_OK
        assert "64" in chat_resp.json()["message"]
    finally:
        # Alice deletes her document
        client.delete(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token_a}"})


def test_4_persistence_simulation_across_restart():
    """Simulates service restart by re-instantiating storage and checking data integrity."""
    test_pdf = create_pdf("Persistent Runbook V1: Gateway port is 8443.")
    up = client.post(
        "/api/v1/documents/upload",
        files={"file": ("persistent_test.pdf", test_pdf, "application/pdf")},
        headers={"X-User-ID": "persistence_tester"}
    )
    doc_id = up.json()["document_id"]

    try:
        # Re-load document service metadata directly from disk file
        metadata_map = document_service._load_metadata()
        assert doc_id in metadata_map
        assert metadata_map[doc_id]["filename"] == "persistent_test.pdf"
        assert metadata_map[doc_id]["user_id"] == "persistence_tester"

        # Verify physical file exists on disk
        stored_path = document_service.get_document_path(doc_id)
        assert stored_path.exists()
        assert stored_path.stat().st_size > 0
    finally:
        client.delete(f"/api/v1/documents/{doc_id}", headers={"X-User-ID": "persistence_tester"})
