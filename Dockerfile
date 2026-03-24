# syntax=docker/dockerfile:1
# ── Stage 1: dependency resolution ──────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests only — maximises layer cache reuse
COPY pyproject.toml uv.lock* ./

# Install all runtime deps (no dev extras) into the venv
RUN uv sync --no-dev --frozen

# ── Stage 2: application image ───────────────────────────────────────────────
FROM python:3.12-slim AS app

WORKDIR /app

# uv binary needed at runtime for `uv run` invocations (e.g. migrations)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy venv built in stage 1
COPY --from=deps /app/.venv /app/.venv

# Copy source
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY pyproject.toml uv.lock* alembic.ini* ./

# Activate the venv for all subsequent RUN / CMD invocations
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "-m", "opendove.main"]
