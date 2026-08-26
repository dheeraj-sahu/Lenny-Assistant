"""
ingestion/parse_transcript.py

Parses a single transcript.md file from the lennys-podcast-transcripts repo.

Each file has:
  1. A YAML-like metadata table at the top with fields:
     guest, title, youtube_url, video_id, publish_date, duration_seconds,
     duration, view_count, channel, keywords
  2. The transcript body: speaker-attributed, timestamped paragraphs
     e.g. "Speaker Name (HH:MM:SS): text"

Returns a typed ParsedTranscript dataclass.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpeakerTurn:
    """A single timestamped speaker utterance."""
    speaker: str
    timestamp: str      # "HH:MM:SS"
    text: str


@dataclass
class ParsedTranscript:
    """Parsed representation of one transcript file."""
    episode_slug: str           # e.g. "nick-turley"
    guest: str
    title: str
    youtube_url: str
    video_id: str
    publish_date: str
    duration_seconds: int
    duration: str
    view_count: int
    channel: str
    keywords: list[str]
    description: str
    body_raw: str               # full transcript body text
    speaker_turns: list[SpeakerTurn]


# ── Regex patterns ────────────────────────────────────────────────────────────

# Matches "Speaker Name (HH:MM:SS):" lines in the transcript body
_SPEAKER_LINE = re.compile(
    r"^(?P<speaker>[^\(]+)\s*\((?P<ts>\d{1,2}:\d{2}:\d{2})\)\s*:\s*",
    re.MULTILINE,
)

# Matches metadata key-value lines like "| **guest** | Nick Turley |"
# Also handles plain "key: value" frontmatter style
_META_TABLE_ROW = re.compile(r"\|\s*\*?\*?(\w+)\*?\*?\s*\|\s*(.+?)\s*\|")
_META_PLAIN = re.compile(r"^(\w[\w_]*)\s*:\s*(.+)$", re.MULTILINE)


def _parse_metadata(content: str) -> dict:
    """
    Extract metadata from the first section of the file.
    Handles both markdown-table format and plain key:value frontmatter.
    """
    meta: dict = {}

    # Try markdown table format first
    for match in _META_TABLE_ROW.finditer(content[:3000]):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        meta[key] = value

    # Fallback: plain key: value pairs (YAML-ish)
    if "guest" not in meta:
        for match in _META_PLAIN.finditer(content[:3000]):
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            meta[key] = value

    return meta


def _parse_keywords(raw: str) -> list[str]:
    """Parse a comma-separated or bracket-enclosed keyword string."""
    raw = raw.strip("[]'\"")
    return [k.strip().strip("'\"") for k in raw.split(",") if k.strip()]


def _parse_speaker_turns(body: str) -> list[SpeakerTurn]:
    """Split the transcript body into individual speaker turns."""
    turns = []
    matches = list(_SPEAKER_LINE.finditer(body))

    for i, match in enumerate(matches):
        speaker = match.group("speaker").strip()
        timestamp = match.group("ts")
        # Text runs from end of this match to start of next (or end of body)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[start:end].strip()
        if text:
            turns.append(SpeakerTurn(speaker=speaker, timestamp=timestamp, text=text))

    return turns


def parse_transcript_file(file_path: Path, episode_slug: str) -> ParsedTranscript:
    """
    Parse a single transcript.md file.

    Args:
        file_path:     Path to the transcript.md file.
        episode_slug:  Guest-slug directory name (e.g. "nick-turley").

    Returns:
        ParsedTranscript dataclass.
    """
    content = file_path.read_text(encoding="utf-8", errors="replace")

    # Split: everything before the first speaker line is considered "header/metadata"
    first_speaker = _SPEAKER_LINE.search(content)
    header = content[: first_speaker.start()] if first_speaker else content
    body = content[first_speaker.start() :] if first_speaker else ""

    meta = _parse_metadata(header)

    return ParsedTranscript(
        episode_slug=episode_slug,
        guest=meta.get("guest", episode_slug),
        title=meta.get("title", ""),
        youtube_url=meta.get("youtube_url", ""),
        video_id=meta.get("video_id", ""),
        publish_date=meta.get("publish_date", ""),
        duration_seconds=int(float(meta.get("duration_seconds", 0) or 0)),
        duration=meta.get("duration", ""),
        view_count=int(float(meta.get("view_count", 0) or 0)),
        channel=meta.get("channel", ""),
        keywords=_parse_keywords(meta.get("keywords", "")),
        description=meta.get("description", ""),
        body_raw=body,
        speaker_turns=_parse_speaker_turns(body),
    )


def discover_episodes(transcripts_root: Path) -> list[tuple[str, Path]]:
    """
    Walk the episodes/ directory and return (slug, transcript_path) pairs.
    """
    episodes_dir = transcripts_root / "episodes"
    if not episodes_dir.exists():
        return []

    results = []
    for guest_dir in sorted(episodes_dir.iterdir()):
        if not guest_dir.is_dir():
            continue
        transcript_file = guest_dir / "transcript.md"
        if transcript_file.exists():
            results.append((guest_dir.name, transcript_file))

    return results
