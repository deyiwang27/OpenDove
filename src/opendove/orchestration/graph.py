from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from opendove.models.task import Role, Task, TaskStatus
from opendove.validation.contracts import ValidationDecision, ValidationResult


class GraphState(TypedDict):
    task: Task
    messages: list[str]
    retry_count: int


GraphNode = Callable[[GraphState], GraphState]


def product_manager_node(state: GraphState) -> GraphState:
    task = state["task"]
    task.status = TaskStatus.IN_PROGRESS

    return {
        **state,
        "task": task,
        "messages": [*state["messages"], "ProductManager: spec locked."],
    }


def project_manager_node(state: GraphState) -> GraphState:
    task = state["task"]

    return {
        **state,
        "task": task,
        "messages": [
            *state["messages"],
            f"ProjectManager: task assigned, max_retries={task.max_retries}.",
        ],
    }


def lead_architect_node(state: GraphState) -> GraphState:
    return {
        **state,
        "messages": [*state["messages"], "Architect: approach defined."],
    }


def developer_node(state: GraphState) -> GraphState:
    task = state["task"]
    task.artifact = "implementation_stub"
    task.status = TaskStatus.AWAITING_VALIDATION

    return {
        **state,
        "task": task,
        "messages": [*state["messages"], "Developer: implementation complete."],
    }


def ava_node(state: GraphState) -> GraphState:
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
    }


def _route_after_ava(state: GraphState) -> Literal["approve", "reject", "escalate"]:
    validation_result = state["task"].validation_result
    if validation_result is None:
        raise ValueError("AVA must set task.validation_result before routing.")

    if validation_result.decision is ValidationDecision.APPROVE:
        return "approve"
    if validation_result.decision is ValidationDecision.REJECT:
        return "reject"
    return "escalate"


def build_orchestration_summary() -> str:
    ordered_roles = [
        Role.PRODUCT_MANAGER,
        Role.PROJECT_MANAGER,
        Role.LEAD_ARCHITECT,
        Role.DEVELOPER,
        Role.AVA,
    ]
    path = " -> ".join(role.value for role in ordered_roles)
    return f"OpenDove orchestration path: {path}"


def build_graph(developer_node_fn: GraphNode | None = None) -> Any:
    graph_builder = StateGraph(GraphState)
    effective_developer_node = developer_node_fn or developer_node

    graph_builder.add_node("product_manager_node", product_manager_node)
    graph_builder.add_node("project_manager_node", project_manager_node)
    graph_builder.add_node("lead_architect_node", lead_architect_node)
    graph_builder.add_node("developer_node", effective_developer_node)
    graph_builder.add_node("ava_node", ava_node)

    graph_builder.add_edge(START, "product_manager_node")
    graph_builder.add_edge("product_manager_node", "project_manager_node")
    graph_builder.add_edge("project_manager_node", "lead_architect_node")
    graph_builder.add_edge("lead_architect_node", "developer_node")
    graph_builder.add_edge("developer_node", "ava_node")
    graph_builder.add_conditional_edges(
        "ava_node",
        _route_after_ava,
        {
            "approve": END,
            "reject": "developer_node",
            "escalate": END,
        },
    )

    return graph_builder.compile()
