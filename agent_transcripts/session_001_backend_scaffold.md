# Agent Transcripts

This folder contains logs of AI coding agent sessions used to build this project.

## Session 001 — Initial Backend Scaffold

**Tool**: Antigravity (Claude Sonnet 4.6)  
**Goal**: Implement full backend from solution design document  
**Date**: 2026-08-26

### Key decisions made during this session:

1. **Agent SDK approach**: Used Anthropic Python SDK's `.messages.stream()` method for the agent loop rather than a higher-level agent framework. This gives fine-grained control over tool dispatch and SSE streaming while staying within a single Python process.

2. **SSE architecture**: The streaming response uses `StreamingResponse` + an async generator in FastAPI. Each tool call result is awaited before continuing the loop, which means the agent's "thinking" (tool calls) doesn't produce visible tokens but the final synthesis does.

3. **Retrieval threshold tuning**: Set `score_threshold=0.35` as the default. This was chosen conservatively — too high causes many valid queries to miss; too low returns irrelevant chunks. The value is configurable via `RETRIEVAL_SCORE_THRESHOLD` env var.

4. **Ingestion idempotency**: Used `hash(episode_slug + chunk_index)` mapped to a uint64 as the Qdrant point ID. This allows re-running ingestion after a `git pull` to update changed episodes without creating duplicates.

5. **Ship30 validation**: The validator is intentionally lenient (1,000–1,500 words rather than exactly 1,250) to account for model variability. One automatic correction attempt is made before returning the essay regardless.

### Issues encountered and resolved:

- **Issue**: `setuptools.backends.legacy:build` not available in older setuptools version on test machine
  - **Fix**: Changed to standard `setuptools.build_meta` backend in `pyproject.toml`

- **Issue**: SQLite doesn't support `UUID` type natively — tests using SQLite fail on UUID columns  
  - **Fix**: Tests use `aiosqlite` which handles UUID via string conversion; models use `UUID(as_uuid=True)` which SQLAlchemy handles transparently

- **Issue**: Alembic async support requires `run_sync` wrapper  
  - **Fix**: Used `conn.run_sync(lambda sync_conn: context.configure(...))` pattern in `alembic/env.py`
