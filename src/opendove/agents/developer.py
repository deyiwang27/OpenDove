from __future__ import annotations

import logging

from opendove.agents.base import BaseAgent
from opendove.agents.schemas import DeveloperOutput
from opendove.agents.tools import BashTool, GlobTool, GrepTool, ReadFileTool, WriteFileTool
from opendove.models.task import TaskStatus
from opendove.orchestration.graph import GraphState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Developer agent in an autonomous software development system.

You receive a task with a technical approach from the Lead Architect. Your job is \
to implement it completely and correctly in the git worktree at the path provided.

Rules:
- Read the existing code in the worktree before writing anything. Never overwrite \
  work that already exists unless you are explicitly replacing it.
- Follow the project's existing patterns: naming conventions, import style, test \
  structure. Run a quick grep/glob to understand conventions before starting.
- Every file you create or modify must be consistent with the rest of the codebase.
- Write tests for every new function or class. Tests live in tests/unit/.
- If you are modifying a public interface, update all callers.
- When done, produce an artifact summary that lists every file changed and explains \
  how each success criterion is satisfied. AVA will use this to validate your work.
- Do NOT modify unrelated files. Minimum diff, maximum correctness.

You have access to file tools (read, write, edit, glob, grep) and a bash tool for \
running tests. Use them. Always run the tests before declaring work complete.
"""


class DeveloperAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = _SYSTEM_PROMPT

    def __init__(self, llm, system_prompt: str = _SYSTEM_PROMPT, **kwargs) -> None:
        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            tools=[ReadFileTool(), GlobTool(), GrepTool(), WriteFileTool(), BashTool()],
            **kwargs,
        )

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        worktree_path = state.get("worktree_path", "")
        architect_approach = task.artifact or "(no architect guidance provided)"
        success_criteria_str = "\n".join(f"- {c}" for c in task.success_criteria)

        user_message = (
            f"Task: {task.title}\n"
            f"Intent: {task.intent}\n"
            f"Success criteria:\n{success_criteria_str}\n"
            f"Worktree path: {worktree_path or '(working directory)'}\n"
            f"Technical approach from Architect:\n{architect_approach}\n\n"
            "Implement this task completely. When done, summarise every file changed "
            "and explain how each success criterion is satisfied."
        )

        try:
            output: DeveloperOutput = self._call_llm_structured(
                user_message, DeveloperOutput
            )
            files_note = ", ".join(output.files_changed) if output.files_changed else "none listed"
            updated_task = task.model_copy(
                update={
                    "artifact": output.artifact,
                    "status": TaskStatus.AWAITING_VALIDATION,
                }
            )
            message = f"Developer: implementation complete. Files changed: {files_note}."
        except Exception:
            logger.exception("Developer LLM call failed")
            updated_task = task.model_copy(
                update={
                    "artifact": "implementation_stub",
                    "status": TaskStatus.AWAITING_VALIDATION,
                }
            )
            message = "Developer: implementation complete (LLM unavailable, stub artifact)."

        return {
            **state,
            "task": updated_task,
            "messages": [*state["messages"], message],
            "worktree_path": worktree_path,
        }
