"""
ingestion/chunker.py

Splits a ParsedTranscript's body into overlapping, semantically-coherent chunks.

Strategy:
  1. Start from the list of speaker turns produced by the parser.
  2. Group consecutive turns into windows targeting ~600 tokens (≈ 2,400 chars).
  3. Add ~15% overlap between windows by carrying forward the last N turns
     from the previous window.
  4. Each chunk records its timestamp range (start–end) for precise citation.
  5. Chunks are assigned a deterministic ID: hash(episode_slug + chunk_index)
     so re-running ingestion updates existing vectors rather than duplicating them.
"""

import hashlib
import uuid
from dataclasses import dataclass

from ingestion.parse_transcript import ParsedTranscript, SpeakerTurn

# Target chunk size in characters (approx 600 tokens × 4 chars/token)
TARGET_CHUNK_CHARS = 2_400
# Overlap: carry forward approximately 15% of previous chunk
OVERLAP_CHARS = int(TARGET_CHUNK_CHARS * 0.15)


@dataclass
class Chunk:
    """A single indexable unit ready for embedding and Qdrant upsert."""
    chunk_id: str           # deterministic hash
    chunk_index: int
    episode_slug: str
    chunk_text: str
    timestamp_range: str    # e.g. "00:12:34–00:17:45"
    # All episode-level metadata is duplicated into the chunk payload
    # so each Qdrant point is self-contained and we never need a JOIN.
    guest: str
    title: str
    youtube_url: str
    video_id: str
    publish_date: str
    keywords: list[str]


def _make_chunk_id(episode_slug: str, chunk_index: int) -> str:
    """
    Deterministic, Qdrant-safe chunk ID (UUID).
    Uses a hash so re-ingestion updates existing points instead of duplicating.
    """
    raw = f"{episode_slug}::{chunk_index}"
    digest = hashlib.md5(raw.encode()).hexdigest()
    # Qdrant point IDs must be unsigned 64-bit integers or UUIDs.
    return str(uuid.UUID(digest))


def _turns_to_text(turns: list[SpeakerTurn]) -> str:
    """Concatenate speaker turns into a readable block."""
    return "\n".join(
        f"{turn.speaker} ({turn.timestamp}): {turn.text}" for turn in turns
    )


def chunk_transcript(transcript: ParsedTranscript) -> list[Chunk]:
    """
    Split a ParsedTranscript into overlapping chunks.

    If the transcript has no speaker turns (very short or parse failure),
    fall back to chunking the raw body by character count.
    """
    turns = transcript.speaker_turns

    if not turns:
        # Fallback: chunk raw body text
        return _chunk_raw_text(transcript)

    chunks: list[Chunk] = []
    window: list[SpeakerTurn] = []
    window_chars = 0
    chunk_index = 0
    overlap_turns: list[SpeakerTurn] = []  # carry-forward buffer

    for turn in turns:
        turn_text = f"{turn.speaker} ({turn.timestamp}): {turn.text}"
        turn_chars = len(turn_text)

        # If adding this turn would exceed the target, flush the current window
        if window and (window_chars + turn_chars) > TARGET_CHUNK_CHARS:
            chunk_text = _turns_to_text(window)
            ts_start = window[0].timestamp
            ts_end = window[-1].timestamp

            chunks.append(
                Chunk(
                    chunk_id=_make_chunk_id(transcript.episode_slug, chunk_index),
                    chunk_index=chunk_index,
                    episode_slug=transcript.episode_slug,
                    chunk_text=chunk_text,
                    timestamp_range=f"{ts_start}–{ts_end}",
                    guest=transcript.guest,
                    title=transcript.title,
                    youtube_url=transcript.youtube_url,
                    video_id=transcript.video_id,
                    publish_date=transcript.publish_date,
                    keywords=transcript.keywords,
                )
            )
            chunk_index += 1

            # Compute overlap: carry forward turns that fill ~OVERLAP_CHARS
            overlap_turns = []
            overlap_chars = 0
            for t in reversed(window):
                t_len = len(f"{t.speaker} ({t.timestamp}): {t.text}")
                if overlap_chars + t_len > OVERLAP_CHARS:
                    break
                overlap_turns.insert(0, t)
                overlap_chars += t_len

            window = overlap_turns[:]
            window_chars = sum(len(f"{t.speaker} ({t.timestamp}): {t.text}") for t in window)

        window.append(turn)
        window_chars += turn_chars

    # Flush the final window
    if window:
        chunk_text = _turns_to_text(window)
        ts_start = window[0].timestamp
        ts_end = window[-1].timestamp
        chunks.append(
            Chunk(
                chunk_id=_make_chunk_id(transcript.episode_slug, chunk_index),
                chunk_index=chunk_index,
                episode_slug=transcript.episode_slug,
                chunk_text=chunk_text,
                timestamp_range=f"{ts_start}–{ts_end}",
                guest=transcript.guest,
                title=transcript.title,
                youtube_url=transcript.youtube_url,
                video_id=transcript.video_id,
                publish_date=transcript.publish_date,
                keywords=transcript.keywords,
            )
        )

    return chunks


def _chunk_raw_text(transcript: ParsedTranscript) -> list[Chunk]:
    """Fallback: fixed-size character chunking for transcripts with no parsed turns."""
    text = transcript.body_raw
    chunks = []
    i = 0
    chunk_index = 0

    while i < len(text):
        end = min(i + TARGET_CHUNK_CHARS, len(text))
        chunk_text = text[i:end]
        chunks.append(
            Chunk(
                chunk_id=_make_chunk_id(transcript.episode_slug, chunk_index),
                chunk_index=chunk_index,
                episode_slug=transcript.episode_slug,
                chunk_text=chunk_text,
                timestamp_range="",
                guest=transcript.guest,
                title=transcript.title,
                youtube_url=transcript.youtube_url,
                video_id=transcript.video_id,
                publish_date=transcript.publish_date,
                keywords=transcript.keywords,
            )
        )
        i += TARGET_CHUNK_CHARS - OVERLAP_CHARS
        chunk_index += 1

    return chunks
