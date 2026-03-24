# OpenDove Runbook

End-to-end guide for running OpenDove locally using Docker Compose.

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Docker | 24.x | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled with Docker Desktop) | — |
| Git | any | — |
| An LLM API key | — | Anthropic / OpenAI / Gemini |

---

## 1. Clone and configure

```bash
git clone https://github.com/deyiwang27/OpenDove.git
cd OpenDove

cp .env.example .env
```

Open `.env` and set at minimum:

```env
OPENDOVE_ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI / GEMINI key
OPENDOVE_GITHUB_TOKEN=ghp_...           # required for repo + issue management
```

Everything else has a sensible default. See `.env.example` for the full reference.

---

## 2. Start the system

```bash
docker compose up --build
```

On first run this will:
1. Build the app image (≈ 2 min)
2. Start PostgreSQL and wait for it to be healthy
3. Run Alembic migrations (`alembic upgrade head`)
4. Start the FastAPI server on port 8000

You should see:

```
app-1  | INFO:     Application startup complete.
app-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify it's healthy:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

## 3. Register a project

OpenDove works against a GitHub repository. Register one with:

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "repo_url": "https://github.com/your-org/your-repo.git",
    "default_branch": "main"
  }'
```

Response:

```json
{
  "id": "3f2e1a...",
  "name": "my-project",
  "status": "idle",
  "active_task_id": null,
  "queued_task_count": 0
}
```

Save the `id` — you'll need it to submit tasks.

---

## 4. Submit a task

```bash
PROJECT_ID="3f2e1a..."   # from step 3

curl -X POST http://localhost:8000/projects/$PROJECT_ID/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Add a health endpoint",
    "intent": "Add GET /health that returns {\"status\": \"ok\"} with HTTP 200.",
    "success_criteria": [
      "GET /health returns HTTP 200",
      "Response body is {\"status\": \"ok\"}",
      "Unit test for the endpoint passes"
    ],
    "owner": "developer",
    "max_retries": 3,
    "risk_level": "low"
  }'
```

The task is accepted immediately (HTTP 202) and the agent pipeline starts in the background.

---

## 5. Observe progress

**Task status:**

```bash
TASK_ID="..."   # from the submit response

curl http://localhost:8000/tasks/$TASK_ID
```

Status values: `pending` → `in_progress` → `awaiting_validation` → `approved` | `rejected` | `escalated`

**App logs (live):**

```bash
docker compose logs -f app
```

**Database (optional):**

```bash
docker compose exec db psql -U opendove -d opendove
\dt          -- list tables
SELECT id, title, status FROM tasks ORDER BY created_at DESC LIMIT 10;
```

---

## 6. Trigger a manual GitHub issue sync

If you have `OPENDOVE_GITHUB_TOKEN` set and issues labelled `opendove` in your repo:

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/sync
```

This pulls open issues and creates tasks for any that haven't been synced yet.

---

## 7. Stop and clean up

```bash
# Stop containers, keep volumes (data survives restart)
docker compose down

# Stop and delete all data
docker compose down -v
```

---

## Troubleshooting

### App exits immediately on startup

Check logs for migration errors:

```bash
docker compose logs app
```

Common cause: database not yet ready. The healthcheck retries 10 times with 5s intervals — if PostgreSQL is slow to initialise on your machine, increase `retries` in `docker-compose.yml`.

### `alembic upgrade head` fails with "relation already exists"

Your database has a partial schema from a previous run. Easiest fix:

```bash
docker compose down -v   # wipes the postgres volume
docker compose up
```

### LLM calls fail with authentication errors

Verify your API key is set in `.env`:

```bash
grep OPENDOVE_ANTHROPIC_API_KEY .env
```

Make sure there are no trailing spaces and the key is not quoted.

### Tasks stay in `pending` forever

The scheduler runs on a timer. Check that the app started cleanly:

```bash
curl http://localhost:8000/health
docker compose logs app | grep "scheduler"
```

If the scheduler failed to start, restart the app: `docker compose restart app`.

### Port 8000 already in use

Change the host port in `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"   # use 8080 instead
```

---

## Running without Docker (local development)

```bash
# Install dependencies
uv sync --extra dev

# Start PostgreSQL (any method — Docker, Homebrew, etc.)
# then set the connection string:
export OPENDOVE_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/opendove"

# Run migrations
uv run alembic upgrade head

# Start the server
uv run python -m opendove.main

# Run tests
uv run python -m pytest tests/unit/
```
