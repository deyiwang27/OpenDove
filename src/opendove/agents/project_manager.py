from opendove.agents.base import BaseAgent
from opendove.orchestration.graph import GraphState


class ProjectManagerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = "Assign tasks, control retries, and trigger escalation."

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]

        return {
            **state,
            "task": task,
            "messages": [
                *state["messages"],
                f"ProjectManager: task assigned, max_retries={task.max_retries}.",
            ],
            "worktree_path": state.get("worktree_path", ""),
        }
