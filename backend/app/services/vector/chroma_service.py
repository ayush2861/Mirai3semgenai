import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services.vector.chunking_service import IntelligentChunk

logger = logging.getLogger(__name__)

class ChromaService:
    """
    Manages persistent ChromaDB vector storage for InfraMind knowledge base.
    Supports persistent disk storage, multi-tenant isolation by user_id,
    and safe collection lifecycle management.
    """

    def __init__(self):
        self.persist_dir = str(settings.CHROMA_DIR)
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        logger.info(f"Initializing persistent ChromaDB client at {self.persist_dir}...")
        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            return self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Failed to get/create ChromaDB collection '{self.collection_name}': {e}")
            raise RuntimeError(f"ChromaDB initialization error: {str(e)}")

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._get_or_create_collection()
        return self._collection

    def upsert_chunks(
        self,
        chunks: List[IntelligentChunk],
        embeddings: List[List[float]]
    ) -> int:
        """
        Inserts or updates chunks and their corresponding embeddings into ChromaDB.
        """
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "document_name": c.document_name,
                "user_id": c.user_id,
                "page_number": int(c.page_number),
                "chunk_index": int(c.chunk_index),
                "section_title": c.section_title or "General",
                "content_type": c.content_type,
                "extraction_method": c.extraction_method,
                "char_count": int(c.char_count),
                "word_count": int(c.word_count),
            }
            for c in chunks
        ]

        # Chroma upsert in mini-batches to conserve memory on 512MB RAM instances
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            self.collection.upsert(
                ids=ids[i:i + batch_size],
                embeddings=embeddings[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size]
            )
        import gc
        gc.collect()

        logger.info(f"Upserted {len(chunks)} chunks into Chroma collection '{self.collection_name}'.")
        return len(chunks)

    def query_semantic(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic vector search in ChromaDB with user isolation and document scoping.
        """
        # Build filter with user isolation
        conditions = []
        if user_id:
            conditions.append({"user_id": user_id})

        if document_ids:
            if len(document_ids) == 1:
                conditions.append({"document_id": document_ids[0]})
            else:
                conditions.append({"document_id": {"$in": document_ids}})

        if where_filter:
            conditions.append(where_filter)

        final_where = None
        if len(conditions) == 1:
            final_where = conditions[0]
        elif len(conditions) > 1:
            final_where = {"$and": conditions}

        # Query ChromaDB
        total_in_collection = self.collection.count()
        if total_in_collection == 0:
            return []

        actual_k = min(top_k, total_in_collection)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            where=final_where,
            include=["documents", "metadatas", "distances"]
        )

        hits: List[Dict[str, Any]] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            for idx in range(len(results["ids"][0])):
                chunk_id = results["ids"][0][idx]
                content = results["documents"][0][idx] if results.get("documents") else ""
                metadata = results["metadatas"][0][idx] if results.get("metadatas") else {}
                distance = results["distances"][0][idx] if results.get("distances") else 1.0
                # Cosine distance to similarity score: similarity = 1 - distance
                similarity = max(0.0, min(1.0, 1.0 - distance))

                hits.append({
                    "chunk_id": chunk_id,
                    "content": content,
                    "metadata": metadata,
                    "similarity": similarity,
                    "distance": distance
                })

        return hits

    def get_document_chunks(
        self,
        document_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all indexed chunks for a document, scoped by user_id if provided.
        """
        where_clause: Dict[str, Any] = {"document_id": document_id}
        if user_id:
            where_clause = {"$and": [{"document_id": document_id}, {"user_id": user_id}]}

        results = self.collection.get(
            where=where_clause,
            include=["documents", "metadatas"]
        )

        chunks: List[Dict[str, Any]] = []
        if results and results.get("ids"):
            for idx, c_id in enumerate(results["ids"]):
                chunks.append({
                    "chunk_id": c_id,
                    "content": results["documents"][idx] if results.get("documents") else "",
                    "metadata": results["metadatas"][idx] if results.get("metadatas") else {}
                })
        return chunks

    def delete_document(self, document_id: str, user_id: Optional[str] = None) -> int:
        """
        Removes all chunks of a document from Chroma collection with user verification.
        """
        where_clause: Dict[str, Any] = {"document_id": document_id}
        if user_id:
            where_clause = {"$and": [{"document_id": document_id}, {"user_id": user_id}]}

        # Check existing count
        existing = self.collection.get(where=where_clause)
        count = len(existing.get("ids", []))
        if count > 0:
            self.collection.delete(where=where_clause)
            logger.info(f"Deleted {count} chunks for document {document_id} from ChromaDB.")
        return count

    def get_index_status(self, document_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Checks indexing status of a document in ChromaDB.
        """
        where_clause: Dict[str, Any] = {"document_id": document_id}
        if user_id:
            where_clause = {"$and": [{"document_id": document_id}, {"user_id": user_id}]}

        existing = self.collection.get(where=where_clause)
        count = len(existing.get("ids", []))
        return {
            "document_id": document_id,
            "indexed": count > 0,
            "chunk_count": count,
            "collection_name": self.collection_name
        }

chroma_service = ChromaService()
