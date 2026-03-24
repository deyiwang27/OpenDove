from opendove.agents.base import BaseAgent
from opendove.models.task import TaskStatus
from opendove.orchestration.graph import GraphState
from opendove.validation.contracts import ValidationDecision, ValidationResult


class AVAAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = "Approve, reject, or escalate based on the task contract and evidence."

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        retry_count = state["retry_count"]

        if retry_count >= task.max_retries:
            task.status = TaskStatus.ESCALATED
            decision = ValidationDecision.ESCALATE
            rationale = "Retry limit reached."
        elif task.artifact == "":
            retry_count += 1
            task.retry_count = retry_count
            task.status = TaskStatus.REJECTED
            decision = ValidationDecision.REJECT
            rationale = "No artifact produced."
        else:
            task.status = TaskStatus.APPROVED
            decision = ValidationDecision.APPROVE
            rationale = "Artifact present and criteria met."

        if decision is not ValidationDecision.REJECT:
            task.retry_count = retry_count

        task.validation_result = ValidationResult(
            task_id=task.id,
            decision=decision,
            rationale=rationale,
        )

        return {
            **state,
            "task": task,
            "retry_count": retry_count,
            "messages": [*state["messages"], f"AVA: {decision.value}."],
            "worktree_path": state.get("worktree_path", ""),
        }
