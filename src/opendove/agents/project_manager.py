from opendove.agents.base import BaseAgent
from opendove.orchestration.graph import GraphState


class ProjectManagerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = (
        "You are the Project Manager. Assign tasks, manage priorities, "
        "track progress, and trigger escalation when needed."
    )

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        messages = list(state["messages"])

        # Determine priority label from task's github_issue_number presence
        priority_note = ""
        if task.github_issue_number is not None:
            priority_note = f" (GitHub issue #{task.github_issue_number})"

        messages.append(
            f"ProjectManager: task '{task.title}'{priority_note} assigned to {task.owner}, "
            f"max_retries={task.max_retries}, risk_level={task.risk_level}."
        )

        return {
            **state,
            "task": task,
            "messages": messages,
            "worktree_path": state.get("worktree_path", ""),
        }
