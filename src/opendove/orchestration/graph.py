from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from opendove.agents.base import BaseAgent, LLMCallError
from opendove.models.task import Role, Task, TaskStatus
from opendove.validation.contracts import ValidationDecision, ValidationResult

_log = __import__("logging").getLogger(__name__)


class GraphState(TypedDict):
    task: Task
    messages: list[str]
    retry_count: int
    architect_retry_count: NotRequired[int]
    worktree_path: NotRequired[str]


GraphNode = Callable[[GraphState], GraphState]


def product_manager_node(state: GraphState) -> GraphState:
    task = state["task"]
    task.status = TaskStatus.IN_PROGRESS

    return {
        **state,
        "task": task,
        "messages": [*state["messages"], "ProductManager: spec locked."],
        "architect_retry_count": state.get("architect_retry_count", 0),
        "worktree_path": state.get("worktree_path", ""),
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
        "architect_retry_count": state.get("architect_retry_count", 0),
        "worktree_path": state.get("worktree_path", ""),
    }


def lead_architect_node(state: GraphState) -> GraphState:
    return {
        **state,
        "messages": [*state["messages"], "Architect: approach defined."],
        "architect_retry_count": state.get("architect_retry_count", 0),
        "worktree_path": state.get("worktree_path", ""),
    }


def developer_node(state: GraphState) -> GraphState:
    task = state["task"]
    task.artifact = "implementation_stub"
    task.status = TaskStatus.AWAITING_VALIDATION

    return {
        **state,
        "task": task,
        "messages": [*state["messages"], "Developer: implementation complete."],
        "architect_retry_count": state.get("architect_retry_count", 0),
        "worktree_path": state.get("worktree_path", ""),
    }


def architect_review_node(state: GraphState) -> GraphState:
    task = state["task"]
    architect_retry_count = state.get("architect_retry_count", 0) + 1
    task.artifact = "revised_implementation_stub"
    task.status = TaskStatus.AWAITING_VALIDATION

    return {
        **state,
        "task": task,
        "architect_retry_count": architect_retry_count,
        "messages": [
            *state["messages"],
            f"Architect: revised after AVA rejection (attempt {architect_retry_count}).",
        ],
        "worktree_path": state.get("worktree_path", ""),
    }


def ava_node(state: GraphState) -> GraphState:
    task = state["task"]
    retry_count = state["retry_count"]
    architect_retry_count = state.get("architect_retry_count", 0)

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
    elif architect_retry_count >= 2:
        task.status = TaskStatus.ESCALATED
        decision = ValidationDecision.ESCALATE
        rationale = "Architect retry limit reached."
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
        "architect_retry_count": architect_retry_count,
        "messages": [*state["messages"], f"AVA: {decision.value}."],
        "worktree_path": state.get("worktree_path", ""),
    }


def _route_after_ava(state: GraphState) -> Literal["approve", "architect_review", "escalate"]:
    validation_result = state["task"].validation_result
    if validation_result is None:
        raise ValueError("AVA must set task.validation_result before routing.")

    if validation_result.decision is ValidationDecision.APPROVE:
        return "approve"
    if validation_result.decision is ValidationDecision.ESCALATE:
        return "escalate"
    if state.get("architect_retry_count", 0) < 2:
        return "architect_review"
    return "escalate"


def _wrap_with_llm_error_guard(node_fn: GraphNode, node_name: str) -> GraphNode:
    """Wrap a graph node so that LLMCallError escalates the task instead of crashing."""

    def guarded(state: GraphState) -> GraphState:
        try:
            return node_fn(state)
        except LLMCallError as exc:
            _log.error("LLM call failed in %s, escalating task: %s", node_name, exc)
            task = state["task"].model_copy(
                update={
                    "status": TaskStatus.ESCALATED,
                    "validation_result": ValidationResult(
                        task_id=state["task"].id,
                        decision=ValidationDecision.ESCALATE,
                        rationale=f"LLM call failed in {node_name}: {exc}",
                    ),
                }
            )
            return {
                **state,
                "task": task,
                "messages": [
                    *state["messages"],
                    f"{node_name}: escalated due to LLM failure.",
                ],
            }

    return guarded


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


def build_graph(
    developer_node_fn: GraphNode | None = None,
    product_manager_agent: BaseAgent | None = None,
    project_manager_agent: BaseAgent | None = None,
    lead_architect_agent: BaseAgent | None = None,
    architect_review_agent: BaseAgent | None = None,
    developer_agent: BaseAgent | None = None,
    ava_agent: BaseAgent | None = None,
) -> Any:
    graph_builder = StateGraph(GraphState)
    effective_developer_node = developer_node_fn or developer_node

    raw_nodes: dict[str, GraphNode] = {
        "product_manager_node": (
            product_manager_agent.run if product_manager_agent is not None else product_manager_node
        ),
        "project_manager_node": (
            project_manager_agent.run if project_manager_agent is not None else project_manager_node
        ),
        "lead_architect_node": (
            lead_architect_agent.run if lead_architect_agent is not None else lead_architect_node
        ),
        "architect_review_node": (
            architect_review_agent.run
            if architect_review_agent is not None
            else architect_review_node
        ),
        "developer_node": (
            developer_agent.run if developer_agent is not None else effective_developer_node
        ),
        "ava_node": ava_agent.run if ava_agent is not None else ava_node,
    }

    for name, fn in raw_nodes.items():
        graph_builder.add_node(name, _wrap_with_llm_error_guard(fn, name))

    def _route_after_pipeline_node(
        next_node: str,
    ) -> Callable[[GraphState], Literal["escalate"] | str]:
        def _router(state: GraphState) -> Literal["escalate"] | str:
            if state["task"].status is TaskStatus.ESCALATED:
                return "escalate"
            return next_node

        return _router

    graph_builder.add_edge(START, "product_manager_node")
    for src, dst in [
        ("product_manager_node", "project_manager_node"),
        ("project_manager_node", "lead_architect_node"),
        ("lead_architect_node", "developer_node"),
        ("developer_node", "ava_node"),
    ]:
        graph_builder.add_conditional_edges(
            src,
            _route_after_pipeline_node(dst),
            {"escalate": END, dst: dst},
        )

    graph_builder.add_conditional_edges(
        "ava_node",
        _route_after_ava,
        {
            "approve": END,
            "architect_review": "architect_review_node",
            "escalate": END,
        },
    )
    graph_builder.add_conditional_edges(
        "architect_review_node",
        _route_after_pipeline_node("ava_node"),
        {"escalate": END, "ava_node": "ava_node"},
    )

    return graph_builder.compile()
