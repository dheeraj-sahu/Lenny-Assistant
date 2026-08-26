# Backend Dockerfile
# Multi-stage build: slim final image with only runtime dependencies

FROM python:3.11-slim AS base

# System deps for asyncpg, sentence-transformers, and gitpython
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependency installation stage ─────────────────────────────────────────────
FROM base AS builder

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[dev]"

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM base AS runtime

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create data directory for transcript repo
RUN mkdir -p /app/data/transcripts

# Pre-download the embedding model so it's baked into the image
# (avoids download on first request)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

# Run database migrations then start the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
