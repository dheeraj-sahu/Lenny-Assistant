"""
tests/test_retrieval_service.py

Unit tests for the retrieval service layer.
These tests use mocking so they don't require a live Qdrant instance.
"""

from unittest.mock import MagicMock, patch

import pytest

from retrieval.retrieval_service import (
    chunks_to_citations,
    format_chunks_for_prompt,
    retrieve,
)
from retrieval.qdrant_client import TranscriptChunk


def _make_chunk(score: float = 0.8, slug: str = "nick-turley") -> TranscriptChunk:
    return TranscriptChunk(
        chunk_id="123",
        score=score,
        chunk_text="Lenny asked about product-market fit and Nick said...",
        episode_slug=slug,
        guest="Nick Turley",
        title="Building ChatGPT's First Product",
        youtube_url="https://youtube.com/watch?v=abc123",
        video_id="abc123",
        publish_date="2024-01-15",
        timestamp_range="00:12:34–00:17:45",
        keywords=["product", "growth"],
        corpus_version="abc12345",
    )


@pytest.fixture
def mock_embedder():
    with patch("retrieval.retrieval_service.get_embedding_client") as mock:
        client = MagicMock()
        client.embed.return_value = [0.1] * 384
        client.dimension = 384
        mock.return_value = client
        yield client


@pytest.fixture
def mock_qdrant():
    with patch("retrieval.retrieval_service.get_qdrant_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


def test_retrieve_found(mock_embedder, mock_qdrant):
    """retrieve() should return found=True when Qdrant returns chunks."""
    mock_qdrant.search.return_value = [_make_chunk(score=0.75)]

    result = retrieve("how does Figma think about pricing?")

    assert result.found is True
    assert len(result.chunks) == 1
    assert result.top_score == pytest.approx(0.75)
    mock_qdrant.search.assert_called_once()


def test_retrieve_not_found(mock_embedder, mock_qdrant):
    """retrieve() should return found=False when Qdrant returns empty list."""
    mock_qdrant.search.return_value = []

    result = retrieve("what is the best JavaScript framework in 2026?")

    assert result.found is False
    assert result.chunks == []
    assert result.top_score == 0.0


def test_format_chunks_for_prompt(mock_embedder, mock_qdrant):
    """format_chunks_for_prompt should include guest, title, and text."""
    chunk = _make_chunk()
    formatted = format_chunks_for_prompt([chunk])

    assert "Nick Turley" in formatted
    assert "Building ChatGPT's First Product" in formatted
    assert "00:12:34" in formatted
    assert "product-market fit" in formatted


def test_chunks_to_citations_deduplicates():
    """chunks_to_citations should deduplicate by episode_slug."""
    chunks = [
        _make_chunk(score=0.9, slug="nick-turley"),
        _make_chunk(score=0.7, slug="nick-turley"),  # same episode
        _make_chunk(score=0.6, slug="shreyas-doshi"),
    ]
    # Manually assign different slug to the third
    chunks[2] = TranscriptChunk(
        chunk_id="456",
        score=0.6,
        chunk_text="Shreyas talked about influence...",
        episode_slug="shreyas-doshi",
        guest="Shreyas Doshi",
        title="The Art of Influence",
        youtube_url="https://youtube.com/watch?v=xyz",
        video_id="xyz",
        publish_date="2023-06-01",
        timestamp_range="00:05:00–00:10:00",
        keywords=["influence", "leadership"],
        corpus_version="abc12345",
    )

    citations = chunks_to_citations(chunks)

    assert len(citations) == 2  # deduped
    slugs = {c["episode_slug"] for c in citations}
    assert "nick-turley" in slugs
    assert "shreyas-doshi" in slugs


def test_topic_hint_passed_to_qdrant(mock_embedder, mock_qdrant):
    """retrieve() with topic_hint should pass it to Qdrant search."""
    mock_qdrant.search.return_value = []

    retrieve("pricing strategy", topic_hint="pricing")

    call_kwargs = mock_qdrant.search.call_args.kwargs
    assert call_kwargs.get("topic_filter") == "pricing"
