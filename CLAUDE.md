# CLAUDE.md — OpenDove project instructions

## Git Workflow

Always branch from `main` for new work. Never reuse or build on stale feature branches unless explicitly told to.

## Delegation & Workflow

Delegate implementation tasks to CodeX MCP (`mcp__codex__codex`) whenever possible. Only implement directly if CodeX is unavailable or the task is trivial (< 5 lines).

When using CodeX MCP for PRs, always specify the exact target branch explicitly. Verify the branch and diff before pushing.

## Debugging

When fixing bugs, verify the root cause before implementing. For async/concurrency issues, check event loops, blocking calls, and timing before assuming the cause. Run targeted tests after each fix.

## Testing & CI

This project uses Python as the primary language. Always follow existing project conventions for imports, type hints, and test structure. Run the full CI pipeline (`pytest`) after changes to catch env/config mismatches.
