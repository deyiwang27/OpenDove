from __future__ import annotations

import logging

from opendove.agents.base import BaseAgent
from opendove.agents.schemas import ArchitectReviewOutput, LeadArchitectOutput
from opendove.orchestration.graph import GraphState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Lead Architect for an autonomous software development system.

Your job is to produce a concrete, step-by-step implementation plan that a Developer \
agent can execute without needing clarification. You have access to file-reading and \
code-search tools — use them to understand the existing codebase before designing \
your approach.

Rules:
- Always check existing code before proposing new files or patterns. Reuse what \
  exists; do not introduce duplicate abstractions.
- The implementation plan must be specific enough that a developer can follow it \
  mechanically: name the files, the functions, the data types.
- Assess risk_level honestly:
    - "architectural" if the change touches: public API contracts, database schema, \
      core interfaces (BaseAgent, GraphState, TaskStore), or cross-cutting concerns.
    - "low" for everything else.
- List every file you expect the developer to touch. Missing a file here often \
  means AVA will reject for docs not updated.
"""

_REVIEW_SYSTEM_PROMPT = """\
You are the Lead Architect reviewing a rejected implementation.

AVA has rejected the Developer's work. Your job is to diagnose the root cause and \
produce revised implementation guidance that will fix the issue. Be surgical — do \
not rewrite the entire approach unless necessary.

Rules:
- Read the AVA rejection rationale carefully. Address each failure point explicitly.
- Your revised approach must be actionable: name the specific change required in \
  each affected file.
- Do not repeat guidance that was already correct. Focus only on what needs to change.
"""


class LeadArchitectAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = _SYSTEM_PROMPT

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        architect_retry_count = state.get("architect_retry_count", 0)

        # Architect review mode: AVA rejected, we're revising
        if architect_retry_count > 0:
            return self._run_review(state)

        success_criteria_str = "\n".join(f"- {c}" for c in task.success_criteria)
        user_message = (
            f"Task: {task.title}\n"
            f"Intent: {task.intent}\n"
            f"Success criteria:\n{success_criteria_str}\n"
            f"Worktree path: {state.get('worktree_path', '(not yet created)')}\n\n"
            "Produce a technical approach and list the files you expect to be changed."
        )

        try:
            output: LeadArchitectOutput = self._call_llm_structured(
                user_message, LeadArchitectOutput
            )
            updated_task = task.model_copy(
                update={"risk_level": output.risk_level}
            )
            approach_summary = output.technical_approach[:200].replace("\n", " ")
            files_note = ", ".join(output.affected_files) if output.affected_files else "none listed"
            message = (
                f"Architect: approach defined (risk={output.risk_level}). "
                f"Files: {files_note}. Approach: {approach_summary}..."
            )
        except Exception:
            logger.exception("LeadArchitect LLM call failed; using original task")
            updated_task = task
            message = "Architect: approach defined (LLM unavailable, using defaults)."

        return {
            **state,
            "task": updated_task,
            "messages": [*state["messages"], message],
            "worktree_path": state.get("worktree_path", ""),
        }

    def _run_review(self, state: GraphState) -> GraphState:
        task = state["task"]
        architect_retry_count = state.get("architect_retry_count", 0) + 1
        ava_rationale = (
            task.validation_result.rationale
            if task.validation_result
            else "No rationale provided."
        )
        ava_checks = (
            ", ".join(task.validation_result.checks)
            if task.validation_result and task.validation_result.checks
            else "unknown"
        )

        user_message = (
            f"Task: {task.title}\n"
            f"Original intent: {task.intent}\n"
            f"AVA rejection rationale: {ava_rationale}\n"
            f"Checks that failed: {ava_checks}\n"
            f"Current artifact summary: {task.artifact[:500] if task.artifact else '(none)'}\n\n"
            "Diagnose the root cause and provide revised implementation guidance."
        )

        try:
            output: ArchitectReviewOutput = self._call_llm_structured(
                user_message, ArchitectReviewOutput
            )
            updated_task = task.model_copy(
                update={"artifact": output.revised_approach}
            )
            message = (
                f"Architect: revised after AVA rejection (attempt {architect_retry_count}). "
                f"Root cause: {output.root_cause}"
            )
        except Exception:
            logger.exception("LeadArchitect review LLM call failed")
            updated_task = task.model_copy(
                update={"artifact": f"revised_stub_attempt_{architect_retry_count}"}
            )
            message = f"Architect: revised after AVA rejection (attempt {architect_retry_count})."

        from opendove.models.task import TaskStatus

        updated_task = updated_task.model_copy(update={"status": TaskStatus.AWAITING_VALIDATION})

        return {
            **state,
            "task": updated_task,
            "architect_retry_count": architect_retry_count,
            "messages": [*state["messages"], message],
            "worktree_path": state.get("worktree_path", ""),
        }
