# OpenDove

An autonomous software development system where specialized AI agents collaborate through a validation-gated pipeline to deliver working software.

[![CI](https://github.com/deyiwang27/OpenDove/actions/workflows/ci.yml/badge.svg)](https://github.com/deyiwang27/OpenDove/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)

---

## What it does

You submit a task (title + intent + success criteria). OpenDove runs it through a five-role agent pipeline, validates the output against your criteria, and either merges the result automatically or escalates to a human when it gets stuck.

```
Product Manager → Project Manager → Lead Architect → Developer → AVA
                                                          ↑           │
                                                          └── reject ─┘
```

- **Product Manager** — refines success criteria so they are concrete and testable
- **Project Manager** — calibrates retry budget, assigns priority (P0/P1/P2)
- **Lead Architect** — produces a technical approach; assesses risk level
- **Developer** — implements in an isolated git worktree using MCP tools (Claude Code, CodeX)
- **AVA** — validates CI status, docs, and requirements; auto-merges low-risk work; blocks architectural changes for human review

Nothing is "done" until AVA approves it.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Outer graph  (daily trigger — issue lifecycle)         │
│  PdM scan → PjM prioritize → Architect breakdown        │
│       → [inner graph × N sub-tasks] → PjM close → PdM  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Inner graph  (per sub-task)                            │
│  PM → PjM → Architect → Developer → AVA                │
│                  ↑   reject (≤ 2 retries)   │           │
│                  └────────────────────────┘            │
│  low-risk + pass → auto-merge                          │
│  architectural   → email human + needs-human-review    │
└─────────────────────────────────────────────────────────┘
```

**Stack:**

| Layer | Choice |
|---|---|
| Orchestration | LangGraph (StateGraph) |
| Agents | LangChain `BaseChatModel` — Anthropic, OpenAI, Gemini |
| MCP tools | Claude Code, CodeX, Brave Search, Fetch |
| Persistence | PostgreSQL + SQLAlchemy 2 + Alembic |
| API | FastAPI |
| CLI | Typer + Rich |
| Scheduler | APScheduler (in-process, FastAPI lifespan) |
| Packaging | uv |

---

## Quickstart (Docker)

```bash
git clone https://github.com/deyiwang27/OpenDove.git
cd OpenDove

cp .env.example .env
# Edit .env — set OPENDOVE_ANTHROPIC_API_KEY and OPENDOVE_GITHUB_TOKEN

docker compose up --build
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

See [docs/runbook.md](docs/runbook.md) for the full walkthrough.

---

## CLI

```bash
# Install (outside Docker)
uv sync
uv run opendove --help

# Register a project
opendove project add my-project https://github.com/org/repo.git

# Submit a task
opendove task submit <project-id> \
  --title "Add rate limiting to the API" \
  --intent "Protect all endpoints with a 100 req/min per-IP limit" \
  --criteria "Returns 429 when limit exceeded" \
  --criteria "X-RateLimit-Remaining header present on all responses" \
  --risk low

# Check status
opendove task status <task-id>
opendove project list
```

---

## Multi-LLM configuration

All agents use `BaseChatModel` — swap providers without touching code.

```env
# Global default
OPENDOVE_LLM_PROVIDER=anthropic
OPENDOVE_LLM_MODEL=claude-sonnet-4-6

# Per-role override (empty = inherit global)
OPENDOVE_ARCHITECT_LLM_PROVIDER=anthropic
OPENDOVE_ARCHITECT_LLM_MODEL=claude-opus-4-6
OPENDOVE_DEVELOPER_LLM_PROVIDER=openai
OPENDOVE_DEVELOPER_LLM_MODEL=gpt-4o
```

Supported providers: `anthropic`, `openai`, `gemini`.

---

## Repository layout

```
src/opendove/
├── agents/          # Agent implementations + schemas + LLM factory
│   ├── base.py      # BaseAgent with _call_llm_structured()
│   ├── schemas.py   # Pydantic output contracts per role
│   ├── ava.py       # AVA: CI gate, doc check, auto-merge
│   └── ...
├── api/             # FastAPI app, routers, schemas, dependencies
├── cli/             # Typer CLI (opendove project/task commands)
├── config.py        # Pydantic settings (OPENDOVE_* env vars)
├── git/             # GitManager: clone, worktree, commit/push
├── github/          # GitHubClient: issues, PRs, CI status, merge
├── models/          # Task, Project, Role, TaskStatus
├── notifications/   # NotificationService (email + Discord-ready)
├── orchestration/   # LangGraph graphs, TaskRunner, dispatcher
├── scheduler/       # APScheduler wrapper, IssueSyncer, FeedbackIngestor
├── state/           # Store protocols + in-memory implementations
├── storage/         # SQLAlchemy ORM + PostgreSQL stores
└── validation/      # ValidationResult, ValidationDecision

migrations/          # Alembic migrations
tests/
├── integration/     # Full-pipeline tests with fake agents
└── unit/            # Per-component tests
```

---

## Development

```bash
uv sync --extra dev
uv run python -m pytest tests/unit/        # fast (no DB required)
uv run python -m pytest tests/             # full suite (postgres tests skip without DB)
uv run ruff check .
```

---

## Docs

- [Runbook](docs/runbook.md) — setup, first run, troubleshooting
- [Tech Strategy](docs/architecture/tech_strategy.md) — implementation phases and progress tracker
- [Architecture](docs/architecture.md) — system design overview
- [Principles](docs/principles.md) — non-negotiable rules
- [Roadmap](docs/roadmap.md) — product direction

---

## Non-negotiable rules

1. **No self-approval** — the Developer cannot approve its own work; AVA is a separate gate
2. **AVA is blocking** — nothing is "done" without AVA approval
3. **Explicit integration step** — the Architect validates system-level behaviour before Developer ships
4. **Iteration limits** — PjM enforces max retries (default: 3); escalates rather than looping forever
5. **Clear termination** — every task has `success_criteria` before execution starts
