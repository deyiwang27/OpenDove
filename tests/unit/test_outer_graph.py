from pathlib import Path

from opendove.github.client import GitHubIssue
from opendove.models.project import Project
from opendove.models.task import TaskStatus
from opendove.orchestration.outer_graph import build_outer_graph


def _build_project() -> Project:
    return Project(
        name="OpenDove",
        repo_url="https://example.com/opendove.git",
        local_path=Path("/tmp/opendove"),
    )


def _build_issue() -> GitHubIssue:
    return GitHubIssue(
        number=14,
        title="Two-level LangGraph",
        body="Replace the flat graph with outer and inner orchestration layers.",
        labels=["enhancement"],
        state="open",
        html_url="https://example.com/issues/14",
    )


def test_outer_graph_happy_path() -> None:
    graph = build_outer_graph()

    result = graph.invoke(
        {
            "project": _build_project(),
            "current_issue": _build_issue(),
            "sub_tasks": [],
            "completed_sub_tasks": [],
            "messages": [],
            "cycle_count": 0,
        }
    )

    assert result["cycle_count"] == 1
    assert result["messages"] == [
        "PdM: scanned roadmap and feedback, identified work items.",
        "PjM: queue prioritized.",
        "Architect: broke issue into 2 sub-tasks.",
        "SubTaskRunner: all 2 sub-tasks completed.",
        "PjM: issue closed, progress updated.",
        "PdM: reviewed merged work. No new issues found.",
    ]


def test_outer_graph_sub_tasks_completed() -> None:
    graph = build_outer_graph()

    result = graph.invoke(
        {
            "project": _build_project(),
            "current_issue": _build_issue(),
            "sub_tasks": [],
            "completed_sub_tasks": [],
            "messages": [],
            "cycle_count": 0,
        }
    )

    assert len(result["completed_sub_tasks"]) == 2
    assert all(task.status is TaskStatus.APPROVED for task in result["completed_sub_tasks"])


def test_outer_graph_messages_ordered() -> None:
    graph = build_outer_graph()

    result = graph.invoke(
        {
            "project": _build_project(),
            "current_issue": _build_issue(),
            "sub_tasks": [],
            "completed_sub_tasks": [],
            "messages": [],
            "cycle_count": 0,
        }
    )

    assert result["messages"] == [
        "PdM: scanned roadmap and feedback, identified work items.",
        "PjM: queue prioritized.",
        "Architect: broke issue into 2 sub-tasks.",
        "SubTaskRunner: all 2 sub-tasks completed.",
        "PjM: issue closed, progress updated.",
        "PdM: reviewed merged work. No new issues found.",
    ]
