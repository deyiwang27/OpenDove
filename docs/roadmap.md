# Roadmap

## Phase 0: Kickoff

Objective: define the product direction and prove the architecture can support the core thesis.

- align on mission, vision, and product scope
- define the task lifecycle and role contracts
- establish the initial repository structure
- identify the minimum end-to-end task flow to implement first

## Phase 1: Single-Task Trust Loop

Objective: prove that one task can move through the system with real control and validation.

- define the task schema and state machine
- persist tasks, artifacts, and events in PostgreSQL
- run one orchestrated flow through the core roles
- enforce retry limits and escalation conditions
- make AVA approval a blocking gate

Success looks like one scoped engineering task completing with durable state, clear artifacts, and a trustworthy approval or rejection outcome.

## Phase 2: Semi-Autonomous Team Tool

Objective: make OpenDove useful for real engineering workflows.

- add real execution adapters for Claude Code, Codex, and Gemini
- support human review and intervention points
- add richer integration validation and evidence collection
- improve observability for task progress and decision history
- support practical day-to-day usage on small engineering tasks

Success looks like a team being able to hand OpenDove a scoped task and supervise exceptions rather than coordinate every step manually.

## Phase 3: Multi-Task Delivery System

Objective: expand from one task loop to coordinated project execution.

- support multiple concurrent tasks
- add dependency awareness and prioritization
- add stronger scheduling and resource policies
- add project-level dashboards and audit trails
- improve failure recovery and task re-planning

Success looks like OpenDove managing a stream of related engineering work instead of isolated tasks.

## Phase 4: Autonomous Software Factory

Objective: move from semi-autonomous task execution to broad project autonomy.

- accept larger product goals instead of only narrow tasks
- perform task decomposition and planning automatically
- coordinate multiple execution paths safely
- manage escalation and policy boundaries at project scale
- continuously validate progress against the original product intent

Success looks like a user setting direction and constraints while OpenDove manages most of the delivery loop with minimal human intervention.
