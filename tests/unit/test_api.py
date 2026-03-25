from collections.abc import Generator
from uuid import uuid4

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


def _register_project() -> dict[str, str]:
    response = client.post(
        "/projects",
        json={
            "name": "OpenDove",
            "repo_url": "https://example.com/opendove.git",
            "default_branch": "main",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_project() -> None:
    response = client.post(
        "/projects",
        json={
            "name": "OpenDove",
            "repo_url": "https://example.com/opendove.git",
            "default_branch": "main",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "OpenDove"
    assert body["status"] == ProjectStatus.IDLE.value
    assert body["active_task_id"] is None
    assert body["queued_task_count"] == 0


def test_get_project_not_found() -> None:
    response = client.get(f"/projects/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_get_project_after_register() -> None:
    project = _register_project()

    response = client.get(f"/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "OpenDove"


def test_submit_task_to_idle_project() -> None:
    project = _register_project()

    response = client.post(
        f"/projects/{project['id']}/tasks",
        json={
            "title": "Task 1",
            "intent": "Execute Task 1.",
            "success_criteria": ["Task 1 is complete."],
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["title"] == "Task 1"
    assert body["status"] == TaskStatus.QUEUED.value


def test_submit_task_to_busy_project() -> None:
    project = _register_project()

    first_response = client.post(
        f"/projects/{project['id']}/tasks",
        json={
            "title": "Task 1",
            "intent": "Execute Task 1.",
            "success_criteria": ["Task 1 is complete."],
        },
    )
    second_response = client.post(
        f"/projects/{project['id']}/tasks",
        json={
            "title": "Task 2",
            "intent": "Execute Task 2.",
            "success_criteria": ["Task 2 is complete."],
        },
    )

    assert first_response.status_code == 202
    assert first_response.json()["status"] == TaskStatus.QUEUED.value
    assert second_response.status_code == 202
    assert second_response.json()["status"] == TaskStatus.PENDING.value


def test_get_task() -> None:
    project = _register_project()
    task_response = client.post(
        f"/projects/{project['id']}/tasks",
        json={
            "title": "Task 1",
            "intent": "Execute Task 1.",
            "success_criteria": ["Task 1 is complete."],
        },
    )
    assert task_response.status_code == 202
    task = task_response.json()

    response = client.get(f"/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Task 1"


def test_submit_task_to_unknown_project() -> None:
    response = client.post(
        f"/projects/{uuid4()}/tasks",
        json={
            "title": "Task 1",
            "intent": "Execute Task 1.",
            "success_criteria": ["Task 1 is complete."],
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}
