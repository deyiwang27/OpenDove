# Architecture

## High-Level System View

OpenDove is not intended to be one more coding model. It is intended to be the control system around coding models.

At a high level, the system has five parts:

1. Goal intake
2. Orchestration and state management
3. Role-specific decision logic
4. Execution adapters for coding assistants
5. Validation and escalation

The architecture should reflect that separation clearly from the beginning.

## System Intent

The system accepts a user goal and moves it through a managed delivery loop while preserving alignment with the original intent.

That means the architecture must support:

- persistent task state
- explicit stage transitions
- durable artifacts
- validation before completion
- escalation when autonomy should stop

## Conceptual Layers

### 1. Control Layer

This is the core of OpenDove.

It manages tasks, role transitions, retry limits, decision points, and traceability. This layer decides what should happen next and whether the system can continue autonomously.

### 2. Role Layer

This layer encapsulates the responsibilities of Product Manager, Project Manager, Lead Architect, Developer, and AVA.

Each role should have a clear contract:

- expected input
- expected output
- allowed decisions
- handoff conditions

### 3. Execution Layer

This layer connects OpenDove to code-capable agents such as Claude Code, Codex, and Gemini.

Those systems should be treated as pluggable execution engines, not as the source of truth for delivery state. OpenDove owns the workflow. The coding assistants perform bounded execution within that workflow.

### 4. State And Artifact Layer

This layer stores the durable record of work:

- task definitions
- task status
- ownership
- role outputs
- code and test evidence
- validation decisions
- escalation events

Markdown can document the system, but it should not function as the runtime coordination mechanism. The runtime source of truth should live in structured state and persistent storage.

### 5. Validation Layer

This layer enforces completion standards. It should verify:

- conformance to the task contract
- alignment with original intent
- sufficiency of test evidence
- absence of obvious scope drift

This is where OpenDove becomes more than orchestration theater.

## Core Flow

The initial system should support one task moving through this sequence:

1. Product defines the task contract.
2. Project Manager turns it into an execution unit with limits.
3. Lead Architect defines the technical approach.
4. Developer executes implementation and produces evidence.
5. Lead Architect performs explicit integration review.
6. AVA approves, rejects, or escalates.

If AVA rejects, the task returns for rework. If AVA escalates, the task returns to human or upstream decision-making.

## Why Existing Coding Assistants Matter

OpenDove is designed for the current AI-native development stack, not in opposition to it.

Claude Code, Codex, and Gemini already make strong execution engines for implementation tasks. OpenDove should leverage them where they are strongest and avoid re-creating their strengths. The architecture should therefore prioritize:

- adapter-based integration with execution tools
- clear boundaries between orchestration and implementation
- portability across different model providers

## Initial Technical Shape

The first implementation should stay minimal:

- LangGraph for orchestration
- PostgreSQL for durable task and event state
- Python services and modules for control logic
- prompt files for role behavior and policy
- adapter interfaces for external coding assistants

## Mapping To Repository Structure

- `src/opendove/models/`: shared task and domain contracts
- `src/opendove/orchestration/`: workflow graph and execution control
- `src/opendove/roles/`: role definitions and role-specific behavior
- `src/opendove/state/`: state transitions and store contracts
- `src/opendove/storage/`: durable persistence adapters
- `src/opendove/validation/`: validation rules and decision contracts
- `prompts/`: versioned prompt definitions per role

## First Architecture Milestone

The first architecture milestone is not multi-project autonomy. It is one trustworthy task loop.

To count as successful, the initial system should be able to:

- accept one scoped task
- persist its state and artifacts
- execute a role-based flow
- enforce retry limits
- require AVA approval before completion
- escalate when the task cannot be resolved safely
