"""Integration tests for TaskRunner."""
from __future__ import annotations

from pathlib import Path

from opendove.models.project import Project
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.orchestration.task_runner import TaskRunner
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore

from tests.integration.conftest import (
    FakeAlwaysEscalateAVA,
    FakeApproveAVA,
    FakeArchitectReview,
    FakeDeveloper,
    FakeLeadArchitect,
    FakeProductManager,
    FakeProjectManager,
)


def _setup() -> tuple[InMemoryTaskStore, ProjectDispatcher, Project]:
    task_store = InMemoryTaskStore()
    project_store = InMemoryProjectStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    project = dispatcher.register_project(
        Project(
            name="Runner Test Project",
            repo_url="https://github.com/test/repo.git",
            local_path=Path("/tmp/runner-test"),
        )
    )
    return task_store, dispatcher, project


def _all_approve_runner(task_store, dispatcher) -> TaskRunner:
    return TaskRunner(
        task_store=task_store,
        dispatcher=dispatcher,
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=FakeApproveAVA(),
    )


def test_runner_persists_approved_task() -> None:
    """TaskRunner with all-approve fake agents persists APPROVED task to task_store."""
    task_store, dispatcher, project = _setup()
    runner = _all_approve_runner(task_store, dispatcher)

    raw_task = Task(
        title="Runner Task",
        intent="Do something useful.",
        success_criteria=["It works."],
        owner=Role.DEVELOPER,
    )
    submitted = dispatcher.submit_task(project.id, raw_task)
    assert submitted.status == TaskStatus.IN_PROGRESS

    result = runner.run(submitted, project.id)

    assert result.status == TaskStatus.APPROVED
    stored = task_store.get_task(str(result.id))
    assert stored is not None
    assert stored.status == TaskStatus.APPROVED


def test_runner_calls_on_task_complete() -> None:
    """dispatcher.on_task_complete is called with the correct project_id and task_id."""
    task_store, dispatcher, project = _setup()

    original_on_task_complete = dispatcher.on_task_complete
    calls: list[tuple] = []

    def spy(project_id, task_id):
        calls.append((project_id, task_id))
        return original_on_task_complete(project_id, task_id)

    dispatcher.on_task_complete = spy  # type: ignore[method-assign]

    runner = _all_approve_runner(task_store, dispatcher)
    raw_task = Task(
        title="Spy Task",
        intent="Test the spy.",
        success_criteria=["Spy is called."],
        owner=Role.DEVELOPER,
    )
    submitted = dispatcher.submit_task(project.id, raw_task)
    runner.run(submitted, project.id)

    assert len(calls) == 1
    assert calls[0] == (project.id, submitted.id)


def test_runner_persists_escalated_task() -> None:
    """TaskRunner with escalating AVA persists ESCALATED task; on_task_complete still called."""
    task_store, dispatcher, project = _setup()

    calls: list[tuple] = []
    original = dispatcher.on_task_complete

    def spy(project_id, task_id):
        calls.append((project_id, task_id))
        return original(project_id, task_id)

    dispatcher.on_task_complete = spy  # type: ignore[method-assign]

    runner = TaskRunner(
        task_store=task_store,
        dispatcher=dispatcher,
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=FakeAlwaysEscalateAVA(),
    )

    raw_task = Task(
        title="Escalation Task",
        intent="Should escalate.",
        success_criteria=["Never passes."],
        owner=Role.DEVELOPER,
    )
    submitted = dispatcher.submit_task(project.id, raw_task)
    result = runner.run(submitted, project.id)

    assert result.status == TaskStatus.ESCALATED
    stored = task_store.get_task(str(result.id))
    assert stored is not None
    assert stored.status == TaskStatus.ESCALATED
    assert len(calls) == 1
    assert calls[0] == (project.id, submitted.id)


def test_runner_stores_execution_log() -> None:
    """TaskRunner persists a non-empty execution_log on the completed task."""
    task_store, dispatcher, project = _setup()
    runner = _all_approve_runner(task_store, dispatcher)

    raw_task = Task(
        title="Log Task",
        intent="Produce an execution log.",
        success_criteria=["Log is captured."],
        owner=Role.DEVELOPER,
    )
    submitted = dispatcher.submit_task(project.id, raw_task)
    result = runner.run(submitted, project.id)

    assert isinstance(result.execution_log, list)
    assert len(result.execution_log) > 0

    stored = task_store.get_task(str(result.id))
    assert stored is not None
    assert stored.execution_log == result.execution_log
