# Contributing

OpenDove is built for AI-assisted software delivery, so the contribution process is designed to keep AI speed without losing alignment, review quality, or traceability.

## Workflow Summary

Each feature should move through this sequence:

1. Create or refine an issue.
2. Define intent, scope, and acceptance criteria before coding.
3. Create a feature branch from the current base branch.
4. Implement with AI assistance inside the issue boundary.
5. Run local pre-commit and test checks.
6. Open a PR with evidence and explicit review focus.
7. Review for alignment, correctness, and test adequacy before merge.

## Branch Naming

Use short, descriptive branch names:

- `feat/<short-name>`
- `fix/<short-name>`
- `docs/<short-name>`
- `chore/<short-name>`

## Create An Issue

Every feature should start from an issue. The issue is the source of truth for intent.

The issue must define:

- the problem being solved
- the intended outcome
- what is in scope
- what is out of scope
- acceptance criteria
- required validation evidence

If those fields are weak, coding should not start yet. OpenDove is explicitly trying to reduce drift from weak intent.

## Implement The Feature

AI tools such as Claude Code, Codex, and Gemini are encouraged for implementation work. Use them as execution accelerators, not as approval authorities.

The person driving the feature remains responsible for:

- keeping the work inside scope
- reviewing generated changes before commit
- checking that tests actually validate the requirement
- escalating ambiguity instead of guessing

## Local Checks Before Commit

Install the development dependencies and hooks:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

Before opening a PR, run:

```bash
pre-commit run --all-files
make test
```

## Pull Request Requirements

Every PR should:

- link to its issue
- explain the intent behind the change
- state whether any scope changed
- disclose how AI tools were used
- include validation evidence
- highlight review hotspots

Keep PRs small enough that a reviewer can validate alignment, not just skim code.

## Review Standard

Reviews should prioritize:

- alignment with the issue intent and acceptance criteria
- behavioral regressions or integration risk
- missing or weak tests
- evidence of scope creep
- unresolved ambiguity that should be escalated

The main question is not only "does this code work?" It is also "is this the right change for the stated goal?"

## Merge Standard

A PR is ready to merge only when:

- CI passes
- review concerns are resolved
- the linked issue acceptance criteria are satisfied
- no material ambiguity remains hidden

If the change is technically correct but misaligned with the issue intent, it is not ready to merge.

