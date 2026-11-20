import logging
import threading
from typing import List, Optional
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Local embedding generator using Sentence Transformers.
    Loads sentence-transformers/all-MiniLM-L6-v2 locally as a thread-safe singleton.
    Provides batch embedding generation for chunks and normalized embeddings for queries.
    """

    _instance: Optional["EmbeddingService"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model: Optional[SentenceTransformer] = None
        self._dimension: int = 384
        self._init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_model_loaded(self):
        """Loads model once into memory."""
        if self._model is None:
            with self._init_lock:
                if self._model is None:
                    logger.info(f"Loading local SentenceTransformer model: {self.model_name}...")
                    try:
                        self._model = SentenceTransformer(self.model_name)
                        # Derive dimension safely
                        if hasattr(self._model, "get_embedding_dimension"):
                            self._dimension = self._model.get_embedding_dimension()
                        else:
                            self._dimension = self._model.get_sentence_embedding_dimension()
                        logger.info(
                            f"Embedding model '{self.model_name}' loaded successfully "
                            f"(dimension={self._dimension})."
                        )
                    except Exception as e:
                        logger.error(f"Failed to initialize embedding model '{self.model_name}': {e}")
                        raise RuntimeError(f"Embedding model initialization failed: {str(e)}")

    @property
    def dimension(self) -> int:
        self._ensure_model_loaded()
        return self._dimension

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True
    ) -> List[List[float]]:
        """
        Generates normalized embedding vectors for a batch of text chunks.
        """
        if not texts:
            return []

        self._ensure_model_loaded()
        try:
            embeddings = self._model.encode(
                sentences=texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize,
                convert_to_numpy=True
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

    def embed_query(self, query: str, normalize: bool = True) -> List[float]:
        """
        Generates normalized embedding vector for a single user query.
        """
        if not query or not query.strip():
            return [0.0] * self.dimension

        self._ensure_model_loaded()
        try:
            embedding = self._model.encode(
                sentences=query.strip(),
                normalize_embeddings=normalize,
                convert_to_numpy=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding for '{query}': {e}")
            raise RuntimeError(f"Failed to generate query embedding: {str(e)}")

embedding_service = EmbeddingService.get_instance()
