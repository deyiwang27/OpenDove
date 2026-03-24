# Architecture

OpenDove starts with a single orchestrator that moves one task through five role stages:

1. Product Manager defines the task contract.
2. Project Manager assigns ownership and iteration limits.
3. Lead Architect defines the implementation plan.
4. Developer produces changes and tests.
5. AVA validates scope, intent, and evidence.

## Core building blocks

- `src/opendove/models/`: shared domain models and task contracts
- `src/opendove/orchestration/`: graph and execution flow
- `src/opendove/roles/`: role-specific behavior and prompts
- `src/opendove/state/`: task state transitions and persistence contracts
- `src/opendove/storage/`: PostgreSQL adapters
- `src/opendove/validation/`: validation decisions and rejection reasons

## First implementation target

The first working milestone should support a single task end to end:

- create task
- plan task
- simulate or execute implementation
- require AVA approval before closure
- persist each state transition

