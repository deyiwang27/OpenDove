from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.graph import GraphState, build_graph
from opendove.state.memory_store import InMemoryTaskStore
from opendove.validation.contracts import ValidationDecision


def test_happy_path() -> None:
    task = Task(
        title="Implement core flow",
        intent="Run the deterministic Phase 1 orchestration successfully.",
        success_criteria=["Graph completes", "Task is approved"],
        owner=Role.PROJECT_MANAGER,
        artifact="seed_artifact",
    )

    graph = build_graph()
    result = graph.invoke({"task": task, "messages": [], "retry_count": 0})

    assert result["task"].status is TaskStatus.APPROVED
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision is ValidationDecision.APPROVE
    assert result["task"].artifact == "implementation_stub"
    assert result["retry_count"] == 0


def test_rejection_then_approval() -> None:
    task = Task(
        title="Retry until artifact exists",
        intent="Validate the AVA rejection loop.",
        success_criteria=["First attempt rejects", "Second attempt approves"],
        owner=Role.PROJECT_MANAGER,
    )

    def flaky_developer_node(state: GraphState) -> GraphState:
        updated_task = state["task"]
        if state["retry_count"] == 0:
            updated_task.artifact = ""
            message = "Developer: implementation incomplete."
        else:
            updated_task.artifact = "implementation_stub"
            message = "Developer: implementation complete."

        updated_task.status = TaskStatus.AWAITING_VALIDATION
        return {
            **state,
            "task": updated_task,
            "messages": [*state["messages"], message],
        }

    graph = build_graph(developer_node_fn=flaky_developer_node)
    result = graph.invoke({"task": task, "messages": [], "retry_count": 0})

    assert result["retry_count"] == 1
    assert result["task"].retry_count == 1
    assert result["task"].status is TaskStatus.APPROVED
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision is ValidationDecision.APPROVE
    assert result["messages"].count("AVA: reject.") == 1
    assert result["messages"].count("AVA: approve.") == 1


def test_escalation_on_retry_limit() -> None:
    task = Task(
        title="Escalate immediately",
        intent="Stop when retries are already exhausted.",
        success_criteria=["Task is escalated"],
        owner=Role.PROJECT_MANAGER,
        max_retries=0,
    )

    graph = build_graph()
    result = graph.invoke({"task": task, "messages": [], "retry_count": 0})

    assert result["task"].status is TaskStatus.ESCALATED
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision is ValidationDecision.ESCALATE
    assert result["retry_count"] == 0


def test_memory_store_crud() -> None:
    store = InMemoryTaskStore()
    task = Task(
        title="Persist task",
        intent="Exercise the in-memory task store.",
        success_criteria=["CRUD works"],
        owner=Role.PROJECT_MANAGER,
    )

    created_task = store.create_task(task)
    fetched_task = store.get_task(str(created_task.id))

    assert fetched_task is not None
    assert fetched_task == created_task

    created_task.status = TaskStatus.IN_PROGRESS
    updated_task = store.update_task(created_task)

    assert updated_task.status is TaskStatus.IN_PROGRESS
    assert store.get_task(str(created_task.id)) == updated_task
    assert store.list_tasks() == [updated_task]
