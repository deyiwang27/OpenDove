# OpenDove Workflow Design

## Overview

OpenDove is an autonomous software development system that contributes to GitHub repositories using a team of AI agents. It operates in two modes:

- **Contribution Mode** — OpenDove works on issues from an existing repo, following the repo's contribution guidelines and creating PRs for maintainer review.
- **Autonomous Mode** — OpenDove owns the product direction on a personal repo. The Product Manager agent drives feature creation, research, and delivery autonomously with periodic user check-ins.

Both modes share the same core development pipeline. They differ only in how work enters the system and what happens after a PR is created.

---

## Roles

| Agent | Responsibility |
|---|---|
| **Product Manager (PdM)** | Selects or creates issues, reviews completed work against product vision, reports to user, manages daily token budget |
| **Project Manager (PjM)** | Prioritizes the work queue, assigns milestones, tracks progress in DB, manages re-queuing of blocked tasks |
| **Architect** | Assesses issue complexity, produces technical brief, optionally decomposes into sub-tasks (autonomous mode only), reviews code quality and test results, creates PR on approval |
| **Developer** | Implements sub-task or issue, runs tests, pushes branch |
| **Pre-checks** | Automated gate (not an agent): CI passed, files changed. Blocks Architect review if failed |

> **Note:** AVA (Alignment & Validation Agent) is retired as a standalone agent. Its automated checks become the pre-checks gate. Technical review is owned by the Architect. Product alignment is owned by PdM.

---

## Unified Pipeline

```
CONTRIBUTION MODE                      AUTONOMOUS MODE
─────────────────                      ────────────────
PdM selects open issues           ←→   PdM session with user
from target repo                        PdM researches + creates issues
(up to daily token budget)              (up to daily token budget)
        ↓                                      ↓
        └────────────── enqueue to project ────┘
                             ↓
        PjM prioritizes queue, assigns to milestone (both modes)
                             ↓
        Architect: read codebase, assess issue
          → atomic (fits one PR)  → produce technical brief → Developer
          → compound (autonomous only) → decompose into sub-tasks
            → create sub-issues on GitHub via API
            → produce technical brief per sub-task → Developer
                             ↓
        ┌── INNER LOOP (per sub-task or issue) ───────────────────────┐
        │                                                              │
        │  Developer: implement, test, push branch                    │
        │  (worktree stays alive while PR is open)                    │
        │       ↓                                                      │
        │  Pre-checks: CI passed? files changed?                      │
        │       ↓ fail → Architect diagnoses root cause               │
        │               → guidance to Developer (max 2 escalations)  │
        │               → after 2: escalate to human                  │
        │  Architect: code review                                      │
        │       ↓ reject → Developer fixes (max 2 rounds)            │
        │       ↓ approve → create PR                                 │
        │                                                              │
        │  CONTRIBUTION MODE:                                         │
        │    → status: PENDING_EXTERNAL_REVIEW                        │
        │    → continue next task from queue                          │
        │    [background poller watches PR]                           │
        │      merged / closed → remove from queue, update DB         │
        │      changes requested → re-queue at original priority      │
        │          (top of same priority tier)                        │
        │          → Architect reads PR review comments               │
        │          → briefs Developer → fix in same PR (max 2 rounds) │
        │                                                              │
        │  AUTONOMOUS MODE:                                           │
        │    PdM: review PR + parent issue + test output              │
        │       ↓ reject / request changes (max 2 rounds)            │
        │           → Architect guidance → Developer fixes same PR    │
        │       ↓ accept → auto-merge                                 │
        └──────────────────────────────────────────────────────────────┘
                             ↓
        PjM: all sub-tasks done for parent issue?
          → no: next sub-task
          → yes: proceed to outer loop
                             ↓
        ┌── OUTER LOOP (per parent issue) ────────────────────────────┐
        │                                                              │
        │  CONTRIBUTION MODE:                                         │
        │    PjM: update issue status in DB                           │
        │    (issue stays open on GitHub — maintainer closes it)      │
        │                                                              │
        │  AUTONOMOUS MODE:                                           │
        │    PjM: close GitHub issue, update milestone progress in DB │
        │    milestone complete?                                       │
        │      → yes: PdM compiles report → email user → new session  │
        │      → no: next issue from queue                            │
        └──────────────────────────────────────────────────────────────┘
```

---

## Retry Limits (all independent counters)

| Trigger | Max rounds | After limit |
|---|---|---|
| Pre-checks fail | 2 | Architect escalation |
| Architect escalation (pre-checks) | 2 | Human escalation |
| Architect code review reject | 2 | Human escalation |
| Maintainer requests changes | 2 | Human escalation |
| PdM rejects (autonomous) | 2 | Human escalation |

---

## Task Status Model

```
PENDING               → created, not yet queued
QUEUED                → in the work queue
IN_PROGRESS           → agent pipeline is actively running
PENDING_EXTERNAL_REVIEW → PR created, waiting for maintainer
APPROVED              → merged (autonomous) or accepted (contribution)
REJECTED              → failed validation, being retried
ESCALATED             → exceeded retry limit, needs human
BLOCKED               → dependency not yet resolved
CLOSED                → done, issue updated
```

---

## State Persistence

**GitHub is the source of truth** for issues, sub-issues, PRs, and milestones.

**OpenDove DB** stores only:
- Project registration: repo URL, mode, settings, daily token budget
- Task execution state: current status, retry counters, which graph node
- Links: `task → github_issue_number`, `task → github_pr_url`

**Repo files** (`.opendove/` directory, gitignored) store:
- Milestone definitions
- PdM session transcripts and conclusions
- Architect technical briefs

---

## Agent Tooling

| Agent | Tools |
|---|---|
| PdM | GitHub API (read/create issues), web search, email |
| PjM | GitHub API (read issues, update status), DB |
| Architect | Claude Code MCP (full codebase access), GitHub API (create sub-issues, read PR reviews, create/merge PR) |
| Developer | Read, write, edit files; Bash (run tests); Glob; Grep |
| Pre-checks | CI status via GitHub API, git diff |

---

## GitHub Token Requirements

A **Classic Personal Access Token** with `repo` scope is required for both modes.

- Contribution mode: push branches, create PRs, read PR review comments
- Autonomous mode: all of the above + merge PRs on owned repos

Token is set as `OPENDOVE_GITHUB_TOKEN` in `.env`.

---

## Daily Token Budget

- Per-project setting stored in DB
- PdM tracks cumulative LLM API tokens consumed per day
- When budget is reached, PdM stops selecting/creating new issues
- In-flight tasks complete normally
- Budget resets at midnight UTC

---

## Mode Comparison

| Aspect | Contribution Mode | Autonomous Mode |
|---|---|---|
| Issue source | PdM selects from existing repo | PdM creates via research + user session |
| Sub-issue decomposition | Internal sub-tasks only (not on GitHub) | GitHub sub-issues created by Architect |
| PR per issue | One PR per issue (all sub-tasks on one branch) | One PR per sub-issue |
| Post-PR | Maintainer reviews and merges | PdM reviews and auto-merges |
| Issue closure | Maintainer closes; PjM updates DB | PjM closes GitHub issue |
| PdM role | Minimal (queue entry + token budget) | Full (research, create, accept, report) |
| Milestone management | PjM tracks in DB | PjM tracks in DB + GitHub milestones |
| User notification | DB/dashboard (future) | Email on milestone completion |
