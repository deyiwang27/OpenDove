# OpenDove

Direction-aligned multi-agent software development system.

## Overview

OpenDove is a multi-agent system designed to keep software delivery aligned with user intent from specification through validation.

The core idea is simple: code quality is not enough if the system drifts from the original goal. OpenDove uses explicit role separation and a blocking validation layer to keep the work on course.

## Workflow

Spec -> Plan -> Design -> Build -> Integrate -> Validate

Nothing is complete until validation approves it.

## Core Roles

- Product Manager: defines intent, scope, and success criteria
- Project Manager: assigns work, sets retry limits, and controls escalation
- Lead Architect: defines the technical path and performs integration checks
- Developer: implements code and tests
- AVA: approves, rejects, or escalates based on alignment and evidence

## Repository Structure

```text
.
├── docs/               # Architecture and roadmap
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

This repository is now scaffolded for the first implementation milestone:

- define the task contract
- persist task state
- orchestrate the five core roles
- block completion on AVA approval

The next step is to implement a real end-to-end task flow on top of this structure.
