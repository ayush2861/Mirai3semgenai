import os
import logging
import threading
from typing import List, Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Reduce thread and memory allocations for low-memory environments (Render 512MB RAM)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

class EmbeddingService:
    """
    Lightweight embedding generator.
    Uses ChromaDB's built-in ONNXMiniLM_L6_V2 runtime (fast, minimal RAM < 150MB, no PyTorch overhead).
    Falls back gracefully to SentenceTransformer if ONNX runtime is unavailable.
    """

    _instance: Optional["EmbeddingService"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model: Optional[Any] = None
        self._is_onnx: bool = False
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
        """Loads lightweight ONNX model into memory (or SentenceTransformer fallback)."""
        if self._model is None:
            with self._init_lock:
                if self._model is None:
                    # 1. Primary: Lightweight ONNX MiniLM (safe for 512MB containers)
                    try:
                        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
                        logger.info("Initializing lightweight ONNXMiniLM_L6_V2 embedding engine...")
                        self._model = ONNXMiniLM_L6_V2()
                        self._is_onnx = True
                        self._dimension = 384
                        logger.info("Lightweight ONNX embedding engine initialized successfully (dim=384).")
                        return
                    except Exception as onnx_err:
                        logger.warning(
                            f"ONNX MiniLM engine initialization failed ({onnx_err}); "
                            "falling back to SentenceTransformer..."
                        )

                    # 2. Secondary fallback: SentenceTransformer (lazy loaded)
                    try:
                        from sentence_transformers import SentenceTransformer
                        logger.info(f"Loading SentenceTransformer fallback model: {self.model_name}...")
                        self._model = SentenceTransformer(self.model_name)
                        self._is_onnx = False
                        if hasattr(self._model, "get_embedding_dimension"):
                            self._dimension = self._model.get_embedding_dimension()
                        else:
                            self._dimension = self._model.get_sentence_embedding_dimension()
                        logger.info(
                            f"SentenceTransformer fallback model loaded successfully "
                            f"(dimension={self._dimension})."
                        )
                    except Exception as e:
                        logger.error(f"Failed to initialize embedding model: {e}")
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
            if self._is_onnx:
                all_results: List[List[float]] = []
                mini_batch_size = max(1, min(batch_size, 16))
                for i in range(0, len(texts), mini_batch_size):
                    chunk_slice = texts[i:i + mini_batch_size]
                    raw_batch = self._model(chunk_slice)
                    for vec in raw_batch:
                        all_results.append([float(x) for x in vec])
                import gc
                gc.collect()
                return all_results
            else:
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
            if self._is_onnx:
                res = self._model([query.strip()])
                return [float(x) for x in res[0]]
            else:
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
