# Lenny Growth Assistant

An AI assistant grounded in **300+ Lenny's Podcast transcripts**. Ask product and growth questions, get cited answers, convert them to Ship 30 for 30 essays, and render content as live HTML artifacts — all running locally with zero mandatory cloud costs.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Grounded Q&A** | All answers cite real Lenny's Podcast episodes with guest, title, timestamp, and YouTube link |
| 🚫 **Honest "I don't know"** | If the knowledge base has no relevant content, the assistant says so plainly |
| ✍️ **Ship 30 for 30 Essays** | One-click conversion of any answer into a structured ~1,250-word publishable essay |
| 🖥️ **HTML Artifact Viewer** | Renders AI-generated HTML in a sandboxed iframe (sanitized, isolated from parent page) |
| 📄 **Markdown Artifact Viewer** | Renders structured documents with copy and download buttons |
| ⚡ **Local LLM (Ollama)** | Runs entirely free on your machine — no API key required |
| ☁️ **Cloud LLM (Anthropic)** | Switch to Claude with one click and your own API key — no restart needed |
| 💬 **Session history** | Multiple independent chat sessions, each with full conversation context |
| 📌 **Source citation chips** | Clickable chips link directly to the YouTube episode at the cited timestamp |

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI (Python 3.11) |
| Agent | Anthropic Claude Agent SDK (works with Ollama locally) |
| Vector DB | Qdrant (self-hosted) |
| Relational DB | PostgreSQL 16 |
| Embedding model | `all-MiniLM-L6-v2` (sentence-transformers, runs locally) |
| LLM (local) | Ollama (`qwen2.5:1.5b` or any model you have pulled) |
| LLM (cloud, optional) | Anthropic Claude API |
| Containers | Docker + Docker Compose |

---

## ⚡ Prerequisites

Before running, ensure you have:

1. **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/)
2. **Ollama** — [download](https://ollama.com/download) *(for local LLM)*
3. **Node.js 20+** — only needed if running the frontend outside Docker
4. A model pulled in Ollama:

```powershell
ollama pull qwen2.5:1.5b
```

> You can use any model you already have. Check what's available: `ollama ls`

---

## 🚀 Quick Start (Docker — Recommended)

### Step 1 — Clone & configure

```powershell
git clone <your-repo-url>
cd <cloned-directory>
```

Copy the example environment file and fill in your values:

```powershell
Copy-Item backend\.env.example backend\.env
```

Open `backend\.env` and set at minimum:

```env
# Required — your PostgreSQL password
POSTGRES_PASSWORD=YourPasswordHere

# Required — must match above, URL-encode special characters
# e.g. if password is Abc@123, encode @ as %40 → Abc%40123
DATABASE_URL=postgresql+asyncpg://lenny:YourPasswordHere@postgres:5432/lenny_assistant

# Your Ollama model name (must be pulled locally)
OLLAMA_MODEL=qwen2.5:1.5b

# Optional — only needed if you want to use Claude from the UI
ANTHROPIC_API_KEY=sk-ant-api03-...
```

> **Password with special characters?** URL-encode them in `DATABASE_URL`:
> `@` → `%40`, `#` → `%23`, `$` → `%24`

### Step 2 — Start all services

```powershell
docker-compose up --build
```

This starts: **PostgreSQL**, **Qdrant**, **FastAPI backend**, **React frontend**

Wait until you see:
```
lenny-backend  | INFO: Application startup complete.
```

### Step 3 — Populate the knowledge base

Open a **new** PowerShell window and run:

```powershell
$headers = @{ "X-Admin-Secret" = "changeme-admin-secret" }
Invoke-RestMethod -Uri "http://localhost:8000/admin/refresh-kb" -Method POST -Headers $headers
```

This clones the Lenny's Podcast transcript repository and indexes ~273 episodes into Qdrant. It runs in the background — check progress with:

```powershell
docker logs lenny-backend --follow
```

Wait until you see `"event": "ingestion_complete"` in the logs.

### Step 4 — Open the app

Navigate to **http://localhost:5173** in your browser.

---

## 🖥️ Running the Frontend Separately (Development)

If you want hot-reload for the frontend while the backend runs in Docker:

```powershell
# Terminal 1 — backend + services
docker-compose up

# Terminal 2 — frontend dev server
cd frontend
npm install
npm run dev
```

Frontend will be at **http://localhost:5173**, proxying API calls to `http://localhost:8000`.

---

## 🔑 Switching LLM Providers (No Restart Needed)

Click the **provider badge** (top-right of the chat header) to open the model switcher:

- **⚡ Local · Ollama** — zero cost, runs on your machine, one click
- **☁️ Cloud · Anthropic** — paste your `sk-ant-api03-...` key in the input field, click **"Use Claude →"**

The switch is immediate and in-memory. It resets when the container restarts. To make it permanent, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` in `backend/.env` and restart.

---

## 📂 Project Structure

```
take_home_assignment/
├── backend/
│   ├── agent/          # Claude Agent SDK orchestrator + tools
│   ├── api/            # FastAPI route handlers
│   ├── app/            # App factory, config, lifespan
│   ├── core/           # Logging, shared utilities
│   ├── ingestion/      # Transcript fetch → parse → chunk → embed → upsert
│   ├── persistence/    # SQLAlchemy models, Alembic migrations, DB engine
│   ├── retrieval/      # Qdrant client wrapper + embedding service
│   ├── schemas/        # Pydantic request/response models
│   ├── skills/         # Ship 30 for 30 writing skill
│   ├── tests/          # pytest test suite
│   ├── docker/         # Backend Dockerfile
│   ├── .env.example    # ← copy this to .env and fill in values
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/        # API clients (sessions, messages, artifacts)
│   │   ├── components/ # Chat, Sidebar, ArtifactViewer, ProviderBadge
│   │   └── styles/     # Global CSS design system
│   └── vite.config.ts
├── docs/
│   ├── architecture.md # System architecture & data flow
│   ├── design.md       # UI/UX design decisions
│   └── PRD.md          # Product requirements document
├── docker-compose.yml
└── README.md           # ← you are here
```

---

## 🔧 Useful Commands

### Check service health
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

### View active configuration
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/config"
```

### View backend logs (live)
```powershell
docker logs lenny-backend --follow
```

### Re-index transcripts (after new episodes are published)
```powershell
$headers = @{ "X-Admin-Secret" = "changeme-admin-secret" }
Invoke-RestMethod -Uri "http://localhost:8000/admin/refresh-kb" -Method POST -Headers $headers
```

### Stop everything and remove volumes (full reset)
```powershell
docker-compose down -v
```

### Stop without removing data
```powershell
docker-compose down
```

### Restart just the backend
```powershell
docker-compose restart backend
```

---

## 🌡️ Troubleshooting

| Problem | Fix |
|---|---|
| `password authentication failed for user "lenny"` | Your `POSTGRES_PASSWORD` and `DATABASE_URL` are out of sync in `backend/.env`. Make sure they match and URL-encode special characters (`@` → `%40`). Then run `docker-compose down -v && docker-compose up` |
| Backend crashes immediately | Run `docker logs lenny-backend` to see the error. Most common cause: mismatched DB credentials |
| Ollama unreachable | Ensure Ollama is running on your host: `ollama serve`. The backend connects via `host.docker.internal:11434` |
| Knowledge base empty / no answers | Run the ingestion command in Step 3. Check logs for `ingestion_complete` |
| HTML not rendering in right panel | Click the green **🖥️ Render as HTML** button that appears below any assistant message containing HTML code |
| Port 5432 already in use | Another PostgreSQL is running on your host. The docker-compose maps to port `5433` on the host — this is already handled |

---

## 🔒 Security Notes

- `backend/.env` is **git-ignored** — never commit it
- Anthropic API keys entered in the UI are stored **in-memory only** and reset on restart
- HTML artifacts are **sanitized server-side** (removes `<script>`, inline event handlers, external resources) and then rendered in a **sandboxed `<iframe>`** that cannot access the parent page, cookies, or make network calls

---

## 📜 License

This project was built as a take-home engineering assignment. All transcript content belongs to Lenny's Podcast and is sourced from the public [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts) repository.
