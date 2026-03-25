# Phase 1 — Contribution Mode Core Pipeline

## Goal

Deliver a working end-to-end contribution mode pipeline:
PdM selects an issue → pipeline implements it → PR is created → poller tracks it → DB is updated.

No PdM session interface, no autonomous mode, no milestone management, no email notifications.

---

## Out of Scope for Phase 1

- Autonomous mode (PdM research, issue creation, user session)
- GitHub sub-issues (contribution mode uses internal sub-tasks only)
- PdM acceptance review (no PdM in contribution mode pipeline)
- Email / Discord notifications
- Dashboard
- Daily token budget enforcement (tracked but not enforced)
- Parallel task conflict detection

---

## Deliverables

### 1. Project model — mode field

**File:** `src/opendove/models/project.py`

Add `mode: Literal["contribution", "autonomous"] = "contribution"` to the `Project` model.

**API:** `POST /projects` body accepts `mode`. `GET /projects` and `GET /projects/{id}` return it.

---

### 2. Task status — full lifecycle

**File:** `src/opendove/models/task.py`

Replace current `TaskStatus` with:

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    PENDING_EXTERNAL_REVIEW = "pending_external_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CLOSED = "closed"
```

---

### 3. Retry counters on Task model

**File:** `src/opendove/models/task.py`

Add independent retry counters:

```python
precheck_retry_count: int = 0
architect_review_retry_count: int = 0
external_review_retry_count: int = 0
```

These are independent of the existing `retry_count` (which tracks Developer retries).

---

### 4. Worktree lifecycle — keep alive while PR is open

**File:** `src/opendove/orchestration/worker.py`

Current behaviour: worktree is always removed in the `finally` block.

New behaviour:
- If task status is `PENDING_EXTERNAL_REVIEW` → do **not** remove the worktree
- Worktree is removed only when the poller marks the task as `APPROVED`, `CLOSED`, or `ESCALATED`

---

### 5. PdM issue selection tool

**File:** `src/opendove/agents/product_manager.py`

New capability: given a repo URL, fetch open GitHub issues and select a subset to enqueue. For Phase 1 this is a simple tool call — PdM reads open issues and returns a list of issue numbers to enqueue.

**Tool required:** GitHub API — `GET /repos/{owner}/{repo}/issues`

PdM enqueues selected issues via the dispatcher.

---

### 6. Architect — full pipeline role

**File:** `src/opendove/agents/lead_architect.py`

Replace current stub behaviour with:

1. **Assess issue**: read the issue body + codebase (Claude Code MCP), decide atomic vs compound
2. **Produce technical brief**: always output a structured brief for Developer
3. **Code review**: after Developer pushes, read the diff + test output, approve or reject with specific reason
4. **Create PR**: on approval, call GitHub API to open PR with issue reference in body
5. **Read PR review comments**: when re-activated after `PENDING_EXTERNAL_REVIEW`, read maintainer's comments and produce revised guidance for Developer

**Tools required:**
- Claude Code MCP (full codebase read)
- GitHub API: read issue, read PR diff, read PR review comments, create PR

---

### 7. Developer — implement on branch

**File:** `src/opendove/agents/developer.py`

Current behaviour: Developer writes files using file tools (working).

New behaviour additions:
- Developer always pulls latest from the base branch before starting
- Developer receives the Architect's technical brief as primary instruction
- On re-activation after external review: Developer receives Architect's interpretation of maintainer comments as instruction, and continues on the same branch (worktree already exists)

---

### 8. Pre-checks gate

**File:** `src/opendove/agents/ava_checks.py` (rename to `src/opendove/checks/pre_checks.py`)

Automated checks run before Architect code review:
- CI status: green on the pushed branch (GitHub API: `GET /repos/{owner}/{repo}/commits/{ref}/status`)
- Files changed: at least one file modified in the worktree (existing `check_files_changed`)

On failure:
- Increment `precheck_retry_count`
- If `precheck_retry_count < 2`: Architect diagnoses from test output + diff, produces fix guidance for Developer
- If `precheck_retry_count >= 2`: task → `ESCALATED`

---

### 9. Graph redesign

**File:** `src/opendove/orchestration/graph.py`

Replace the current linear graph with the Phase 1 contribution mode graph:

```
START
  ↓
pjm_node          (prioritize, assign)
  ↓
architect_plan_node   (assess, brief)
  ↓
developer_node        (implement, test, push)
  ↓
pre_checks_node       (CI, files changed)
  ↓ fail → architect_precheck_escalation_node → developer_node (max 2)
  ↓ pass
architect_review_node (code review)
  ↓ reject → developer_node (max 2)
  ↓ approve
architect_create_pr_node  (open PR on GitHub)
  ↓
END  (task → PENDING_EXTERNAL_REVIEW)
```

---

### 10. PR poller

**File:** `src/opendove/scheduler/pr_poller.py`

New scheduled job (every 5 minutes):

1. Query DB for all tasks with status `PENDING_EXTERNAL_REVIEW`
2. For each task, call GitHub API: `GET /repos/{owner}/{repo}/pulls/{pull_number}`
3. On **merged**: set task → `APPROVED`, remove worktree, update DB
4. On **closed without merge**: set task → `CLOSED`, remove worktree, update DB
5. On **review requested changes**: set task → `QUEUED` (re-insert at original priority, top of tier), keep worktree

Register this job in the scheduler alongside the existing worker tick.

---

### 11. PjM progress tracking

**File:** `src/opendove/agents/project_manager.py`

After each task reaches a terminal state (`APPROVED`, `CLOSED`, `ESCALATED`):
- Update task record in DB with final status and timestamp
- Comment on the GitHub issue with a brief status update (contribution mode: "PR merged by maintainer" / "PR closed" / "Escalated — needs human review")

---

### 12. API additions

**File:** `src/opendove/api/routers/projects.py`

- `POST /projects/{id}/select-issues` — PdM selects GitHub issues to enqueue (contribution mode)
- `GET /projects/{id}/tasks` — add `precheck_retry_count`, `architect_review_retry_count`, `external_review_retry_count` to `TaskResponse`

---

## Implementation Order

Issues should be implemented in this order to avoid blocking dependencies:

```
1.  Project.mode field + API
2.  TaskStatus full lifecycle
3.  Retry counters on Task
4.  Pre-checks gate (rename + CI check)
5.  Graph redesign (skeleton, stubs ok)
6.  Architect — plan + code review + create PR
7.  Developer — pull latest + re-activation on same branch
8.  Worktree lifecycle fix (keep alive on PENDING_EXTERNAL_REVIEW)
9.  PR poller
10. PdM issue selection
11. PjM progress tracking + GitHub comment
12. API additions
```

---

## Acceptance Criteria for Phase 1

- [ ] Register a project in contribution mode via API
- [ ] Call `POST /projects/{id}/select-issues` with a list of GitHub issue numbers → tasks enqueued
- [ ] Worker picks up task → Architect reads issue + codebase → produces technical brief
- [ ] Developer implements on branch in worktree → pushes
- [ ] Pre-checks run → if CI fails, Architect diagnoses, Developer fixes (up to 2 rounds)
- [ ] Architect reviews code → rejects with reason or approves
- [ ] On approval → PR created on GitHub referencing the issue
- [ ] Task status transitions to `PENDING_EXTERNAL_REVIEW`
- [ ] Next queued task starts immediately
- [ ] Poller detects PR merged → task → `APPROVED`, worktree removed
- [ ] Poller detects changes requested → task re-queued → Architect reads comments → Developer fixes same PR
- [ ] All task statuses visible via `GET /projects/{id}/tasks`
- [ ] Full test suite passes
