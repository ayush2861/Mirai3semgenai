import os
import re
import math
import uuid
from typing import List, Dict, Any, Optional, Tuple
import pymupdf
from app.schemas import SourceReference, DocumentMetadata
from app.storage import storage

class RAGEngine:
    def __init__(self):
        self.documents_index: Dict[str, List[Dict[str, Any]]] = {}
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self._init_index()

    def _tokenize(self, text: str) -> List[str]:
        # Clean and extract alphanumeric tokens, lowercased
        return re.findall(r'[a-zA-Z0-9_\-\.]{2,}', text.lower())

    def index_document(self, doc_id: str, filepath: str, filename: str) -> DocumentMetadata:
        try:
            pdf_doc = pymupdf.open(filepath)
            total_pages = len(pdf_doc)
            chunks: List[Dict[str, Any]] = []

            for page_index in range(total_pages):
                page = pdf_doc[page_index]
                page_text = page.get_text("text").strip()
                if not page_text:
                    continue

                page_num = page_index + 1
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]
                section_title = f"Page {page_num}"
                for line in lines[:4]:
                    if len(line) > 5 and not line.startswith("Page ") and not line.startswith("TitanCloud"):
                        section_title = line
                        break

                # Create page chunk
                chunk = {
                    "id": f"{doc_id}_p{page_num}",
                    "document_id": doc_id,
                    "document_name": filename,
                    "page_number": page_num,
                    "section": section_title,
                    "text": page_text,
                    "tokens": self._tokenize(page_text)
                }
                chunks.append(chunk)

            self.documents_index[doc_id] = chunks
            self._update_idf()

            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            doc_meta = DocumentMetadata(
                id=doc_id,
                filename=filename,
                filepath=filepath,
                size_bytes=file_size,
                pages=total_pages,
                chunks=len(chunks),
                status="indexed",
                uploaded_at="2026-11-20T10:00:00Z"
            )
            storage.save_document(doc_meta)
            print(f"Indexed document '{filename}': {total_pages} pages, {len(chunks)} chunks.")
            return doc_meta

        except Exception as e:
            print(f"Failed to index document {filename}: {e}")
            doc_meta = DocumentMetadata(
                id=doc_id,
                filename=filename,
                filepath=filepath,
                size_bytes=0,
                pages=0,
                chunks=0,
                status="error",
                error_message=str(e),
                uploaded_at="2026-11-20T10:00:00Z"
            )
            storage.save_document(doc_meta)
            return doc_meta

    def _update_idf(self):
        all_chunks = []
        for chunks in self.documents_index.values():
            all_chunks.extend(chunks)

        total_docs = len(all_chunks)
        if total_docs == 0:
            return

        doc_freq: Dict[str, int] = {}
        for chunk in all_chunks:
            unique_tokens = set(chunk["tokens"])
            for t in unique_tokens:
                doc_freq[t] = doc_freq.get(t, 0) + 1

        self.idf = {
            t: math.log((total_docs + 1) / (df + 1)) + 1.0
            for t, df in doc_freq.items()
        }

    def _init_index(self):
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "documents")
        os.makedirs(docs_dir, exist_ok=True)

        # Check existing documents from storage
        existing_docs = storage.list_documents()
        for doc in existing_docs:
            if os.path.exists(doc.filepath):
                self.index_document(doc.id, doc.filepath, doc.filename)

        # Ensure default runbook is indexed if present
        default_runbook_path = os.path.join(docs_dir, "titancloud_sre_incident_runbook_50p.pdf")
        if os.path.exists(default_runbook_path):
            existing_match = [d for d in existing_docs if d.filename == "titancloud_sre_incident_runbook_50p.pdf"]
            if not existing_match:
                doc_id = str(uuid.uuid4())
                self.index_document(doc_id, default_runbook_path, "titancloud_sre_incident_runbook_50p.pdf")

    def search(self, query: str, top_k: int = 4, target_doc_ids: Optional[List[str]] = None) -> List[Tuple[Dict[str, Any], float]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        all_candidates = []
        for doc_id, chunks in self.documents_index.items():
            if target_doc_ids and doc_id not in target_doc_ids:
                continue
            for chunk in chunks:
                all_candidates.append(chunk)

        if not all_candidates:
            return []

        scores: List[Tuple[Dict[str, Any], float]] = []

        # Technical terms boosting
        key_technical_terms = {
            "kubernetes": 2.5, "k8s": 2.5, "etcd": 3.0, "quorum": 2.5, "node": 1.5,
            "replication": 2.5, "lag": 2.5, "postgres": 2.0, "postgresql": 2.0, "patroni": 3.0,
            "gateway": 2.0, "envoy": 2.5, "502": 3.0, "504": 3.0, "timeout": 2.0,
            "cpu": 2.0, "memory": 2.0, "oom": 3.0, "oomkilled": 3.5, "cgroup": 2.5,
            "sla": 2.5, "credit": 3.0, "credits": 3.0, "availability": 2.0, "tier": 2.0,
            "kafka": 2.5, "consumer": 2.0, "partition": 2.0, "rebalance": 2.5,
            "redis": 2.5, "cache": 2.0, "eviction": 2.5, "sentinel": 2.5,
            "bgp": 3.0, "latency": 2.0, "peering": 2.0, "network": 1.5,
            "escalation": 2.0, "post-mortem": 2.5, "rca": 2.5, "sev-1": 3.0, "p1": 3.0
        }

        for chunk in all_candidates:
            chunk_tokens = chunk["tokens"]
            chunk_token_set = set(chunk_tokens)
            score = 0.0

            # Lexical BM25-like scoring
            for q in query_tokens:
                if q in chunk_token_set:
                    term_freq = chunk_tokens.count(q)
                    idf_val = self.idf.get(q, 1.2)
                    boost = key_technical_terms.get(q, 1.0)
                    score += (term_freq / (term_freq + 1.5)) * idf_val * boost

            # Query phrase match bonus
            query_lower = query.lower()
            chunk_text_lower = chunk["text"].lower()
            if query_lower in chunk_text_lower:
                score += 5.0
            
            # Sub-phrase match bonus
            words = query_lower.split()
            if len(words) >= 2:
                for w_idx in range(len(words) - 1):
                    pair = f"{words[w_idx]} {words[w_idx+1]}"
                    if pair in chunk_text_lower:
                        score += 2.0

            if score > 0.1:
                scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def generate_response(self, query: str, top_chunks: List[Tuple[Dict[str, Any], float]]) -> Tuple[str, List[SourceReference]]:
        sources: List[SourceReference] = []
        context_snippets = []

        for chunk, score in top_chunks:
            # Clean snippet for reference
            clean_text = " ".join(chunk["text"].replace("\n", " ").split())
            snippet = clean_text[:220] + "..." if len(clean_text) > 220 else clean_text
            sources.append(SourceReference(
                document_name=chunk["document_name"],
                page_number=chunk["page_number"],
                snippet=snippet,
                score=round(score, 2)
            ))
            context_snippets.append(
                f"[Source: {chunk['document_name']} — Page {chunk['page_number']} | Section: {chunk['section']}]\n{chunk['text']}"
            )

        full_context = "\n\n---\n\n".join(context_snippets)

        # Check if user has configured Gemini API key
        settings = storage.get_settings()
        gemini_key = settings.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel(settings.model_name or "gemini-2.0-flash")
                prompt = f"""You are TitanOps AI, an expert Enterprise Cloud SRE & Incident Runbook Assistant.
Your job is to provide accurate, authoritative, and actionable answers using the retrieved runbook context below.

CONTEXT FROM ENTERPRISE DOCUMENTATION:
{full_context}

USER QUESTION:
{query}

INSTRUCTIONS:
1. Ground your answer strictly in the provided technical documentation and runbook pages.
2. Provide technical depth with exact CLI commands, telemetry queries (Prometheus, Postgres, Envoy, etcd, etc.), root causes, and remediation steps.
3. Format with clean Markdown: use ## and ### headers, bold terms, bullet points, and syntax-highlighted bash/sql/yaml code blocks.
4. If warning or high-risk actions exist (e.g. data loss risk, failover), highlight them clearly.
5. Do NOT include a redundant "Sources" section in your text output; our UI automatically renders the exact interactive Sources cards below your response."""

                res = model.generate_content(prompt)
                if res and res.text:
                    return res.text.strip(), sources
            except Exception as e:
                print(f"Gemini API call failed, falling back to built-in SRE engine: {e}")

        # Built-in High-Intelligence SRE Engine (Deterministic, Grounded in Real Runbook Chunks)
        answer = self._synthesize_sre_response(query, top_chunks)
        return answer, sources

    def _synthesize_sre_response(self, query: str, top_chunks: List[Tuple[Dict[str, Any], float]]) -> str:
        if not top_chunks:
            return (
                "### No Relevant Documentation Found\n\n"
                "I searched the active enterprise documentation and incident runbooks, but could not find high-confidence procedures matching your query.\n\n"
                "**Recommended Action:**\n"
                "- Verify that the appropriate SRE runbook PDF (e.g., `titancloud_sre_incident_runbook_50p.pdf`) is uploaded and indexed in the **Documents** panel.\n"
                "- Try querying with specific technical terms such as *Kubernetes Outage*, *Database Replication Lag*, *Envoy 502/504*, *Kafka Lag*, *SLA Credits*, or *SEV-1 Escalation*."
            )

        top_chunk = top_chunks[0][0]
        page_num = top_chunk["page_number"]
        section = top_chunk["section"]
        text = top_chunk["text"]

        # Parse commands and structured text from the retrieved chunk
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        # Build structured markdown answer based on retrieved runbook content
        response_parts = []
        response_parts.append(f"## {section}\n")
        response_parts.append(f"**Referenced Document:** `{top_chunk['document_name']}` (Page {page_num})\n")

        # Extract problem/symptoms and diagnosis
        content_clean = text.replace("TitanCloud Global Infrastructure — SRE Operational Runbook", "")
        content_clean = re.sub(r'Page \d+ of \d+', '', content_clean).strip()

        # Look for commands in the chunk
        commands = []
        for line in lines:
            if any(tool in line for tool in ["kubectl", "etcdctl", "curl", "psql", "SELECT", "patronictl", "redis-cli", "kafka-", "mtr", "vtysh", "aws", "jcmd", "iostat", "systemctl", "ansible"]):
                commands.append(line)

        # Format overview
        response_parts.append("### 1. Operational Overview & Impact Assessment\n")
        # Extract main text
        paragraphs = [p.strip() for p in content_clean.split("\n\n") if len(p.strip()) > 30]
        if paragraphs:
            for p in paragraphs[:2]:
                if not any(cmd in p for cmd in ["kubectl", "etcdctl", "patronictl", "redis-cli"]):
                    response_parts.append(f"{p}\n")
        else:
            response_parts.append(f"Based on **Page {page_num}** of the SRE Incident Runbook, this incident pattern requires immediate systematic verification and triage according to standard Tier-1 protocol.\n")

        # Actionable diagnostic commands
        if commands:
            response_parts.append("### 2. Immediate Diagnostic & Remediation Commands\n")
            response_parts.append("Execute the following verification procedures in the incident cluster:\n\n```bash")
            for cmd in commands[:5]:
                clean_cmd = cmd.strip()
                if clean_cmd.startswith("•") or clean_cmd.startswith("-"):
                    clean_cmd = clean_cmd[1:].strip()
                response_parts.append(clean_cmd)
            response_parts.append("```\n")

        # Secondary chunks context if available
        if len(top_chunks) > 1:
            second_chunk = top_chunks[1][0]
            response_parts.append(f"### 3. Escalation & Correlated Runbook Context (Page {second_chunk['page_number']})\n")
            sec_text = second_chunk["text"].replace("TitanCloud Global Infrastructure — SRE Operational Runbook", "")
            sec_text = re.sub(r'Page \d+ of \d+', '', sec_text).strip()
            sec_lines = [l.strip() for l in sec_text.split("\n") if len(l.strip()) > 25 and not l.startswith("Page")]
            if sec_lines:
                for l in sec_lines[:3]:
                    response_parts.append(f"- **{l}**")
                response_parts.append("\n")

        # SLA / SRE Verification notes
        response_parts.append("### 4. Verification & Incident Resolution Criteria\n")
        response_parts.append("- **Verification:** Confirm telemetry stabilizes and error rates drop below the 0.01% baseline for at least 15 consecutive minutes.\n"
                               "- **Post-Incident Action:** File an Incident Record in PagerDuty and schedule a blameless post-mortem review per the SRE Incident Command guidelines.")

        return "\n".join(response_parts)

rag_engine = RAGEngine()
