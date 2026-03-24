"""Tests for PjM priority queue, paused flag, and ProjectManagerAgent."""
from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from opendove.agents.project_manager import ProjectManagerAgent
from opendove.models.project import Project, ProjectStatus
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.orchestration.graph import GraphState
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


def _make_dispatcher() -> tuple[ProjectDispatcher, InMemoryProjectStore, InMemoryTaskStore]:
    project_store = InMemoryProjectStore()
    task_store = InMemoryTaskStore()
    dispatcher = ProjectDispatcher(project_store, task_store)
    return dispatcher, project_store, task_store


def test_p0_dequeued_before_p1() -> None:
    dispatcher, project_store, task_store = _make_dispatcher()
    project = dispatcher.register_project(_build_project())

    # First task starts immediately (project is idle)
    anchor_task = dispatcher.submit_task(project.id, _build_task("anchor"))
    assert anchor_task.status is TaskStatus.IN_PROGRESS

    # Submit P1 task first, then P0 task — both go to queue
    p1_task = dispatcher.submit_task(project.id, _build_task("P1 task"))
    p0_task = dispatcher.submit_task(project.id, _build_task("P0 task"))

    assert p1_task.status is TaskStatus.PENDING
    assert p0_task.status is TaskStatus.PENDING

    # Re-sort queue: P0 first
    priority_map = {p1_task.id: 1, p0_task.id: 0}
    dispatcher.prioritize_queue(project.id, priority_map)

    # Complete the anchor task; P0 should be dequeued next
    next_task = dispatcher.on_task_complete(project.id, anchor_task.id)
    assert next_task is not None
    assert next_task.id == p0_task.id
    assert next_task.status is TaskStatus.IN_PROGRESS


def test_p0_dequeued_before_p2() -> None:
    dispatcher, project_store, task_store = _make_dispatcher()
    project = dispatcher.register_project(_build_project())

    anchor_task = dispatcher.submit_task(project.id, _build_task("anchor"))
    assert anchor_task.status is TaskStatus.IN_PROGRESS

    dispatcher.submit_task(project.id, _build_task("P2 task"))
    p0_task = dispatcher.submit_task(project.id, _build_task("P0 task"))

    # P2 has no entry in priority_map (defaults to 2), P0 is 0
    priority_map = {p0_task.id: 0}
    dispatcher.prioritize_queue(project.id, priority_map)

    next_task = dispatcher.on_task_complete(project.id, anchor_task.id)
    assert next_task is not None
    assert next_task.id == p0_task.id
    assert next_task.status is TaskStatus.IN_PROGRESS


def test_paused_project_does_not_start_task_on_submit() -> None:
    dispatcher, project_store, task_store = _make_dispatcher()
    project = dispatcher.register_project(_build_project())

    # Submit first task (starts immediately)
    first_task = dispatcher.submit_task(project.id, _build_task("first"))
    assert first_task.status is TaskStatus.IN_PROGRESS

    # Complete the task so project goes IDLE
    dispatcher.on_task_complete(project.id, first_task.id)
    stored = project_store.get_project(str(project.id))
    assert stored is not None
    assert stored.status is ProjectStatus.IDLE

    # Pause the project
    dispatcher.pause_project(project.id)

    # Submit a second task — should be queued, not started
    second_task = dispatcher.submit_task(project.id, _build_task("second"))
    assert second_task.status is TaskStatus.PENDING

    stored = project_store.get_project(str(project.id))
    assert stored is not None
    assert stored.status is ProjectStatus.IDLE
    assert second_task.id in stored.task_queue


def test_paused_project_does_not_dequeue_on_complete() -> None:
    dispatcher, project_store, task_store = _make_dispatcher()
    project = dispatcher.register_project(_build_project())

    # Start a task
    first_task = dispatcher.submit_task(project.id, _build_task("first"))
    assert first_task.status is TaskStatus.IN_PROGRESS

    # Queue a second task
    second_task = dispatcher.submit_task(project.id, _build_task("second"))
    assert second_task.status is TaskStatus.PENDING

    # Pause the project while active
    dispatcher.pause_project(project.id)

    # Complete the active task — project should go IDLE, no next task started
    result = dispatcher.on_task_complete(project.id, first_task.id)
    assert result is None

    stored = project_store.get_project(str(project.id))
    assert stored is not None
    assert stored.status is ProjectStatus.IDLE
    assert stored.active_task_id is None
    # Second task should still be in the queue
    assert second_task.id in stored.task_queue


def test_unpause_starts_next_eligible_task() -> None:
    dispatcher, project_store, task_store = _make_dispatcher()
    project = dispatcher.register_project(_build_project())

    # Start a task then complete it so project is IDLE
    first_task = dispatcher.submit_task(project.id, _build_task("first"))
    dispatcher.on_task_complete(project.id, first_task.id)

    # Pause the project before submitting another task
    dispatcher.pause_project(project.id)

    # Submit task while paused — queued, not started
    queued_task = dispatcher.submit_task(project.id, _build_task("queued"))
    assert queued_task.status is TaskStatus.PENDING

    stored = project_store.get_project(str(project.id))
    assert stored is not None
    assert stored.status is ProjectStatus.IDLE

    # Unpause — should immediately start the queued task
    started = dispatcher.unpause_project(project.id)
    assert started is not None
    assert started.id == queued_task.id
    assert started.status is TaskStatus.IN_PROGRESS

    stored = project_store.get_project(str(project.id))
    assert stored is not None
    assert stored.status is ProjectStatus.ACTIVE
    assert stored.active_task_id == queued_task.id
    assert stored.paused is False


def test_pjm_agent_run_includes_issue_number() -> None:
    fake_llm = FakeListChatModel(responses=["unused"])
    agent = ProjectManagerAgent(
        llm=fake_llm,
        system_prompt=ProjectManagerAgent.DEFAULT_SYSTEM_PROMPT,
    )

    task = Task(
        title="Fix login bug",
        intent="Fix the authentication failure.",
        success_criteria=["Login works"],
        owner=Role.DEVELOPER,
        github_issue_number=42,
    )

    state: GraphState = {
        "task": task,
        "messages": [],
        "retry_count": 0,
    }

    result = agent.run(state)

    messages = result["messages"]
    assert len(messages) == 1
    assert "issue #42" in messages[0]
    assert "Fix login bug" in messages[0]
