# OpenDove

OpenDove is an alignment-first software delivery system for the AI-native development era.

It is built for a world where Claude Code, Codex, Gemini, and similar tools are already strong at local code execution, but the surrounding delivery process still depends on too much human coordination. OpenDove is designed to manage that process: translate goals into scoped work, orchestrate execution, enforce validation, and escalate only when human judgment is actually needed.

## Vision

The long-term ambition is an autonomous software factory.

Users provide goals, constraints, and intent. OpenDove manages the delivery loop from specification to validation while keeping the work aligned with what the user actually meant to build.

The near-term starting point is more practical: a developer tool for semi-autonomous engineering teams that reduces manual coordination around AI-assisted software delivery.

## Core Idea

Most coding assistants optimize for producing code. OpenDove optimizes for delivering the right outcome.

Its core thesis is that software automation fails when there is no strong system for:

- preserving intent across stages
- separating responsibilities clearly
- validating work before it is considered done
- escalating ambiguity instead of hiding it

## Workflow

Intent -> Spec -> Plan -> Design -> Build -> Integrate -> Validate

Nothing is complete until validation approves it.

## Role Model

- Product Manager defines what should be built and why
- Project Manager controls execution flow, retries, and escalation
- Lead Architect defines the technical path and checks integration
- Developer agents execute implementation and tests using tools such as Claude Code, Codex, and Gemini
- AVA acts as the blocking alignment and validation gate

## Why This Exists

Current AI-native development still leaves humans doing too much of the coordination work:

- clarifying goals
- turning goals into executable tasks
- reviewing whether the result matches the original intent
- checking whether tests are meaningful
- deciding whether something is actually done

OpenDove is intended to own that missing layer.

## Kickoff Docs

- [Vision](docs/vision.md)
- [Product](docs/product.md)
- [Principles](docs/principles.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Glossary](docs/glossary.md)

## Repository Structure

```text
.
├── docs/               # Product, strategy, and architecture docs
├── examples/           # Example tasks and flows
├── migrations/         # Database migration files
├── prompts/            # Versioned role prompts
├── scripts/            # Local helper scripts
├── src/opendove/
│   ├── models/         # Shared task and domain models
│   ├── orchestration/  # LangGraph flow and orchestration logic
│   ├── roles/          # Role definitions and role-specific behavior
│   ├── state/          # Task state transitions and store contracts
│   ├── storage/        # PostgreSQL adapters
│   └── validation/     # Validation decisions and rules
└── tests/
    ├── integration/
    └── unit/
```

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
PYTHONPATH=src python -m opendove.main
```

## Current Status

The repository is still at kickoff stage. The documentation now defines the product direction, system principles, and high-level architecture. The next engineering milestone is to implement the first end-to-end task lifecycle with state, orchestration, and a blocking AVA decision.
