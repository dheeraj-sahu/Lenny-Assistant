# Architecture — The Lenny Growth Assistant

## 1. System Overview

```
┌──────────────────────────────── CLIENT (Browser) ────────────────────────────────┐
│  SessionSidebar (React)    ChatPanel (React)         ArtifactViewer (React)       │
│  • Session list            • Message thread           • MarkdownRenderer           │
│  • New chat button         • SSE stream handling      • SandboxedHtmlFrame         │
│  • Provider indicator      • "Turn into Ship30" btn   • Download/Copy actions      │
└────────────────────────────────── REST / SSE ─────────────────────────────────────┘
                                        │
                               ┌────────▼────────┐
                               │  FastAPI :8000   │
                               │  (uvicorn)       │
                               └────────┬─────────┘
                    ┌───────────────────┼────────────────────┐
                    │                   │                    │
             ┌──────▼──────┐   ┌────────▼────────┐  ┌───────▼────────┐
             │  API Layer   │   │  Session/Msg    │  │  Agent         │
             │  routes_*    │   │  Service        │  │  Orchestrator  │
             │  schemas_*   │   │  (repositories) │  │  (Claude SDK)  │
             └─────────────┘   └────────┬─────────┘  └───────┬────────┘
                                        │                    │
                               ┌────────▼─────────┐  ┌───────▼────────────┐
                               │   PostgreSQL      │  │  Tools             │
                               │   sessions        │  │  search_transcripts│
                               │   messages        │  │  write_ship30_essay│
                               │   artifacts       │  │  generate_artifact │
                               │   ingestion_runs  │  └───────┬────────────┘
                               └───────────────────┘          │
                                                     ┌────────▼──────────┐
                                                     │  Retrieval Service │
                                                     │  (embed → search) │
                                                     └────────┬──────────┘
                                                              │
                                                     ┌────────▼──────────┐
                                                     │   Qdrant :6333    │
                                                     │  (transcript      │
                                                     │   chunks + meta)  │
                                                     └────────┬──────────┘
                                                              ▲
                                                     ┌────────┴──────────┐
                                                     │  Ingestion        │
                                                     │  Pipeline (CLI)   │
                                                     │  fetch→parse→     │
                                                     │  chunk→embed→     │
                                                     │  upsert           │
                                                     └────────┬──────────┘
                                                              ▲
                                              GitHub: ChatPRD/lennys-podcast-transcripts
```

---

## 2. Component Boundaries

### 2.1 API Layer (`backend/api/`)
- **Responsibility**: HTTP surface only — routing, Pydantic validation, structured error responses
- **Does NOT**: contain business logic, SQL, or LLM calls
- **Key files**: `routes_sessions.py`, `routes_messages.py`, `routes_artifacts.py`, `routes_health.py`

### 2.2 Agent Orchestrator (`backend/agent/`)
- **Responsibility**: Claude Agent SDK multi-turn loop, tool dispatch, streaming
- **Inputs**: session history + user message
- **Outputs**: async generator of SSE events (`token`, `sources`, `artifact_id`, `done`)
- **Provider isolation**: `provider_resolver.py` is the ONLY place that branches on `ollama` vs `anthropic`

### 2.3 Retrieval Service (`backend/retrieval/`)
- **Responsibility**: pure function `(query, topic_hint?) → RetrievalResult`
- **Has no knowledge of**: sessions, messages, HTTP, or the agent
- **Reusable**: can be called from any future surface (Slack bot, API, etc.)

### 2.4 Ingestion Pipeline (`backend/ingestion/`)
- **Responsibility**: offline, idempotent job populating Qdrant
- **Idempotency**: deterministic chunk IDs (`hash(slug + index)`) → re-run = upsert, never duplicate
- **Triggered by**: CLI (`python -m ingestion.cli`) or HTTP (`POST /admin/refresh-kb`)

### 2.5 Artifact Service (`backend/artifacts/`)
- **Responsibility**: classify → sanitize → persist (raw + sanitized)
- **Key rule**: raw content is stored for audit; only sanitized_content is ever returned via API

### 2.6 Persistence Layer (`backend/persistence/`)
- **Pattern**: Repository per entity (Session, Message, Artifact)
- **Async**: all DB calls use `asyncpg` + SQLAlchemy async engine
- **Migrations**: Alembic tracks schema changes

---

## 3. Database Schema

```sql
-- sessions: one per chat conversation
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(512),
    active_provider VARCHAR(64) NOT NULL DEFAULT 'ollama',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- messages: one per user/assistant turn
CREATE TABLE messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role              VARCHAR(32) NOT NULL,            -- 'user' | 'assistant'
    content           TEXT NOT NULL,
    sources           JSONB,                           -- [{guest, title, url, timestamp, score}]
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    latency_ms        INTEGER,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- artifacts: generated Markdown/HTML documents
CREATE TABLE artifacts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID REFERENCES sessions(id) ON DELETE CASCADE,
    message_id        UUID REFERENCES messages(id) ON DELETE SET NULL,
    artifact_type     VARCHAR(32) NOT NULL,            -- 'markdown' | 'html'
    title             VARCHAR(512),
    raw_content       TEXT NOT NULL,                   -- original LLM output
    sanitized_content TEXT NOT NULL,                   -- served to frontend
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- ingestion_runs: audit log of KB refresh jobs
CREATE TABLE ingestion_runs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_commit_sha VARCHAR(64),
    episode_count     INTEGER,
    chunk_count       INTEGER,
    status            VARCHAR(32) DEFAULT 'running',
    started_at        TIMESTAMPTZ DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    error_message     TEXT
);
```

---

## 4. Qdrant Vector Schema

Each point in the `lenny_transcripts` collection:

```json
{
  "id": "<uint64 — hash(episode_slug + chunk_index)>",
  "vector": [/* 384-dim float32 from all-MiniLM-L6-v2 */],
  "payload": {
    "chunk_text":      "Nick Turley (00:12:34): The thing about...",
    "episode_slug":    "nick-turley",
    "chunk_index":     3,
    "timestamp_range": "00:12:34–00:17:45",
    "guest":           "Nick Turley",
    "title":           "Building ChatGPT's First Product",
    "youtube_url":     "https://youtube.com/watch?v=...",
    "video_id":        "abc123",
    "publish_date":    "2024-01-15",
    "keywords":        ["product", "ai", "growth"],
    "corpus_version":  "a1b2c3d4"
  }
}
```

**Retrieval parameters:**
- Distance metric: Cosine similarity
- Default top-k: 8
- Default score threshold: 0.35 (returns sentinel if best match < 0.35)

---

## 5. Agent Routing

```
User message
    │
    ▼
Agent (Claude SDK) — system_prompt instructs retrieval-first behavior
    │
    ├─ tool_use: search_transcripts(query, topic_hint?)
    │       │
    │       └─ RetrievalService.retrieve()
    │               → Qdrant similarity search
    │               → Returns chunks OR "no content found" sentinel
    │
    ├─ tool_use: write_ship30_essay(topic, grounded_context)
    │       │
    │       └─ Dedicated Ship30 system prompt (NOT the chat prompt)
    │               → Validate word count / structure
    │               → Re-prompt once if validation fails
    │
    ├─ tool_use: generate_artifact(content, artifact_type)
    │       │
    │       └─ ArtifactService.create_artifact()
    │               → classify type
    │               → sanitize (nh3 for HTML, passthrough for Markdown)
    │               → persist raw + sanitized
    │               → return artifact_id
    │
    └─ end_turn → final text response → streamed as SSE tokens
```

---

## 6. Model Toggle

```
LLM_PROVIDER=ollama          LLM_PROVIDER=anthropic
       │                             │
       ▼                             ▼
anthropic.Anthropic(           anthropic.Anthropic(
  base_url=http://ollama:11434,  api_key=ANTHROPIC_API_KEY
  api_key="ollama"             )
)
       │                             │
       └──────────┬──────────────────┘
                  ▼
         Same SDK call:
         client.messages.stream(
           model=..., system=..., messages=..., tools=...
         )
```

The agent orchestrator, tools, and skills have **zero branching on provider name**.

---

## 7. Security Model

### 7.1 HTML Artifact Security (two layers)

**Layer 1 — Server-side sanitization (nh3, before storage):**
- Strips: `<script>`, inline event handlers (`onclick=`, etc.), `<iframe>`, `<object>`, `<embed>`
- Blocks: `javascript:` URIs, `data:` URIs in href/src
- Allows: standard structural/formatting HTML, safe CSS classes, http/https links

**Layer 2 — Client-side sandboxed iframe (`sandbox="allow-scripts"`):**

| Capability | Status |
|---|---|
| Styling / layout / CSS | ✅ Allowed |
| Client-side JS (iframe-scoped) | ✅ Allowed (`allow-scripts`) |
| Reading parent page DOM / cookies | ❌ Blocked (no `allow-same-origin`) |
| Making authenticated requests to backend | ❌ Blocked (no same-origin access) |
| Navigating parent page | ❌ Blocked (no `allow-top-navigation`) |
| Opening new windows | ❌ Blocked (no `allow-popups`) |
| Form submission to external origins | ❌ Blocked |

**Residual risk**: No client-side sandbox is perfect. A sufficiently clever exploit against the browser's iframe sandbox implementation could bypass these controls. This is documented as a residual risk and accepted: the primary mitigation is server-side sanitization ensuring malicious scripts never reach the iframe in the first place.

### 7.2 Prompt Injection Defense

Transcript chunks are passed as **tool output** (structured data), not as system prompt text. The system prompt explicitly instructs the agent to treat retrieved content as data and ignore any instruction-looking text within it.

### 7.3 Secret Management

- `.env` is git-ignored; only `.env.example` with placeholder values is committed
- API keys are never logged (structlog config strips key-like values)
- Admin endpoint protected by `X-Admin-Secret` header

---

## 8. Deployment Topology

```
docker-compose.yml
├── postgres    (postgres:16-alpine)      :5432
├── qdrant      (qdrant/qdrant:v1.9.2)    :6333/:6334
├── ollama      (ollama/ollama:latest)    :11434
├── backend     (custom Python 3.11)      :8000
└── frontend    (node:20-alpine + Vite)   :5173
```

**Startup order**: postgres → qdrant → ollama → backend (waits for all three healthy) → frontend

**Volumes**: postgres-data, qdrant-data, ollama-data, transcripts-data (all Docker-managed)

---

## 9. Observability

All log lines are structured JSON (structlog):

```json
{
  "event": "retrieval_complete",
  "request_id": "uuid",
  "query_preview": "how does Figma think about pricing",
  "results_count": 6,
  "top_score": 0.781,
  "latency_ms": 42,
  "timestamp": "2026-08-26T00:00:00Z",
  "level": "info"
}
```

Health endpoint independently reports each dependency:
```json
{
  "status": "degraded",
  "components": {
    "database": {"status": "ok"},
    "qdrant": {"status": "down", "error": "Connection refused"},
    "ollama": {"status": "ok"}
  }
}
```
