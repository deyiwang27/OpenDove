"""Integration tests for the API pipeline using FastAPI TestClient."""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from opendove.api.app import app
from opendove.api.dependencies import reset_state
from opendove.models.project import ProjectStatus
from opendove.models.task import TaskStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_api_state() -> Generator[None, None, None]:
    reset_state()
    yield
    reset_state()


def _register_project() -> dict:
    response = client.post(
        "/projects",
        json={
            "name": "Pipeline Test Project",
            "repo_url": "https://example.com/test.git",
            "default_branch": "main",
        },
    )
    assert response.status_code == 201
    return response.json()


def _submit_task(project_id: str, title: str) -> dict:
    response = client.post(
        f"/projects/{project_id}/tasks",
        json={
            "title": title,
            "intent": f"Execute {title}.",
            "success_criteria": [f"{title} is complete."],
        },
    )
    assert response.status_code == 202
    return response.json()


def test_submit_task_sets_in_progress() -> None:
    """Register a project, submit one task, GET /tasks/{id} shows IN_PROGRESS."""
    project = _register_project()
    task = _submit_task(project["id"], "Task Alpha")

    assert task["status"] == TaskStatus.IN_PROGRESS.value

    response = client.get(f"/tasks/{task['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task["id"]
    assert body["status"] == TaskStatus.IN_PROGRESS.value
    assert body["project_id"] == project["id"]


def test_two_tasks_queue_correctly() -> None:
    """Submit two tasks to same project; first is IN_PROGRESS, second is PENDING; queued_task_count=1."""
    project = _register_project()
    first = _submit_task(project["id"], "Task First")
    second = _submit_task(project["id"], "Task Second")

    assert first["status"] == TaskStatus.IN_PROGRESS.value
    assert second["status"] == TaskStatus.PENDING.value

    response = client.get(f"/projects/{project['id']}")
    assert response.status_code == 200
    project_body = response.json()
    assert project_body["status"] == ProjectStatus.ACTIVE.value
    assert project_body["queued_task_count"] == 1
    assert project_body["active_task_id"] == first["id"]
