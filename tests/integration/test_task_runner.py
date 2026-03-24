"""Integration tests for TaskRunner."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock


from opendove.agents.base import BaseAgent
from opendove.models.project import Project
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.orchestration.task_runner import TaskRunner
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore
from opendove.validation.contracts import ValidationDecision, ValidationResult

# Re-use fake agent definitions from the inner graph tests
from tests.integration.test_inner_graph_e2e import (
    FakeApproveAVA,
    FakeArchitectReview,
    FakeDeveloper,
    FakeLeadArchitect,
    FakeProductManager,
    FakeProjectManager,
)


# ---------------------------------------------------------------------------
# Fake escalating agent helpers
# ---------------------------------------------------------------------------


class FakeAlwaysEscalateAVA(BaseAgent):
    """Always escalates immediately."""

    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state):
        task = state["task"].model_copy(
            update={
                "status": TaskStatus.ESCALATED,
                "validation_result": ValidationResult(
                    task_id=state["task"].id,
                    decision=ValidationDecision.ESCALATE,
                    rationale="Escalated immediately.",
                    checks=[],
                ),
            }
        )
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "AVA: escalate."],
            "worktree_path": state.get("worktree_path", ""),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_runner_persists_approved_task() -> None:
    """TaskRunner with all-approve fake agents persists APPROVED task to task_store."""
    task_store, dispatcher, project = _setup()

    runner = TaskRunner(
        task_store=task_store,
        dispatcher=dispatcher,
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=FakeApproveAVA(),
    )

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
    # Verify it's in the store
    stored = task_store.get_task(str(result.id))
    assert stored is not None
    assert stored.status == TaskStatus.APPROVED


def test_runner_calls_on_task_complete() -> None:
    """Dispatcher.on_task_complete is called with the correct project_id and task_id."""
    task_store, dispatcher, project = _setup()

    # Spy on on_task_complete
    original_on_task_complete = dispatcher.on_task_complete
    calls: list[tuple] = []

    def spy_on_task_complete(project_id, task_id):
        calls.append((project_id, task_id))
        return original_on_task_complete(project_id, task_id)

    dispatcher.on_task_complete = spy_on_task_complete  # type: ignore[method-assign]

    runner = TaskRunner(
        task_store=task_store,
        dispatcher=dispatcher,
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=FakeApproveAVA(),
    )

    raw_task = Task(
        title="Spy Task",
        intent="Test the spy.",
        success_criteria=["Spy is called."],
        owner=Role.DEVELOPER,
    )
    submitted = dispatcher.submit_task(project.id, raw_task)

    runner.run(submitted, project.id)

    assert len(calls) == 1
    called_project_id, called_task_id = calls[0]
    assert called_project_id == project.id
    assert called_task_id == submitted.id


def test_runner_persists_escalated_task() -> None:
    """TaskRunner with escalating fake AVA persists ESCALATED task; on_task_complete still called."""
    task_store, dispatcher, project = _setup()

    calls: list[tuple] = []
    original_on_task_complete = dispatcher.on_task_complete

    def spy_on_task_complete(project_id, task_id):
        calls.append((project_id, task_id))
        return original_on_task_complete(project_id, task_id)

    dispatcher.on_task_complete = spy_on_task_complete  # type: ignore[method-assign]

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

    # on_task_complete was still called
    assert len(calls) == 1
    assert calls[0] == (project.id, submitted.id)
