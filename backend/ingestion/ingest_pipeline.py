"""
ingestion/ingest_pipeline.py

Orchestrates the full offline ingestion pipeline:
  Fetch → Parse → Chunk → Embed → Upsert → Record

Designed to be:
  - Idempotent: re-running after a git pull updates changed episodes, adds new
    ones, and never duplicates existing vectors (deterministic chunk IDs).
  - Observable: each run writes a row to the ingestion_runs table in Postgres.
  - Robust: per-episode errors are caught and logged without aborting the run.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from core.logging import get_logger
from ingestion.chunker import Chunk, chunk_transcript
from ingestion.fetch_repo import fetch_transcripts_repo
from ingestion.parse_transcript import ParsedTranscript, discover_episodes, parse_transcript_file
from retrieval.embedding_client import get_embedding_client
from retrieval.qdrant_client import get_qdrant_service

logger = get_logger(__name__)


def _embed_chunks(chunks: list[Chunk], embedder) -> list[dict]:
    """
    Embed all chunks for one episode using batch encoding.
    Returns a list of dicts ready for Qdrant upsert.
    """
    texts = [c.chunk_text for c in chunks]
    vectors = embedder.embed_batch(texts)

    return [
        {
            "id": chunk.chunk_id,
            "vector": vector,
            "chunk_text": chunk.chunk_text,
            "episode_slug": chunk.episode_slug,
            "chunk_index": chunk.chunk_index,
            "timestamp_range": chunk.timestamp_range,
            "guest": chunk.guest,
            "title": chunk.title,
            "youtube_url": chunk.youtube_url,
            "video_id": chunk.video_id,
            "publish_date": chunk.publish_date,
            "keywords": chunk.keywords,
        }
        for chunk, vector in zip(chunks, vectors)
    ]


async def run_ingestion_pipeline() -> dict:
    """
    Run the full ingestion pipeline.

    Returns a summary dict with episode_count, chunk_count, status.
    Also writes a row to ingestion_runs in Postgres.
    """
    settings = get_settings()
    run_id = None
    db_session = None

    # Import database stuff here to avoid circular imports at module level
    from persistence.database import _session_factory
    from persistence.models import IngestionRun

    total_episodes = 0
    total_chunks = 0
    commit_sha = ""
    status = "running"

    # ── Record run start in Postgres ─────────────────────────────────────────
    try:
        if _session_factory:
            async with _session_factory() as db:
                run = IngestionRun(status="running")
                db.add(run)
                await db.commit()
                await db.refresh(run)
                run_id = run.id
                logger.info("ingestion_run_started", run_id=str(run_id))
    except Exception as exc:
        logger.warning("ingestion_run_record_failed", error=str(exc))
        # Don't abort — DB recording is secondary to the actual ingestion

    try:
        # ── Step 1: Fetch ─────────────────────────────────────────────────────
        logger.info("ingestion_fetch_start")
        commit_sha = fetch_transcripts_repo(
            repo_url=settings.transcripts_repo_url,
            local_path=settings.transcripts_local_path,
        )

        # ── Step 2: Discover episodes ─────────────────────────────────────────
        repo_root = Path(settings.transcripts_local_path)
        episodes = discover_episodes(repo_root)
        logger.info("ingestion_episodes_discovered", count=len(episodes))

        # ── Setup embedding + Qdrant ──────────────────────────────────────────
        embedder = get_embedding_client(settings.embedding_model)
        qdrant = get_qdrant_service(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            collection=settings.qdrant_collection,
            vector_dim=embedder.dimension,
        )

        # ── Step 3–5: Parse → Chunk → Embed → Upsert (per episode) ──────────
        for slug, transcript_path in episodes:
            try:
                # Parse
                transcript: ParsedTranscript = parse_transcript_file(transcript_path, slug)
                # Chunk
                chunks: list[Chunk] = chunk_transcript(transcript)
                if not chunks:
                    logger.warning("ingestion_no_chunks", slug=slug)
                    continue
                # Embed + build Qdrant payload
                payload_list = _embed_chunks(chunks, embedder)
                # Add corpus_version to each chunk payload
                for p in payload_list:
                    p["corpus_version"] = commit_sha[:8]
                # Upsert
                qdrant.upsert_chunks(payload_list)

                total_episodes += 1
                total_chunks += len(chunks)
                logger.info(
                    "ingestion_episode_done",
                    slug=slug,
                    chunks=len(chunks),
                    total_so_far=total_chunks,
                )
            except Exception as exc:
                logger.error("ingestion_episode_error", slug=slug, error=str(exc))
                # Continue with the next episode

        status = "success"
        logger.info(
            "ingestion_complete",
            commit_sha=commit_sha[:8],
            episodes=total_episodes,
            chunks=total_chunks,
        )

    except Exception as exc:
        status = "failed"
        logger.exception("ingestion_pipeline_error", error=str(exc))

    # ── Update run record in Postgres ─────────────────────────────────────────
    try:
        if run_id and _session_factory:
            from sqlalchemy import update as sa_update
            async with _session_factory() as db:
                await db.execute(
                    sa_update(IngestionRun)
                    .where(IngestionRun.id == run_id)
                    .values(
                        corpus_commit_sha=commit_sha,
                        episode_count=total_episodes,
                        chunk_count=total_chunks,
                        status=status,
                        finished_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
    except Exception as exc:
        logger.warning("ingestion_run_update_failed", error=str(exc))

    return {
        "status": status,
        "commit_sha": commit_sha,
        "episode_count": total_episodes,
        "chunk_count": total_chunks,
    }
