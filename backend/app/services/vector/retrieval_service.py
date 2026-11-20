import re
import time
import logging
from typing import List, Dict, Any, Optional, Set
from rank_bm25 import BM25Plus

from app.schemas.search import SearchResultChunk, SearchResponse
from app.services.vector.embedding_service import embedding_service
from app.services.vector.chroma_service import chroma_service

logger = logging.getLogger(__name__)

def tokenize_technical_text(text: str) -> List[str]:
    """
    Tokenizes text while preserving:
    - CLI commands and flags (kubectl, patronictl, --namespace, -n)
    - Error codes (ERR_PG_REPLICA_LAG, 502, 504, 137)
    - Percentages and metrics (99.95%, 100ms, 10Gi)
    - Path and configuration strings
    """
    if not text:
        return []
    # Match alphanumeric sequences including underscore, dash, dot, and percent
    tokens = re.findall(r"[a-zA-Z0-9_\-\.%]+", text.lower())
    return [t for t in tokens if len(t) > 0]

class BM25Manager:
    """
    Manages in-memory BM25 indices per user and document.
    Automatically populates from ChromaDB if not yet cached in memory.
    """

    def __init__(self):
        # Cache structure: user_id -> {document_id -> List[Dict[str, Any]]}
        self._user_docs: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def register_chunks(self, user_id: str, document_id: str, chunks: List[Dict[str, Any]]):
        if user_id not in self._user_docs:
            self._user_docs[user_id] = {}
        self._user_docs[user_id][document_id] = chunks

    def remove_document(self, user_id: str, document_id: str):
        if user_id in self._user_docs and document_id in self._user_docs[user_id]:
            del self._user_docs[user_id][document_id]

    def _ensure_user_docs_loaded(self, user_id: str, document_ids: Optional[List[str]] = None):
        """Loads chunks from persistent ChromaDB if not already in memory."""
        if user_id not in self._user_docs:
            self._user_docs[user_id] = {}

        # Query ChromaDB for user's documents
        where_clause: Dict[str, Any] = {"user_id": user_id}
        if document_ids:
            if len(document_ids) == 1:
                where_clause = {"$and": [{"user_id": user_id}, {"document_id": document_ids[0]}]}
            else:
                where_clause = {"$and": [{"user_id": user_id}, {"document_id": {"$in": document_ids}}]}

        # If cache is empty for this user or specific docs are missing, load from Chroma
        missing_docs = True
        if document_ids:
            missing_docs = any(doc_id not in self._user_docs[user_id] for doc_id in document_ids)
        elif len(self._user_docs[user_id]) == 0:
            missing_docs = True
        else:
            missing_docs = False

        if missing_docs:
            results = chroma_service.collection.get(
                where=where_clause,
                include=["documents", "metadatas"]
            )
            if results and results.get("ids"):
                for idx, c_id in enumerate(results["ids"]):
                    content = results["documents"][idx] if results.get("documents") else ""
                    metadata = results["metadatas"][idx] if results.get("metadatas") else {}
                    doc_id = metadata.get("document_id")
                    if doc_id:
                        if doc_id not in self._user_docs[user_id]:
                            self._user_docs[user_id][doc_id] = []
                        # Avoid duplicates
                        existing_ids = {c["chunk_id"] for c in self._user_docs[user_id][doc_id]}
                        if c_id not in existing_ids:
                            self._user_docs[user_id][doc_id].append({
                                "chunk_id": c_id,
                                "content": content,
                                "metadata": metadata
                            })

    def search_bm25(
        self,
        query: str,
        user_id: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Runs BM25 search over user-authorized chunks.
        """
        self._ensure_user_docs_loaded(user_id, document_ids)

        # Collect target chunks
        target_chunks: List[Dict[str, Any]] = []
        user_dict = self._user_docs.get(user_id, {})
        allowed_doc_ids = set(document_ids) if document_ids else set(user_dict.keys())

        for doc_id, c_list in user_dict.items():
            if doc_id in allowed_doc_ids:
                target_chunks.extend(c_list)

        if not target_chunks:
            return []

        # Tokenize query and corpus
        tokenized_corpus = [tokenize_technical_text(c["content"]) for c in target_chunks]
        tokenized_query = tokenize_technical_text(query)

        if not tokenized_query or not any(tokenized_corpus):
            return []

        bm25 = BM25Plus(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        # Rank results
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)

        hits: List[Dict[str, Any]] = []
        for idx in ranked_indices[:top_k]:
            score = float(scores[idx])
            # Check if there is actual token overlap between query and chunk
            chunk_tokens = set(tokenized_corpus[idx])
            query_tokens = set(tokenized_query)
            if score > 0.0 and len(chunk_tokens.intersection(query_tokens)) > 0:
                chunk = target_chunks[idx]
                hits.append({
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["content"],
                    "metadata": chunk["metadata"],
                    "bm25_score": score
                })

        return hits

class HybridRetrievalService:
    """
    Advanced Hybrid Retrieval Service:
    - Combines semantic vector similarity (ChromaDB) and exact keyword scoring (BM25).
    - Merges rankings via Reciprocal Rank Fusion (RRF).
    - Enforces document isolation by user_id.
    - Measures retrieval latency.
    """

    def __init__(self):
        self.bm25_manager = BM25Manager()

    def search(
        self,
        query: str,
        user_id: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        mode: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60
    ) -> SearchResponse:
        start_time = time.time()
        mode_lower = mode.lower()

        semantic_hits: List[Dict[str, Any]] = []
        bm25_hits: List[Dict[str, Any]] = []

        # 1. Semantic Retrieval (if hybrid or semantic)
        if mode_lower in ("hybrid", "semantic"):
            query_embedding = embedding_service.embed_query(query)
            raw_semantic_hits = chroma_service.query_semantic(
                query_embedding=query_embedding,
                top_k=max(top_k * 2, 10),
                user_id=user_id,
                document_ids=document_ids,
                where_filter=filters
            )
            # Filter out chunks below minimum semantic similarity threshold (0.20)
            semantic_hits = [h for h in raw_semantic_hits if h.get("similarity", 0.0) >= 0.20]

        # 2. Keyword BM25 Retrieval (if hybrid or bm25)
        if mode_lower in ("hybrid", "bm25"):
            bm25_hits = self.bm25_manager.search_bm25(
                query=query,
                user_id=user_id,
                document_ids=document_ids,
                top_k=max(top_k * 2, 10)
            )

        # 3. Rank Fusion
        fused_chunks: List[SearchResultChunk] = []

        if mode_lower == "hybrid":
            # Reciprocal Rank Fusion (RRF)
            # RRF score = sum(1 / (k + rank))
            rrf_scores: Dict[str, float] = {}
            chunk_data: Dict[str, Dict[str, Any]] = {}
            semantic_ranks: Dict[str, int] = {}
            bm25_ranks: Dict[str, int] = {}
            semantic_score_map: Dict[str, float] = {}
            bm25_score_map: Dict[str, float] = {}

            # Process semantic hits
            for rank, hit in enumerate(semantic_hits):
                cid = hit["chunk_id"]
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))
                chunk_data[cid] = hit
                semantic_ranks[cid] = rank + 1
                semantic_score_map[cid] = hit.get("similarity", 0.0)

            # Process BM25 hits
            for rank, hit in enumerate(bm25_hits):
                cid = hit["chunk_id"]
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))
                if cid not in chunk_data:
                    chunk_data[cid] = hit
                bm25_ranks[cid] = rank + 1
                bm25_score_map[cid] = hit.get("bm25_score", 0.0)

            # Sort by RRF score descending
            sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

            for cid in sorted_cids[:top_k]:
                data = chunk_data[cid]
                meta = data.get("metadata", {})
                fused_chunks.append(SearchResultChunk(
                    chunk_id=cid,
                    document_id=meta.get("document_id", ""),
                    document_name=meta.get("document_name", ""),
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    section_title=meta.get("section_title"),
                    content_type=meta.get("content_type", "text"),
                    content=data.get("content", ""),
                    score=round(rrf_scores[cid], 6),
                    semantic_score=round(semantic_score_map.get(cid, 0.0), 4) if cid in semantic_score_map else None,
                    bm25_score=round(bm25_score_map.get(cid, 0.0), 4) if cid in bm25_score_map else None,
                    metadata=meta
                ))

        elif mode_lower == "semantic":
            for hit in semantic_hits[:top_k]:
                meta = hit.get("metadata", {})
                fused_chunks.append(SearchResultChunk(
                    chunk_id=hit["chunk_id"],
                    document_id=meta.get("document_id", ""),
                    document_name=meta.get("document_name", ""),
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    section_title=meta.get("section_title"),
                    content_type=meta.get("content_type", "text"),
                    content=hit.get("content", ""),
                    score=round(hit.get("similarity", 0.0), 4),
                    semantic_score=round(hit.get("similarity", 0.0), 4),
                    bm25_score=None,
                    metadata=meta
                ))

        elif mode_lower == "bm25":
            for hit in bm25_hits[:top_k]:
                meta = hit.get("metadata", {})
                fused_chunks.append(SearchResultChunk(
                    chunk_id=hit["chunk_id"],
                    document_id=meta.get("document_id", ""),
                    document_name=meta.get("document_name", ""),
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    section_title=meta.get("section_title"),
                    content_type=meta.get("content_type", "text"),
                    content=hit.get("content", ""),
                    score=round(hit.get("bm25_score", 0.0), 4),
                    semantic_score=None,
                    bm25_score=round(hit.get("bm25_score", 0.0), 4),
                    metadata=meta
                ))

        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        logger.info(
            f"Search completed in {latency_ms}ms: query='{query[:40]}...', "
            f"mode={mode}, results={len(fused_chunks)}, user={user_id}"
        )

        return SearchResponse(
            query=query,
            total_results=len(fused_chunks),
            mode=mode,
            results=fused_chunks,
            latency_ms=latency_ms
        )

hybrid_retrieval_service = HybridRetrievalService()
