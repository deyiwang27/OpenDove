from __future__ import annotations

from collections import deque
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from opendove.github.client import GitHubIssue
from opendove.models.project import Project
from opendove.models.task import Role, Task
from opendove.orchestration.graph import build_graph


class OuterGraphState(TypedDict):
    project: Project
    current_issue: GitHubIssue | None
    sub_tasks: list[Task]
    completed_sub_tasks: list[Task]
    messages: list[str]
    cycle_count: int


def pdm_scan_node(state: OuterGraphState) -> OuterGraphState:
    return {
        **state,
        "messages": [
            *state["messages"],
            "PdM: scanned roadmap and feedback, identified work items.",
        ],
    }


def pjm_prioritize_node(state: OuterGraphState) -> OuterGraphState:
    return {
        **state,
        "messages": [*state["messages"], "PjM: queue prioritized."],
    }


def architect_breakdown_node(state: OuterGraphState) -> OuterGraphState:
    issue = state["current_issue"]
    if issue is None:
        return {
            **state,
            "sub_tasks": [],
            "messages": [*state["messages"], "Architect: no issue available for breakdown."],
        }

    sub_tasks = [
        Task(
            title=f"Sub-task 1: {issue.title}",
            intent=issue.body,
            success_criteria=["Implementation completed", "Validation approved"],
            owner=Role.PROJECT_MANAGER,
            project_id=state["project"].id,
            parent_issue_number=issue.number,
        ),
        Task(
            title=f"Sub-task 2: {issue.title}",
            intent=issue.body,
            success_criteria=["Implementation completed", "Validation approved"],
            owner=Role.PROJECT_MANAGER,
            project_id=state["project"].id,
            parent_issue_number=issue.number,
        ),
    ]

    return {
        **state,
        "sub_tasks": sub_tasks,
        "messages": [*state["messages"], "Architect: broke issue into 2 sub-tasks."],
    }


def _order_sub_tasks(sub_tasks: list[Task]) -> list[Task]:
    tasks_by_id = {task.id: task for task in sub_tasks}
    in_degree = {task.id: 0 for task in sub_tasks}
    dependents: dict[UUID, list[Task]] = {task.id: [] for task in sub_tasks}

    for task in sub_tasks:
        for dependency_id in task.depends_on:
            if dependency_id not in tasks_by_id:
                continue
            in_degree[task.id] += 1
            dependents[dependency_id].append(task)

    ready = deque(task for task in sub_tasks if in_degree[task.id] == 0)
    ordered: list[Task] = []

    while ready:
        task = ready.popleft()
        ordered.append(task)
        for dependent in dependents[task.id]:
            in_degree[dependent.id] -= 1
            if in_degree[dependent.id] == 0:
                ready.append(dependent)

    if len(ordered) != len(sub_tasks):
        raise ValueError("Circular dependency detected in sub-task graph")

    return ordered


def run_sub_tasks_node(state: OuterGraphState) -> OuterGraphState:
    inner_graph = build_graph()
    completed_sub_tasks = list(state["completed_sub_tasks"])

    for task in _order_sub_tasks(state["sub_tasks"]):
        result = inner_graph.invoke(
            {
                "task": task,
                "messages": [],
                "retry_count": 0,
                "architect_retry_count": 0,
                "worktree_path": "",
            }
        )
        completed_sub_tasks.append(result["task"])

    return {
        **state,
        "completed_sub_tasks": completed_sub_tasks,
        "messages": [
            *state["messages"],
            f"SubTaskRunner: all {len(state['sub_tasks'])} sub-tasks completed.",
        ],
    }


def pjm_close_node(state: OuterGraphState) -> OuterGraphState:
    return {
        **state,
        "messages": [*state["messages"], "PjM: issue closed, progress updated."],
    }


def pdm_review_node(state: OuterGraphState) -> OuterGraphState:
    return {
        **state,
        "cycle_count": state["cycle_count"] + 1,
        "messages": [*state["messages"], "PdM: reviewed merged work. No new issues found."],
    }


def build_outer_graph() -> Any:
    graph_builder = StateGraph(OuterGraphState)
    graph_builder.add_node("pdm_scan_node", pdm_scan_node)
    graph_builder.add_node("pjm_prioritize_node", pjm_prioritize_node)
    graph_builder.add_node("architect_breakdown_node", architect_breakdown_node)
    graph_builder.add_node("run_sub_tasks_node", run_sub_tasks_node)
    graph_builder.add_node("pjm_close_node", pjm_close_node)
    graph_builder.add_node("pdm_review_node", pdm_review_node)

    graph_builder.add_edge(START, "pdm_scan_node")
    graph_builder.add_edge("pdm_scan_node", "pjm_prioritize_node")
    graph_builder.add_edge("pjm_prioritize_node", "architect_breakdown_node")
    graph_builder.add_edge("architect_breakdown_node", "run_sub_tasks_node")
    graph_builder.add_edge("run_sub_tasks_node", "pjm_close_node")
    graph_builder.add_edge("pjm_close_node", "pdm_review_node")
    graph_builder.add_edge("pdm_review_node", END)

    return graph_builder.compile()
