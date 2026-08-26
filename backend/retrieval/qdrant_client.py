"""
retrieval/qdrant_client.py

Thin wrapper around the Qdrant Python client.
Handles collection creation/verification and provides typed
upsert/search methods so the rest of the codebase never imports
qdrant_client directly.
"""

from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchParams,
    VectorParams,
)

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptChunk:
    """A single vector-search result with its payload."""
    chunk_id: str
    score: float
    chunk_text: str
    episode_slug: str
    guest: str
    title: str
    youtube_url: str
    video_id: str
    publish_date: str
    timestamp_range: str
    keywords: list[str]
    corpus_version: str


class QdrantService:
    """
    Manages a Qdrant collection for transcript chunks.
    Exposed as a singleton via get_qdrant_service().
    """

    def __init__(self, host: str, port: int, collection: str, vector_dim: int):
        self._client = _QdrantClient(host=host, port=port)
        self._collection = collection
        self._dim = vector_dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
            logger.info("qdrant_collection_created", collection=self._collection, dim=self._dim)
        else:
            logger.info("qdrant_collection_exists", collection=self._collection)

    def upsert_chunks(self, chunks: list[dict]) -> int:
        """
        Upsert a list of chunk dicts into Qdrant.
        Each dict must have: id, vector, and all payload fields.
        Returns the number of chunks upserted.
        """
        points = [
            PointStruct(
                id=chunk["id"],
                vector=chunk["vector"],
                payload={k: v for k, v in chunk.items() if k not in ("id", "vector")},
            )
            for chunk in chunks
        ]

        # Qdrant recommends batching large upserts
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=self._collection,
                points=points[i : i + batch_size],
            )

        logger.info("qdrant_upserted", count=len(points), collection=self._collection)
        return len(points)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 8,
        score_threshold: float = 0.35,
        topic_filter: str | None = None,
    ) -> list[TranscriptChunk]:
        """
        Perform a similarity search.

        Args:
            query_vector:    Embedding of the user's query.
            top_k:           Maximum number of results to return.
            score_threshold: Minimum cosine similarity (0–1) to include a result.
            topic_filter:    If set, only return chunks whose `keywords` contain this string.

        Returns:
            List of TranscriptChunk objects, ordered by score descending.
        """
        query_filter = None
        if topic_filter:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="keywords",
                        match=MatchValue(value=topic_filter),
                    )
                ]
            )

        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=query_filter,
            search_params=SearchParams(hnsw_ef=128, exact=False),
            with_payload=True,
        )

        chunks = []
        for hit in results:
            p = hit.payload or {}
            chunks.append(
                TranscriptChunk(
                    chunk_id=str(hit.id),
                    score=hit.score,
                    chunk_text=p.get("chunk_text", ""),
                    episode_slug=p.get("episode_slug", ""),
                    guest=p.get("guest", ""),
                    title=p.get("title", ""),
                    youtube_url=p.get("youtube_url", ""),
                    video_id=p.get("video_id", ""),
                    publish_date=p.get("publish_date", ""),
                    timestamp_range=p.get("timestamp_range", ""),
                    keywords=p.get("keywords", []),
                    corpus_version=p.get("corpus_version", ""),
                )
            )
        return chunks

    def count(self) -> int:
        """Return the total number of vectors in the collection."""
        info = self._client.get_collection(self._collection)
        return info.points_count or 0


@lru_cache(maxsize=1)
def get_qdrant_service(
    host: str = "qdrant",
    port: int = 6333,
    collection: str = "lenny_transcripts",
    vector_dim: int = 384,  # all-MiniLM-L6-v2 default
) -> QdrantService:
    """Returns the singleton QdrantService."""
    return QdrantService(host=host, port=port, collection=collection, vector_dim=vector_dim)
