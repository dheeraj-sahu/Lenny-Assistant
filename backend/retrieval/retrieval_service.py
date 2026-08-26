"""
retrieval/retrieval_service.py

Pure-function retrieval service:
  query string → [TranscriptChunk]

This is the only component that bridges the agent's tool call and Qdrant.
It has no knowledge of sessions or database state — keeping it independently
testable and reusable across surfaces (chat, admin, future Slack bot etc.).

Returns a special sentinel when no results exceed the confidence threshold,
which allows the agent to honestly say it can't answer rather than hallucinate.
"""

from dataclasses import dataclass

from app.config import get_settings
from core.logging import get_logger
from retrieval.embedding_client import get_embedding_client
from retrieval.qdrant_client import TranscriptChunk, get_qdrant_service

logger = get_logger(__name__)

# Sentinel value returned when retrieval confidence is too low
NO_RESULTS_SENTINEL = "__NO_RELEVANT_CONTENT_FOUND__"


@dataclass
class RetrievalResult:
    """
    The structured output of a retrieval call.
    `found` is False when nothing exceeded the threshold.
    """
    found: bool
    chunks: list[TranscriptChunk]
    top_score: float


def retrieve(
    query: str,
    topic_hint: str | None = None,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> RetrievalResult:
    """
    Embed `query` and search Qdrant.

    Args:
        query:           User's natural-language question.
        topic_hint:      Optional keyword to narrow results (e.g. "pricing", "growth").
        top_k:           How many chunks to return (defaults to settings value).
        score_threshold: Minimum similarity to include a chunk (defaults to settings value).

    Returns:
        RetrievalResult with found=True and populated chunks, or found=False if
        the best match is below the threshold.
    """
    settings = get_settings()
    k = top_k or settings.retrieval_top_k
    threshold = score_threshold or settings.retrieval_score_threshold

    # 1. Embed the query locally (no network call)
    embedder = get_embedding_client(settings.embedding_model)
    query_vector = embedder.embed(query)

    # 2. Search Qdrant
    qdrant = get_qdrant_service(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
        vector_dim=embedder.dimension,
    )
    chunks = qdrant.search(
        query_vector=query_vector,
        top_k=k,
        score_threshold=threshold,
        topic_filter=topic_hint,
    )

    top_score = chunks[0].score if chunks else 0.0

    logger.info(
        "retrieval_complete",
        query_preview=query[:80],
        topic_hint=topic_hint,
        results_count=len(chunks),
        top_score=round(top_score, 4),
        threshold=threshold,
    )

    if not chunks:
        return RetrievalResult(found=False, chunks=[], top_score=0.0)

    return RetrievalResult(found=True, chunks=chunks, top_score=top_score)


def format_chunks_for_prompt(chunks: list[TranscriptChunk]) -> str:
    """
    Format retrieved chunks into a text block for injection into the agent prompt.
    Each chunk is labelled with its source so the agent can cite it naturally.
    """
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        ts = f" (~{chunk.timestamp_range})" if chunk.timestamp_range else ""
        parts.append(
            f"[Source {i}] {chunk.guest} — \"{chunk.title}\"{ts}\n"
            f"{chunk.chunk_text}"
        )
    return "\n\n---\n\n".join(parts)


def chunks_to_citations(chunks: list[TranscriptChunk]) -> list[dict]:
    """
    Convert chunks to the structured sources[] format stored in the messages table
    and returned in SSE done events.
    """
    seen: set[str] = set()
    citations = []
    for chunk in chunks:
        key = chunk.episode_slug
        if key not in seen:
            seen.add(key)
            citations.append(
                {
                    "episode_slug": chunk.episode_slug,
                    "guest": chunk.guest,
                    "title": chunk.title,
                    "youtube_url": chunk.youtube_url,
                    "timestamp": chunk.timestamp_range.split("–")[0] if chunk.timestamp_range else None,
                    "score": round(chunk.score, 4),
                }
            )
    return citations
