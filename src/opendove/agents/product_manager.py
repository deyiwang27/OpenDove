from __future__ import annotations

import logging

from opendove.agents.base import BaseAgent
from opendove.agents.schemas import ProductManagerOutput
from opendove.models.task import TaskStatus
from opendove.orchestration.graph import GraphState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Product Manager for an autonomous software development system.

Your job is to take a raw task request and make it concrete and unambiguous before \
it enters the development pipeline. You do NOT implement anything — you define what \
"done" means so that the Developer and AVA can work without guesswork.

Rules:
- Success criteria must be independently verifiable (AVA will check them without \
  asking you questions).
- Each criterion should start with an observable verb: "passes", "returns", \
  "creates", "raises", "contains", "does not".
- Reject vague criteria like "works correctly" or "is clean". Replace them with \
  specific, checkable statements.
- Scope note must be a single sentence naming what is NOT in this task. This \
  prevents the developer from over-building.
- Do not add criteria that weren't implied by the original intent. Stay focused.
"""


class ProductManagerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = _SYSTEM_PROMPT

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]

        user_message = (
            f"Task title: {task.title}\n"
            f"Intent: {task.intent}\n"
            f"Current success criteria: {task.success_criteria}\n\n"
            "Refine the success criteria to be concrete and testable. "
            "Produce a scope note that names what is out of scope."
        )

        try:
            output: ProductManagerOutput = self._call_llm_structured(
                user_message, ProductManagerOutput
            )
            updated_task = task.model_copy(
                update={
                    "success_criteria": output.success_criteria,
                    "status": TaskStatus.IN_PROGRESS,
                }
            )
            note = output.scope_note
        except Exception:
            logger.exception("ProductManager LLM call failed; keeping original criteria")
            updated_task = task.model_copy(update={"status": TaskStatus.IN_PROGRESS})
            note = "scope unchanged (LLM unavailable)"

        return {
            **state,
            "task": updated_task,
            "messages": [
                *state["messages"],
                f"ProductManager: spec locked. Out of scope: {note}",
            ],
            "worktree_path": state.get("worktree_path", ""),
        }
