# OpenDove — Tech Strategy & Implementation Plan

## Vision

OpenDove is a multi-agent autonomous development system where specialized AI agents collaborate through a strict, validation-gated pipeline to produce working software.

---

## Agent Pipeline

```
Product Manager → Project Manager → Lead Architect → Developer → AVA
                                                         ↑           |
                                                         └── reject ─┘
```

Each stage is a LangGraph node. AVA is the only gate that decides continuation.

---

## Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Orchestration | LangGraph | Native support for conditional edges, state graphs, retry loops |
| LLM | Anthropic `claude-sonnet-4-6` | Best-in-class for structured reasoning and code gen |
| Data models | Pydantic v2 | Already in use, excellent for structured LLM output |
| State persistence | PostgreSQL + SQLAlchemy 2.x | Required for durable multi-step execution |
| Migrations | Alembic | Standard SQLAlchemy migration tool |
| API | FastAPI | Async, Pydantic-native, easy to add later |
| Testing | pytest | Standard, already scaffolded |

---

## Implementation Phases

### Phase 1 — Core Execution Engine (in-memory, deterministic)

**Goal:** A runnable LangGraph graph with all 5 nodes and iteration control. No LLM calls yet — stub implementations that exercise the full state machine.

**Deliverables:**
- `src/opendove/state/memory_store.py` — `InMemoryTaskStore` implementing `TaskStore` protocol
- `src/opendove/orchestration/graph.py` — Replace stub with real LangGraph `StateGraph`
  - Node for each role: `product_manager`, `project_manager`, `lead_architect`, `developer`, `ava`
  - Conditional edges: AVA → approve (END) | reject (developer, up to max retries) | escalate (END with escalated status)
  - State type: `GraphState` (TypedDict with task, messages, retry_count)
- `src/opendove/models/task.py` — Add `max_retries: int = 3` to `Task`
- Unit tests covering: happy path (approve), rejection loop, escalation on retry limit

**Success criteria:**
- `python -m pytest tests/unit/` passes
- Graph can be instantiated and `.invoke()` called with a stubbed task
- Retry limit is enforced: task escalates after 3 rejections

---

### Phase 2 — LLM Agent Layer

**Goal:** Each role makes real LLM calls using Anthropic SDK. System prompts loaded from `prompts/` files.

**Deliverables:**
- `src/opendove/agents/base.py` — `BaseAgent` with Anthropic client, prompt loading
- `src/opendove/agents/{role}.py` — One agent per role, structured output via Pydantic
- AVA returns `ValidationResult` with `approve/reject/escalate` + `rationale`
- Update `config.py`: replace `openai_api_key` with `anthropic_api_key`
- Integration test: end-to-end run with a simple task fixture

**Success criteria:**
- Each agent can be instantiated and called independently
- AVA returns a valid `ValidationResult`
- End-to-end graph run completes (approve or reject)

---

### Phase 3 — Persistence

**Goal:** Replace in-memory store with PostgreSQL. Tasks survive process restarts.

**Deliverables:**
- `src/opendove/storage/models.py` — SQLAlchemy ORM: `TaskORM`, `ValidationResultORM`
- `src/opendove/storage/postgres_store.py` — `PostgresTaskStore` implementing `TaskStore`
- `migrations/` — Alembic env + initial migration
- Integration tests using a test database

**Success criteria:**
- `PostgresTaskStore` passes same test suite as `InMemoryTaskStore`
- Migration creates correct schema
- Task state survives process restart

---

### Phase 4 — API Surface

**Goal:** HTTP API to create, inspect, and run tasks.

**Deliverables:**
- `src/opendove/api/app.py` — FastAPI app
- Endpoints: `POST /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/run`
- `src/opendove/main.py` — Updated to start the FastAPI server

**Success criteria:**
- All endpoints return correct status codes
- Running a task via API triggers the full agent pipeline

---

## Non-Negotiable Rules (from initial_thoughts)

1. No self-approval — Dev cannot approve own work, Architect cannot bypass AVA
2. AVA is blocking — nothing is "done" without AVA approval
3. Explicit integration step — Architect validates system-level behavior
4. Iteration limits — PM enforces max retries (default: 3)
5. Clear termination — every task has success_criteria before execution starts

---

## Progress Tracker

| Phase | Status | Notes |
|---|---|---|
| Phase 1: Core Engine | ✅ Done | 7/7 unit tests pass; real langgraph wired |
| Phase 2: LLM Agents | ⏳ Pending | — |
| Phase 3: Persistence | ⏳ Pending | — |
| Phase 4: API | ⏳ Pending | — |
