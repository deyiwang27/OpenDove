from __future__ import annotations

import logging

from opendove.agents.base import BaseAgent
from opendove.agents.schemas import ProjectManagerOutput
from opendove.models.task import Role
from opendove.orchestration.graph import GraphState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Project Manager for an autonomous software development system.

You sit between the Product Manager (who defines scope) and the Lead Architect \
(who designs the solution). Your job is to validate that a task is properly \
specified and ready for development, assign it to the right role, and calibrate \
the retry budget.

Rules:
- owner should almost always be "developer". Only set it to another role if the \
  task explicitly belongs to a different stage (e.g. a documentation-only task \
  could be "lead_architect").
- max_retries should reflect task complexity:
    - 2 for simple, well-defined tasks (add a field, fix a typo, rename a method)
    - 3 for standard feature work (new endpoint, new agent, new model)
    - 4-5 for complex tasks (cross-cutting refactor, new subsystem, integration work)
- readiness_note: flag any blockers. If the task is ready, say so explicitly. If \
  success criteria are still vague, call it out — the ProductManager should have \
  caught this but you are the last checkpoint.
"""


class ProjectManagerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = _SYSTEM_PROMPT

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        priority_note = (
            f" (GitHub issue #{task.github_issue_number})"
            if task.github_issue_number is not None
            else ""
        )
        success_criteria_str = "\n".join(f"- {c}" for c in task.success_criteria)

        user_message = (
            f"Task: {task.title}{priority_note}\n"
            f"Intent: {task.intent}\n"
            f"Risk level: {task.risk_level}\n"
            f"Success criteria:\n{success_criteria_str}\n\n"
            "Assign an owner, set max_retries, and confirm readiness."
        )

        try:
            output: ProjectManagerOutput = self._call_llm_structured(
                user_message, ProjectManagerOutput
            )
            updated_task = task.model_copy(
                update={
                    "owner": Role(output.owner),
                    "max_retries": output.max_retries,
                }
            )
            message = (
                f"ProjectManager: task '{task.title}'{priority_note} assigned to "
                f"{output.owner}, max_retries={output.max_retries}. "
                f"{output.readiness_note}"
            )
        except Exception:
            logger.exception("ProjectManager LLM call failed; using task defaults")
            updated_task = task
            message = (
                f"ProjectManager: task '{task.title}'{priority_note} assigned to "
                f"{task.owner}, max_retries={task.max_retries}."
            )

        return {
            **state,
            "task": updated_task,
            "messages": [*state["messages"], message],
            "worktree_path": state.get("worktree_path", ""),
        }
