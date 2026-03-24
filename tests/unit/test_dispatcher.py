from pathlib import Path
from uuid import uuid4

import pytest

from opendove.models.project import Project, ProjectStatus
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore


def _build_project() -> Project:
    return Project(
        name="OpenDove",
        repo_url="https://example.com/opendove.git",
        local_path=Path("/tmp/opendove/main"),
    )


def _build_task(title: str) -> Task:
    return Task(
        title=title,
        intent=f"Execute {title}.",
        success_criteria=[f"{title} is complete."],
        owner=Role.PROJECT_MANAGER,
    )


def test_submit_task_to_idle_project_starts_immediately() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())

    task = dispatcher.submit_task(project.id, _build_task("Task 1"))
    stored_project = project_store.get_project(str(project.id))

    assert task.status is TaskStatus.IN_PROGRESS
    assert task.project_id == project.id
    assert stored_project is not None
    assert stored_project.status is ProjectStatus.ACTIVE
    assert stored_project.active_task_id == task.id
    assert stored_project.task_queue == []


def test_submit_task_to_busy_project_queues_it() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())

    first_task = dispatcher.submit_task(project.id, _build_task("Task 1"))
    second_task = dispatcher.submit_task(project.id, _build_task("Task 2"))
    stored_project = project_store.get_project(str(project.id))

    assert first_task.status is TaskStatus.IN_PROGRESS
    assert second_task.status is TaskStatus.PENDING
    assert stored_project is not None
    assert stored_project.active_task_id == first_task.id
    assert len(stored_project.task_queue) == 1
    assert stored_project.task_queue == [second_task.id]


def test_on_task_complete_goes_idle_when_no_queue() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())

    task = dispatcher.submit_task(project.id, _build_task("Task 1"))

    next_task = dispatcher.on_task_complete(project.id, task.id)
    stored_project = project_store.get_project(str(project.id))

    assert next_task is None
    assert stored_project is not None
    assert stored_project.status is ProjectStatus.IDLE
    assert stored_project.active_task_id is None
    assert stored_project.task_queue == []


def test_on_task_complete_dequeues_next_task() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())

    first_task = dispatcher.submit_task(project.id, _build_task("Task 1"))
    second_task = dispatcher.submit_task(project.id, _build_task("Task 2"))

    next_task = dispatcher.on_task_complete(project.id, first_task.id)
    stored_project = project_store.get_project(str(project.id))

    assert next_task is not None
    assert next_task.id == second_task.id
    assert next_task.status is TaskStatus.IN_PROGRESS
    assert stored_project is not None
    assert stored_project.status is ProjectStatus.ACTIVE
    assert stored_project.active_task_id == second_task.id
    assert stored_project.task_queue == []


def test_submit_task_raises_on_unknown_project() -> None:
    dispatcher = ProjectDispatcher(InMemoryProjectStore(), InMemoryTaskStore())

    with pytest.raises(KeyError):
        dispatcher.submit_task(uuid4(), _build_task("Unknown project task"))
