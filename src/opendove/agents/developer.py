from opendove.agents.base import BaseAgent
from opendove.models.task import TaskStatus
from opendove.orchestration.graph import GraphState


class DeveloperAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = "Implement the task and provide evidence for validation."

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        task.artifact = "implementation_stub"
        task.status = TaskStatus.AWAITING_VALIDATION

        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "Developer: implementation complete."],
            "worktree_path": state.get("worktree_path", ""),
        }
