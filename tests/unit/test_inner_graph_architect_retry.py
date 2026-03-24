from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.graph import GraphState, build_graph
from opendove.validation.contracts import ValidationDecision


def _build_task(max_retries: int = 3) -> Task:
    return Task(
        title="Architect retry flow",
        intent="Exercise the AVA to Architect retry loop.",
        success_criteria=["Routes correctly", "Finishes deterministically"],
        owner=Role.PROJECT_MANAGER,
        max_retries=max_retries,
    )


def test_ava_reject_routes_to_architect() -> None:
    def rejecting_developer_node(state: GraphState) -> GraphState:
        task = state["task"]
        task.artifact = ""
        task.status = TaskStatus.AWAITING_VALIDATION
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "Developer: implementation incomplete."],
        }

    graph = build_graph(developer_node_fn=rejecting_developer_node)
    result = graph.invoke(
        {
            "task": _build_task(),
            "messages": [],
            "retry_count": 0,
            "architect_retry_count": 0,
            "worktree_path": "",
        }
    )

    assert result["task"].status is TaskStatus.APPROVED
    assert result["task"].artifact == "revised_implementation_stub"
    assert result["architect_retry_count"] == 1
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision is ValidationDecision.APPROVE
    assert "Architect: revised after AVA rejection (attempt 1)." in result["messages"]


def test_escalate_after_architect_retries_exhausted() -> None:
    def rejecting_developer_node(state: GraphState) -> GraphState:
        task = state["task"]
        task.artifact = ""
        task.status = TaskStatus.AWAITING_VALIDATION
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "Developer: implementation incomplete."],
        }

    graph = build_graph(developer_node_fn=rejecting_developer_node)
    result = graph.invoke(
        {
            "task": _build_task(),
            "messages": [],
            "retry_count": 0,
            "architect_retry_count": 1,
            "worktree_path": "",
        }
    )

    assert result["architect_retry_count"] == 2
    assert result["task"].status is TaskStatus.ESCALATED
    assert result["task"].artifact == "revised_implementation_stub"
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision is ValidationDecision.ESCALATE


def test_architect_retry_count_defaults_to_zero() -> None:
    def rejecting_developer_node(state: GraphState) -> GraphState:
        task = state["task"]
        task.artifact = ""
        task.status = TaskStatus.AWAITING_VALIDATION
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "Developer: implementation incomplete."],
        }

    graph = build_graph(developer_node_fn=rejecting_developer_node)
    result = graph.invoke({"task": _build_task(), "messages": [], "retry_count": 0})

    assert result["architect_retry_count"] == 1
    assert result["task"].status is TaskStatus.APPROVED
