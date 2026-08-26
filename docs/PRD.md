# PRD — The Lenny Growth Assistant

## 1. Discovery Brief

### 1.1 User & Problem

**Primary user**: A product manager or growth practitioner on a product team that regularly references Lenny Rachitsky's podcast for strategic decisions.

**Job to be done**: "When I face a product or growth decision, I want to quickly find what Lenny's expert guests have said about it, with enough source traceability that I can trust the answer and share it with my team."

**Pain removed**:
- **Today**: manually scrubbing through transcripts, relying on memory of which episode covered what, or asking an LLM that invents citations
- **Tomorrow**: one grounded, cited answer in seconds, convertible to publishable content without rewriting

### 1.2 Success Metrics

| Metric | Target |
|---|---|
| Grounded answer rate | ≥ 90% of queries receive a response citing at least one transcript source |
| Retrieval hit rate | ≥ 80% of PM/growth queries find at least one chunk above the similarity threshold |
| "I don't know" honesty | Out-of-corpus questions correctly decline (no hallucinated sources) |
| Ship30 pass rate | ≥ 85% of essays pass validation (word count + structure) on first generation |
| Startup time | `docker-compose up` + model pull → first answer in < 5 minutes |

### 1.3 Assumptions

1. The user is comfortable in a browser-based chat UI — no CLI or API required.
2. The primary use case is async research, not real-time collaboration (no multi-user concurrency requirements).
3. Lenny's transcript corpus is the authoritative and sufficient source — we are not integrating Lenny's newsletter or other sources in v1.
4. "Free tier" means zero mandatory ongoing cost for a single evaluator running locally — Anthropic cloud path is opt-in and clearly labelled as paid.
5. No user authentication is in scope — this is a single-operator internal tool, not a multi-tenant SaaS product.
6. The evaluator has Docker Desktop installed and ~8 GB RAM available for local model inference.

### 1.4 Scope

**Included:**
- Grounded conversational Q&A with source citations
- Ship 30 for 30 essay generation (distinct tool, enforced structure)
- Markdown and HTML artifact generation with in-app viewer
- Session-based conversation history (independent per session)
- Ollama local LLM + Anthropic Cloud LLM (switchable via env var)
- Full ingestion pipeline for Lenny's transcript corpus
- Docker Compose one-command startup

**Excluded (v1):**
- Multi-user authentication / authorization
- Lenny's newsletter content (transcripts only)
- Real-time collaboration / shared sessions
- Mobile-native app
- Custom fine-tuning of the LLM
- Voice interface

### 1.5 Risks & Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Local model hallucination | Medium | High | Retrieval-gated answers; explicit "no support" sentinel |
| Slow local inference | High | Medium | SSE streaming for perceived responsiveness |
| Embedding quality (small model) | Medium | Medium | Tunable threshold; upgrade path to larger model |
| HTML artifact XSS | Low | High | nh3 sanitization + sandboxed iframe (two independent layers) |
| Corpus drift (new episodes) | High | Low | Idempotent re-runnable ingestion; versioned by commit SHA |
| Cold-start latency (model load) | Medium | Low | Embedding model baked into Docker image |

---

## 2. Acceptance Criteria

### 2.1 Grounded Q&A
- [ ] A PM question (e.g. "How do PLG companies think about pricing?") returns an answer citing at least one Lenny episode
- [ ] The citation is clickable and links to the correct YouTube video
- [ ] A clearly out-of-corpus question (e.g. "What is the best CSS framework?") returns an honest "not in the knowledge base" response
- [ ] Follow-up questions within the same session maintain context

### 2.2 Ship 30 Essay
- [ ] Clicking "Turn into Ship 30 essay" triggers the write_ship30_essay tool
- [ ] The resulting essay is 1,000–1,500 words
- [ ] The essay has ≥ 2 ## sections and a "## The Takeaway" section
- [ ] A "Sources" section citing the transcript episodes appears at the end
- [ ] The essay appears as an artifact in the right-hand panel

### 2.3 Artifact Viewer
- [ ] Markdown artifacts render formatted text (not raw markdown)
- [ ] HTML artifacts render inside a sandboxed iframe
- [ ] Download and copy buttons work
- [ ] `<script>` tags in generated HTML are stripped before rendering

### 2.4 Configuration
- [ ] `GET /config` returns the active provider and model name
- [ ] The UI provider badge updates when the provider changes
- [ ] Switching `LLM_PROVIDER` in `.env` and restarting changes behavior with no code change

### 2.5 Resilience
- [ ] Ollama unreachable → friendly error message (not a stack trace)
- [ ] Empty retrieval → "not in knowledge base" response (not an exception)
- [ ] `/health` reports each dependency independently
