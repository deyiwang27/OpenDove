from opendove.agents.base import BaseAgent
from opendove.models.task import TaskStatus
from opendove.orchestration.graph import GraphState


class ProductManagerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = "Define the task scope, intent, and success criteria."

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        task.status = TaskStatus.IN_PROGRESS

        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "ProductManager: spec locked."],
            "worktree_path": state.get("worktree_path", ""),
        }
