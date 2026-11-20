# InfraMind — Enterprise Cloud SRE & Incident Runbook Assistant

An enterprise-grade, autonomous AI assistant engineered for Site Reliability Engineering (SRE), production incident triage, and runbook operations. Grounded in enterprise documentation and incident manuals with verified page citations, structured diagnosis trees, and telemetry monitoring.

---

## 📌 Development Roadmap

- [x] **Phase 1: Frontend UI & Experience** — High-fidelity ChatGPT Dark Interface (`#000000`), SRE workspaces, pill-shaped chat input, collapsible navigation, document management modals, and runbook directories.
- [x] **Phase 2: Backend Architecture & Foundation** — Clean, modular FastAPI backend (`/api/v1`), Pydantic Settings, secure PDF upload validation with magic byte verification, centralized error handling, and automated pytest suite.
- [x] **Phase 3: PDF Processing Engine** — Complete PyMuPDF extraction, SRE technical text cleaning, LangChain RecursiveCharacterTextSplitter chunking (1000/200), metadata preservation, and validation against the 50-page enterprise runbook.
- [ ] **Phase 4: Vector Storage & Semantic Search** — ChromaDB embeddings, dense vector retrieval, and hybrid keyword ranking.
- [ ] **Phase 5: LLM Orchestration & Grounded Reasoning** — Multi-provider LLM grounding (Gemini & OpenAI), citation verification, and automated SRE runbook execution.

---

## 🏗️ Phase 3 PDF Processing Engine Architecture

```
backend/
├── app/
│   ├── main.py                  # FastAPI application entrypoint & middleware
│   │
│   ├── api/
│   │   ├── router.py            # Centralized API v1 router
│   │   └── routes/
│   │       ├── health.py        # GET /api/v1/health
│   │       ├── chat.py          # POST /api/v1/chat (validated contract)
│   │       └── documents.py     # Document upload, process & status endpoints
│   │
│   ├── core/
│   │   ├── config.py            # Pydantic Settings configuration (.env)
│   │   └── exceptions.py        # Centralized exception handlers & error schemas
│   │
│   ├── schemas/
│   │   ├── chat.py              # Chat request & response Pydantic models
│   │   ├── document.py          # Document metadata & upload models
│   │   └── processing.py        # ExtractedPage, DocumentChunk & status models
│   │
│   ├── services/
│   │   ├── chat_service.py      # Chat validation & lifecycle orchestration
│   │   ├── document_service.py  # File validation, disk streaming & metadata store
│   │   ├── pdf_extractor.py     # PyMuPDF page-by-page extraction & empty-page detection
│   │   ├── text_cleaner.py      # Cleans boilerplate, preserves technical CLI & error codes
│   │   ├── text_chunker.py      # LangChain RecursiveCharacterTextSplitter (1000 / 200)
│   │   └── processing_service.py# Pipeline coordinator & structured JSON persistence
│   │
│   └── utils/
│       └── file_validation.py   # PDF magic bytes & filename sanitization
│
├── data/
│   ├── uploads/                 # Secure original PDF document storage
│   └── processed/               # Structured JSON output ({document_id}.json)
│
├── tests/
│   ├── conftest.py              # TestClient, sample PDF & text fixtures
│   ├── test_health.py           # Health & root endpoint tests
│   ├── test_chat.py             # Valid/invalid chat inquiry tests
│   ├── test_documents.py        # PDF upload, security, limits & CRUD tests
│   └── test_processing.py       # 14 automated unit & integration processing tests
│
├── scripts/
│   └── validate_runbook.py      # End-to-end verification against 50-page runbook
│
├── .env.example                 # Environment variable template
├── .gitignore                   # Version control ignore rules
├── requirements.txt             # Production Python dependencies
└── README.md
```

---

## 📡 API Endpoints (v1)

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service health & metadata check | `200 OK` |
| `POST` | `/api/v1/chat` | Validates chat message & registers conversation | `200 OK` |
| `POST` | `/api/v1/documents/upload` | Validates PDF (magic bytes & size) and stores file | `201 Created` |
| `GET` | `/api/v1/documents` | Lists all uploaded document metadata | `200 OK` |
| `GET` | `/api/v1/documents/{document_id}` | Retrieves metadata for a single document | `200 OK` |
| `DELETE` | `/api/v1/documents/{document_id}` | Safely deletes a document file & metadata | `200 OK` |
| `POST` | `/api/v1/documents/{document_id}/process` | Executes Phase 3 extraction, cleaning & chunking | `200 OK` |
| `GET` | `/api/v1/documents/{document_id}/processing-status` | Retrieves processing state & extraction metrics | `200 OK` |
| `GET` | `/api/v1/documents/{document_id}/chunks` | Retrieves all generated chunks for a document | `200 OK` |

---

## ⚙️ PDF Processing Pipeline Detail

### 1. Extraction (`pdf_extractor.py`)
- Employs **PyMuPDF (`fitz`)** for layout-aware text extraction.
- Preserves 1-based original page numbers (`page_number = page_idx + 1`).
- Identifies empty pages (`is_empty: bool`) and records per-page extraction errors without crashing.
- Handles password-protected PDFs by raising `FileEncryptedError`.
- Handles damaged/corrupted files by raising `FileCorruptedError`.

### 2. Text Cleaning (`text_cleaner.py`)
- Safely strips recurring running headers and footers (`TitanCloud Enterprise SRE & Incident Response Runbook`, `Document Page X of 50`, `Page X of 50 | Confidential...`).
- Normalizes irregular horizontal whitespace and tabs.
- Unwraps hyphenated line breaks (`distrib-\nuted` -> `distributed`) while strictly preserving CLI flags (`--endpoints`, `-o wide`).
- Collapses excessive blank lines (`\n{3,}` -> `\n\n`).
- **Strict Guardrail**: Preserves all CLI commands (`kubectl`, `etcdctl`, `patronictl`), error codes (`ERR_PG_REPLICA_LAG`, `502`, `504`, `137`, `OOMKilled`), percentages (`99.95%`, `99.50%`, `10%`, `25%`, `50%`), and escalation intervals.

### 3. Chunking (`text_chunker.py`)
- Powered by LangChain's **`RecursiveCharacterTextSplitter`**:
  - `chunk_size = 1000` characters.
  - `chunk_overlap = 200` characters.
  - Separators: `["\n\n", "\n", ". ", " ", ""]`.
- Ensures **Page Number Preservation**: Every chunk carries the exact 1-based page number where the text resides.
- Unique chunk ID format: `{document_id}_p{page_number}_c{chunk_index}`.

### 4. Storage & Persistence (`backend/data/processed/`)
- Structured JSON output saved to `backend/data/processed/{document_id}.json`.
- Document metadata in `documents_index.json` automatically transitions:
  `uploaded` $\rightarrow$ `processing` $\rightarrow$ `processed` (or `failed`).

---

## 📊 Runbook Validation Statistics (Actual 50-Page PDF)

Validated against the official enterprise reference manual [titancloud_sre_incident_runbook_50p.pdf](file:///Users/ayushu2861/Documents/byownprojexts/InfraMind/titancloud_sre_incident_runbook_50p.pdf):

```bash
./backend/venv/bin/python backend/scripts/validate_runbook.py
```

| Metric | Measured Value | Target / Requirement |
|---|---|---|
| **Total PDF Pages** | **50** | 50 Pages |
| **Successfully Extracted Pages** | **50 (100%)** | All readable pages |
| **Empty Pages Detected** | **0** | 0 |
| **Failed Pages** | **0** | 0 |
| **Total Extracted Characters** | **75,637** | Full corpus |
| **Total Chunks Generated** | **98** | Recursive 1000/200 splits |
| **Page Range Coverage** | **Pages 1 to 50** | Full continuity (100%) |
| **Technical Content Integrity Score** | **20 / 20 (100.0%)** | Zero data loss |

### Verified Technical Clauses:
- **Page 9**: Enterprise Uptime SLA (99.95%), Tier B 10% credit, Tier C 25% credit (including 99.2%), Tier D 50% credit.
- **Page 22**: Error Code `ERR_PG_REPLICA_LAG`, WAL replay delay definition, 45-second replication lag failover threshold, Patroni automatic fencing.
- **Page 41**: Severity-1 (P0) On-Call Timeline: L1 5-minute acknowledgement, L2 Staff SRE Lead page, 15-minute total escalation to VP of Infrastructure.

---

## 🧪 Automated Testing

Execute the automated test suite with `pytest`:

```bash
cd backend
PYTHONPATH=. ./venv/bin/pytest -v
```

### Complete Test Suite (28 Passed):
- `tests/test_health.py` (2 tests: health check & root metadata)
- `tests/test_chat.py` (4 tests: valid payload, conversation ID preservation, empty message 422, missing body 422)
- `tests/test_documents.py` (8 tests: valid upload, invalid extension, magic byte spoofing, 413 size limits, listing, retrieval, deletion, 404 missing)
- `tests/test_processing.py` (14 tests):
  1. `test_1_valid_pdf_extraction`: Single-page PDF extraction.
  2. `test_2_extraction_across_multiple_pages`: Multi-page ordered extraction.
  3. `test_3_correct_page_number_preservation`: 1-based page numbering sequence.
  4. `test_4_empty_page_detection`: Detection of blank pages without crashing.
  5. `test_5_corrupted_pdf_handling`: Rejection of corrupted files with `FileCorruptedError`.
  6. `test_6_text_cleaning`: Whitespace & newline normalization preserving CLI & codes.
  7. `test_7_chunk_size_limits`: LangChain chunk size cap verification.
  8. `test_8_chunk_overlap`: Character overlap between adjacent chunks.
  9. `test_9_metadata_preservation`: Complete chunk metadata structure.
  10. `test_10_document_processing_endpoint`: `POST /api/v1/documents/{id}/process`.
  11. `test_11_processing_status_endpoint`: `GET /api/v1/documents/{id}/processing-status`.
  12. `test_12_missing_document_handling`: `404 Not Found` on non-existent document processing.
  13. `test_13_duplicate_processing`: Idempotent re-processing without data corruption.
  14. `test_14_extraction_failure_handling`: Graceful handling and state update to `failed`.
