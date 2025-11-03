"""Embedding utilities built on Sentence-Transformers."""

from functools import lru_cache
from threading import Lock
from typing import List

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


class EmbeddingService:
    """Wraps a Sentence-Transformer model for consistent embedding generation."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._lock = Lock()

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Return an embedding vector for a single string."""

        model = self._ensure_model()
        vector = model.encode(
            [text], convert_to_numpy=True, normalize_embeddings=True)
        return vector[0].tolist()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Singleton accessor used by API and worker processes."""

    settings = get_settings()
    return EmbeddingService(settings.embedding_model_name)
