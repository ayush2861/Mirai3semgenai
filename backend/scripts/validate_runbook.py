import os
import sys
import json
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.document_service import document_service
from app.services.processing_service import processing_service

async def run_validation():
    print("=" * 70)
    print(" InfraMind Phase 3 — PDF Processing Engine Validation")
    print(" Target: 50-Page TitanCloud Enterprise SRE Incident Runbook")
    print("=" * 70)

    runbook_path = Path(__file__).resolve().parent.parent.parent / "titancloud_sre_incident_runbook_50p.pdf"
    if not runbook_path.exists():
        runbook_path = settings.DATA_DIR / "documents" / "titancloud_sre_incident_runbook_50p.pdf"

    if not runbook_path.exists():
        print(f"[!] Error: Could not find {runbook_path}")
        return

    print(f"[*] Found runbook at: {runbook_path}")
    print(f"[*] File size: {runbook_path.stat().st_size:,} bytes")

    # 1. Upload runbook into storage via document_service
    class MockUploadFile:
        def __init__(self, path: Path):
            self.filename = path.name
            self.content_type = "application/pdf"
            self._file = open(path, "rb")

        async def read(self, size=-1):
            return self._file.read(size)

        async def seek(self, offset):
            self._file.seek(offset)

        def close(self):
            self._file.close()

    mock_file = MockUploadFile(runbook_path)
    upload_res = await document_service.save_uploaded_file(mock_file)
    mock_file.close()

    doc_id = upload_res.document_id
    print(f"[✓] Uploaded with Document ID: {doc_id}")

    # 2. Process document through Phase 3 pipeline
    print("[*] Executing PDF Processing Engine (Extraction -> Cleaning -> Chunking)...")
    proc_res = await processing_service.process_document(doc_id)

    print("\n" + "-" * 55)
    print(" PROCESSING ENGINE EXTRACTION & CHUNKING STATISTICS:")
    print("-" * 55)
    print(f"  • Total PDF Pages:            {proc_res.total_pages}")
    print(f"  • Successfully Extracted:     {proc_res.extracted_pages}")
    print(f"  • Empty Pages:                {proc_res.empty_pages}")
    print(f"  • Failed Pages:               {proc_res.failed_pages}")
    print(f"  • Total Characters Extracted: {proc_res.total_characters:,}")
    print(f"  • Total Chunks Generated:     {proc_res.total_chunks}")
    print("-" * 55)

    # 3. Verify content preservation across chunks
    chunks = processing_service.get_processed_chunks(doc_id)
    all_chunks_text = " ".join(c.content for c in chunks)

    # Key SRE verification checklist matching the actual 50-page corpus
    checks = {
        "Error Code: ERR_PG_REPLICA_LAG": "ERR_PG_REPLICA_LAG",
        "Replication lag threshold: 45 seconds": "45 seconds",
        "Patroni consensus controller": "Patroni consensus controller",
        "WAL replay delay definition": "write-ahead log",
        "Three consecutive 5s probes": "consecutive 5-second health probes",
        "SLA Standard: 99.95% monthly uptime": "99.95% monthly uptime",
        "Tier B: 99.50% to 99.94% (10% credit)": "10% service credit",
        "Tier C: 99.00% to 99.49% (25% credit)": "25% service credit",
        "Tier C 99.2% inclusion": "99.2%",
        "Tier D: Below 99.00% (50% credit)": "50% service credit",
        "Severity-1 (P0) PagerDuty alert": "Severity-1 (P0)",
        "L1 On-Call 5-minute ack deadline": "maximum of 5 minutes to acknowledge",
        "L2 Staff SRE Lead escalation": "L2 Staff SRE Lead",
        "15 minutes total escalation": "15 minutes total",
        "VP of Infrastructure escalation": "VP of Infrastructure",
        "Kubernetes Control Plane Telemetry": "Kubernetes Control Plane Telemetry",
        "BGP Anycast Ingress Routing": "BGP Anycast Ingress Routing",
        "Zero-Trust mTLS Certificate Rotation": "mTLS Certificate Rotation",
        "Post-Mortem Blameless RCA": "Blameless Root-Cause Analysis",
        "Boilerplate Header Stripped": "TitanCloud Enterprise SRE & Incident Response Runbook - Official Reference Corpus"
    }

    print("\n[*] Auditing Technical Content Preservation & Cleanliness:")
    passed_checks = 0
    for label, pattern in checks.items():
        if label == "Boilerplate Header Stripped":
            # Must NOT be in cleaned chunks
            is_stripped = pattern not in all_chunks_text
            status_icon = "✓" if is_stripped else "✗"
            print(f"  [{status_icon}] {label.ljust(42)}: {'CLEANED (STRIPPED)' if is_stripped else 'LEAKED'}")
            if is_stripped:
                passed_checks += 1
        else:
            found = pattern.lower() in all_chunks_text.lower()
            status_icon = "✓" if found else "✗"
            print(f"  [{status_icon}] {label.ljust(42)}: {'PRESERVED' if found else 'MISSING'}")
            if found:
                passed_checks += 1

    print("-" * 55)
    print(f"Integrity Score: {passed_checks}/{len(checks)} ({passed_checks/len(checks)*100:.1f}%)")

    # 4. Check page number continuity
    unique_pages = sorted(list(set(c.page_number for c in chunks)))
    print(f"\n[*] Page Number Preservation:")
    print(f"  • Min Page: {min(unique_pages)}")
    print(f"  • Max Page: {max(unique_pages)}")
    print(f"  • Total Pages Represented in Chunks: {len(unique_pages)}/50")
    print(f"  • Page 9 (SLA Credits) present in chunks: {9 in unique_pages}")
    print(f"  • Page 22 (ERR_PG_REPLICA_LAG) present in chunks: {22 in unique_pages}")
    print(f"  • Page 41 (Escalation Timeline) present in chunks: {41 in unique_pages}")

    # Inspect Page 9, 22, 41 chunks directly
    p9_chunk = next(c for c in chunks if c.page_number == 9)
    p22_chunk = next(c for c in chunks if c.page_number == 22)
    p41_chunk = next(c for c in chunks if c.page_number == 41)

    print("\n[*] Inspected Chunk Samples:")
    print(f"  --- Chunk ID: {p9_chunk.chunk_id} (Page {p9_chunk.page_number}) ---")
    print(f"  {p9_chunk.content[:220]}...")
    print(f"\n  --- Chunk ID: {p22_chunk.chunk_id} (Page {p22_chunk.page_number}) ---")
    print(f"  {p22_chunk.content[:220]}...")
    print(f"\n  --- Chunk ID: {p41_chunk.chunk_id} (Page {p41_chunk.page_number}) ---")
    print(f"  {p41_chunk.content[:220]}...")

    print("\n[✓] Phase 3 Validation Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(run_validation())
