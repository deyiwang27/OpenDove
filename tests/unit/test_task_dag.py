from pathlib import Path
from uuid import UUID

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


def _build_task(title: str, depends_on: list[UUID] | None = None) -> Task:
    return Task(
        title=title,
        intent=f"Execute {title}.",
        success_criteria=[f"{title} is complete."],
        owner=Role.PROJECT_MANAGER,
        depends_on=[] if depends_on is None else depends_on,
    )


def test_submit_task_with_no_deps_starts_immediately() -> None:
    dispatcher = ProjectDispatcher(InMemoryProjectStore(), InMemoryTaskStore())
    project = dispatcher.register_project(_build_project())

    task = dispatcher.submit_task(project.id, _build_task("Task A", []))

    assert task.status is TaskStatus.IN_PROGRESS


def test_submit_task_with_unmet_deps_stays_pending() -> None:
    project_store = InMemoryProjectStore()
    dispatcher = ProjectDispatcher(project_store, InMemoryTaskStore())
    project = dispatcher.register_project(_build_project())

    task_a = dispatcher.submit_task(project.id, _build_task("Task A"))
    task_b = dispatcher.submit_task(project.id, _build_task("Task B", [task_a.id]))
    stored_project = project_store.get_project(str(project.id))

    assert task_a.status is TaskStatus.IN_PROGRESS
    assert task_b.status is TaskStatus.PENDING
    assert stored_project is not None
    assert stored_project.task_queue == [task_b.id]


def test_get_next_eligible_task_skips_blocked_tasks() -> None:
    dispatcher = ProjectDispatcher(InMemoryProjectStore(), InMemoryTaskStore())
    project = dispatcher.register_project(_build_project())

    task_a = dispatcher.submit_task(project.id, _build_task("Task A"))
    task_b = dispatcher.submit_task(project.id, _build_task("Task B", [task_a.id]))
    task_c = dispatcher.submit_task(project.id, _build_task("Task C"))

    next_task = dispatcher.get_next_eligible_task(project.id)

    assert task_b.status is TaskStatus.PENDING
    assert task_c.status is TaskStatus.PENDING
    assert next_task is not None
    assert next_task.id == task_c.id


def test_circular_dependency_raises() -> None:
    dispatcher = ProjectDispatcher(InMemoryProjectStore(), InMemoryTaskStore())
    project = dispatcher.register_project(_build_project())

    task_b = _build_task("Task B")
    task_a = _build_task("Task A", [task_b.id])
    dispatcher.submit_task(project.id, task_a)

    with pytest.raises(ValueError, match="Circular dependency detected"):
        dispatcher.submit_task(project.id, task_b.model_copy(update={"depends_on": [task_a.id]}))


def test_task_becomes_eligible_after_dependency_approved() -> None:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(_build_project())

    task_a = dispatcher.submit_task(project.id, _build_task("Task A"))
    task_b = dispatcher.submit_task(project.id, _build_task("Task B", [task_a.id]))
    approved_task_a = task_store.update_task(task_a.model_copy(update={"status": TaskStatus.APPROVED}))

    next_task = dispatcher.on_task_complete(project.id, approved_task_a.id)
    stored_project = project_store.get_project(str(project.id))

    assert next_task is not None
    assert next_task.id == task_b.id
    assert next_task.status is TaskStatus.IN_PROGRESS
    assert stored_project is not None
    assert stored_project.status is ProjectStatus.ACTIVE
    assert stored_project.active_task_id == task_b.id
    assert stored_project.task_queue == []


def test_risk_level_defaults_to_low() -> None:
    task = _build_task("Task A")

    assert task.risk_level == "low"
