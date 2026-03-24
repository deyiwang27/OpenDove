# Development Workflow

## Purpose

This workflow defines how OpenDove should be developed in an AI-assisted way without losing control of scope, quality, or alignment.

The workflow is designed for contributors who use tools such as Claude Code, Codex, and Gemini during implementation.

## Operating Principle

AI should accelerate execution. It should not replace intent definition, approval, or review discipline.

## Feature Lifecycle

### 1. Open An Issue

Every feature starts with an issue. The issue should define:

- the problem
- the intended outcome
- in-scope work
- out-of-scope work
- acceptance criteria
- validation evidence

This is the contract for the feature. If the issue is vague, the implementation will drift.

### 2. Clarify Before Coding

Before implementation starts, confirm:

- the issue is small enough for one focused PR
- the constraints are known
- the success criteria are testable
- the likely risks are visible

If not, split the issue or refine it first.

### 3. Implement With AI Assistance

Use AI coding tools for exploration, drafting, refactoring, and test generation where helpful.

Do not delegate final judgment to the tool. The contributor is responsible for:

- reviewing generated code
- checking the assumptions the tool made
- making sure tests are meaningful
- keeping the changes bounded by the issue

### 4. Run Local Gates

Before commit or PR, run the local gates:

- `pre-commit run --all-files`
- `make test`

These are the minimum signals that the change is syntactically clean and does not break the current test suite.

### 5. Open A Pull Request

The PR should link back to the issue and explain:

- what changed
- why it changed
- how AI tools were used
- what validation was performed
- what reviewers should focus on

This keeps the PR review centered on intent and risk, not only diff volume.

### 6. Review The Pull Request

Reviewers should validate five things:

1. The PR matches the original issue intent.
2. The scope did not drift silently.
3. The tests are meaningful for the claimed behavior.
4. Integration risks are addressed or called out.
5. Any uncertainty is escalated instead of hidden.

### 7. Merge Only After Evidence

Merge requires:

- passing CI
- resolved review comments
- sufficient validation evidence
- no unresolved scope ambiguity

## Local Workflow

Install dependencies:

```bash
pip install -e ".[dev]"
pre-commit install
```

Common commands:

```bash
make format
make lint
make test
make check
```

## CI Workflow

GitHub Actions is the enforcement layer for shared quality gates.

The CI pipeline currently:

- installs dependencies
- runs lint checks
- runs tests on Python 3.11 and 3.12

As the codebase grows, this should expand to include integration tests, migration validation, and workflow-specific checks.

## Review Mindset

OpenDove is an alignment-first project, so review should be stricter than "the code seems fine."

Reviewers should look for:

- drift from the issue contract
- over-engineering
- fake or shallow tests
- changes that are hard to validate
- hidden assumptions introduced by AI-generated code

