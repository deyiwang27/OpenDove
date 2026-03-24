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

## Multi-LLM Strategy

All agents use LangChain `BaseChatModel` as a unified interface. Provider selection is a config concern, not a code concern.

**Supported providers:** Anthropic, OpenAI, Gemini (via `langchain-anthropic`, `langchain-openai`, `langchain-google-genai`)

**Config resolution order (per role):**
1. Role-specific `{role}_llm_provider` / `{role}_llm_model` — if set, use this
2. Global `llm_provider` / `llm_model` — fallback default

**Environment variables:**
```
OPENDOVE_LLM_PROVIDER=anthropic          # global default provider
OPENDOVE_LLM_MODEL=claude-sonnet-4-6     # global default model
OPENDOVE_ANTHROPIC_API_KEY=...
OPENDOVE_OPENAI_API_KEY=...
OPENDOVE_GEMINI_API_KEY=...

# Per-role overrides (empty = inherit global)
OPENDOVE_ARCHITECT_LLM_PROVIDER=anthropic
OPENDOVE_ARCHITECT_LLM_MODEL=claude-opus-4-6
OPENDOVE_DEVELOPER_LLM_PROVIDER=openai
OPENDOVE_DEVELOPER_LLM_MODEL=gpt-4o
```

---

## Multi-Repo Architecture

### Top-level entities

```
Project (one per repo)
├── id, name, repo_url, default_branch
├── local_path  →  {workspace_dir}/projects/{project_id}/main/
└── status: idle | active | archived

Task (scoped to a Project)
├── ... (existing fields)
├── project_id: UUID
├── branch_name: str            e.g. feat/task-{short_id}
└── worktree_path: Path | None  {workspace_dir}/projects/{project_id}/tasks/{task_id}/
```

### Disk layout

```
~/.opendove/
└── projects/
    └── {project_id}/
        ├── main/          ← git clone (source of truth)
        └── tasks/
            └── {task_id}/ ← git worktree (isolated per task)
```

### Task scheduling rules

- **One active task per project at a time** — additional tasks are queued (FIFO)
- **Multiple projects run in parallel** — each project queue is independent
- On task completion/escalation → worktree is removed → next queued task starts

### Project onboarding flow

1. User submits `{name, repo_url}`
2. `GitManager.clone(repo_url, local_path)` — clones to `{workspace_dir}/projects/{project_id}/main/`
3. Project status set to `idle`, ready for tasks

### Task execution flow

1. `ProjectDispatcher.submit_task(project_id, task)` called
2. If project is `idle` → set active, create worktree, run LangGraph
3. If project is `active` → enqueue task
4. Developer agent writes files directly into `worktree_path`
5. On graph completion → commit changes, remove worktree, dequeue next task

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

### Phase 2a — Multi-LLM Agent Layer

**Goal:** Each role becomes a real LLM-backed agent using LangChain `BaseChatModel`. Provider and model are configurable per role.

**New dependencies:** `langchain-anthropic`, `langchain-openai`, `langchain-google-genai`

**Deliverables:**
- `src/opendove/config.py` — extended: global LLM defaults + per-role overrides + API keys for all 3 providers + `workspace_dir`
- `src/opendove/agents/llm_factory.py` — `build_llm(provider, model, **kwargs) -> BaseChatModel`; `build_llm_for_role(role, settings) -> BaseChatModel`
- `src/opendove/agents/base.py` — `BaseAgent(llm: BaseChatModel, system_prompt: str)`; async `invoke(state) -> GraphState`
- `src/opendove/agents/product_manager.py` — writes spec, returns updated Task with success_criteria
- `src/opendove/agents/project_manager.py` — sets max_retries, assigns owner
- `src/opendove/agents/lead_architect.py` — returns technical approach as task artifact
- `src/opendove/agents/developer.py` — writes code to `state["worktree_path"]`; returns artifact path
- `src/opendove/agents/ava.py` — validates against success_criteria; returns `ValidationResult`
- Update `src/opendove/orchestration/graph.py` — nodes call real agents; `GraphState` gains `project` and `worktree_path`
- Unit tests: each agent instantiates correctly; `build_llm_for_role` resolves provider/model correctly

**Success criteria:**
- `build_llm_for_role(Role.DEVELOPER, settings)` returns the correct `BaseChatModel` subclass
- Per-role override takes precedence over global default
- Agent nodes in the graph accept a `BaseChatModel` injection (for testing with mocks)

---

### Phase 2c — MCP Tool Integration

**Goal:** Equip every agent with MCP-backed tools via `langchain-mcp-adapters`. Agents become ReAct loops when tools are present; single-call when not.

**MCP servers:**
- **Claude Code MCP** — file tools (read/write/edit/glob/grep) + bash. Scoped: read within project repo, write within task worktree only.
- **CodeX MCP** — full code generation sessions (Architect prototyping, Developer implementation)
- **Brave Search MCP** — structured web search (PdM, PjM, Architect)
- **Fetch MCP** — fetch any URL as clean text (PdM, PjM, Architect, Developer, AVA)

**Tool assignment per role:**

| Role | Claude Code | CodeX | Web Search | Fetch |
|---|---|---|---|---|
| Product Manager | write spec docs | — | ✅ | ✅ |
| Project Manager | write task/progress docs | — | ✅ | ✅ |
| Lead Architect | read/grep codebase, write ADRs | ✅ | ✅ | ✅ |
| Developer | read/write/edit/bash in worktree | ✅ | — | ✅ |
| AVA | bash (run tests), read (review) | — | — | ✅ |

**Deliverables:**
- `langchain-mcp-adapters` and `mcp` added to dependencies
- `src/opendove/agents/tool_registry.py` — `MCPToolRegistry`: connects to MCP servers, loads and filters tools by role
- `src/opendove/agents/tool_config.py` — `RoleToolConfig`: maps roles to tool groups; per-role override via env (`OPENDOVE_{ROLE}_TOOLS`)
- `src/opendove/config.py` — per-role tool config settings
- `src/opendove/agents/base.py` — `tools: list[BaseTool]` injection; uses `create_react_agent` when tools present, `llm.invoke` otherwise
- Unit tests: ReAct path with fake tools; tool registry filtering

**Success criteria:**
- `BaseAgent` with no tools is backward compatible
- `MCPToolRegistry.get_tools_for_role(role)` returns correct filtered set
- All existing tests pass

---

### Phase 2b — Project Model + Git Manager + Dispatcher

**Goal:** Introduce `Project` as a first-class entity. Implement `GitManager` for repo/worktree lifecycle. Add `ProjectDispatcher` for per-project task queuing.

**Deliverables:**
- `src/opendove/models/project.py` — `ProjectStatus(Enum)`, `Project(BaseModel)` with `repo_url`, `local_path`, `status`, `active_task_id`, `task_queue: list[UUID]`
- `src/opendove/models/task.py` — add `project_id: UUID`, `branch_name: str`, `worktree_path: str`
- `src/opendove/state/project_store.py` — `ProjectStore` protocol: `create_project`, `get_project`, `update_project`, `list_projects`
- `src/opendove/state/memory_project_store.py` — `InMemoryProjectStore`
- `src/opendove/git/manager.py` — `GitManager`: `clone(repo_url, path)`, `create_worktree(repo_path, task_id, branch) -> Path`, `remove_worktree(worktree_path)`, `commit_and_push(worktree_path, message, branch)`
- `src/opendove/orchestration/dispatcher.py` — `ProjectDispatcher`: `register_project(project)`, `submit_task(project_id, task)`, `on_task_complete(project_id, task_id)`; enforces one-active-per-project, queues the rest
- Unit tests: dispatcher queuing logic (no real git); GitManager with a temp repo fixture

**Success criteria:**
- `submit_task` on an idle project starts it immediately; on a busy project queues it
- `on_task_complete` dequeues and starts the next task
- `GitManager.create_worktree` creates a real worktree in a temp git repo (integration test)

---

### Phase 3 — Persistence

**Goal:** Replace in-memory stores with PostgreSQL. Projects and tasks survive process restarts.

**Deliverables:**
- `src/opendove/storage/models.py` — SQLAlchemy ORM: `ProjectORM`, `TaskORM`, `ValidationResultORM`
- `src/opendove/storage/postgres_task_store.py` — `PostgresTaskStore` implementing `TaskStore`
- `src/opendove/storage/postgres_project_store.py` — `PostgresProjectStore` implementing `ProjectStore`
- `migrations/` — Alembic env + initial migration (projects + tasks tables)
- Integration tests using a test database

**Success criteria:**
- Both Postgres stores pass same test suite as their in-memory counterparts
- Migration creates correct schema with FK from tasks → projects
- Task and project state survive process restart

---

### Phase 4 — API Surface

**Goal:** HTTP API to register projects, submit tasks, and inspect status.

**Deliverables:**
- `src/opendove/api/app.py` — FastAPI app
- `POST /projects` — register a new project (triggers clone)
- `GET /projects/{id}` — project status + active/queued tasks
- `POST /projects/{id}/tasks` — submit a task (queued or started immediately)
- `GET /tasks/{id}` — task detail + validation result
- `src/opendove/main.py` — updated to start the FastAPI server

**Success criteria:**
- All endpoints return correct status codes
- Submitting a task via API triggers the full agent pipeline
- Second task submitted to a busy project is queued, not dropped

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
| Phase 2a: Multi-LLM Agent Layer | ✅ Done | 11/11 tests; LangChain BaseChatModel, per-role config |
| Phase 2b: Project + Git + Dispatcher | ✅ Done | 18/18 tests; multi-repo, worktrees, task queue |
| Phase 2c: MCP Tool Integration | 🔄 In Progress | issue #7; branch feat/issue-7-mcp-tool-integration |
| Phase 3: Persistence | ⏳ Pending | PostgreSQL for projects + tasks |
| Phase 4: API | ⏳ Pending | FastAPI, project + task endpoints |
