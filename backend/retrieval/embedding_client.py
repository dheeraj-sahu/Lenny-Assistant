"""
retrieval/embedding_client.py

Thin wrapper around sentence-transformers for local, CPU-based embedding.

The model is loaded once (singleton) and shared across all requests in-process.
No external API call is made — everything runs locally.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingClient:
    """
    Wraps a sentence-transformers model.
    Use get_embedding_client() to get the singleton instance.
    """

    def __init__(self, model_name: str):
        logger.info("loading_embedding_model", model=model_name)
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info("embedding_model_loaded", model=model_name, dim=self._dim)

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        """Embed a single string and return as a plain Python list."""
        vector: np.ndarray = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings at once — more efficient than calling embed() in a loop."""
        vectors: np.ndarray = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vectors.tolist()


@lru_cache(maxsize=1)
def get_embedding_client(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingClient:
    """
    Returns the singleton EmbeddingClient.
    Called by both the retrieval service and the ingestion pipeline,
    ensuring the same model (and thus same vector space) is used in both paths.
    """
    return EmbeddingClient(model_name)
