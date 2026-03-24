from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from opendove.agents.base import BaseAgent
from opendove.models.project import Project
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.dispatcher import ProjectDispatcher
from opendove.orchestration.graph import GraphState
from opendove.state.memory_project_store import InMemoryProjectStore
from opendove.state.memory_store import InMemoryTaskStore
from opendove.validation.contracts import ValidationDecision, ValidationResult


# ---------------------------------------------------------------------------
# Fake agents — shared across all integration tests
# ---------------------------------------------------------------------------


class FakeProductManager(BaseAgent):
    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        task = state["task"].model_copy(update={"status": TaskStatus.IN_PROGRESS})
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "ProductManager: spec locked."],
            "architect_retry_count": state.get("architect_retry_count", 0),
            "worktree_path": state.get("worktree_path", ""),
        }


class FakeProjectManager(BaseAgent):
    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        return {
            **state,
            "messages": [*state["messages"], "ProjectManager: task assigned."],
            "architect_retry_count": state.get("architect_retry_count", 0),
            "worktree_path": state.get("worktree_path", ""),
        }


class FakeLeadArchitect(BaseAgent):
    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        return {
            **state,
            "messages": [*state["messages"], "Architect: approach defined."],
            "architect_retry_count": state.get("architect_retry_count", 0),
            "worktree_path": state.get("worktree_path", ""),
        }


class FakeArchitectReview(BaseAgent):
    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        architect_retry_count = state.get("architect_retry_count", 0) + 1
        task = state["task"].model_copy(
            update={
                "artifact": "revised_implementation_stub",
                "status": TaskStatus.AWAITING_VALIDATION,
            }
        )
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


class FakeDeveloper(BaseAgent):
    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        task = state["task"].model_copy(
            update={
                "artifact": "implementation_stub",
                "status": TaskStatus.AWAITING_VALIDATION,
            }
        )
        return {
            **state,
            "task": task,
            "messages": [*state["messages"], "Developer: implementation complete."],
            "architect_retry_count": state.get("architect_retry_count", 0),
            "worktree_path": state.get("worktree_path", ""),
        }


class FakeApproveAVA(BaseAgent):
    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        task = state["task"].model_copy(
            update={
                "status": TaskStatus.APPROVED,
                "validation_result": ValidationResult(
                    task_id=state["task"].id,
                    decision=ValidationDecision.APPROVE,
                    rationale="All checks passed.",
                    checks=["ci", "docs", "requirements"],
                ),
            }
        )
        return {**state, "task": task, "messages": [*state["messages"], "AVA: approve."]}


class FakeRejectThenApproveAVA(BaseAgent):
    """Rejects on first call, approves on second."""

    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None
        self._call_count = 0

    def run(self, state: GraphState) -> GraphState:
        self._call_count += 1
        task = state["task"]

        if self._call_count == 1:
            updated = task.model_copy(
                update={
                    "status": TaskStatus.REJECTED,
                    "retry_count": state.get("retry_count", 0) + 1,
                    "validation_result": ValidationResult(
                        task_id=task.id,
                        decision=ValidationDecision.REJECT,
                        rationale="First check failed.",
                        checks=["ci"],
                    ),
                }
            )
            return {
                **state,
                "task": updated,
                "retry_count": updated.retry_count,
                "architect_retry_count": state.get("architect_retry_count", 0),
                "messages": [*state["messages"], "AVA: reject."],
                "worktree_path": state.get("worktree_path", ""),
            }

        updated = task.model_copy(
            update={
                "status": TaskStatus.APPROVED,
                "validation_result": ValidationResult(
                    task_id=task.id,
                    decision=ValidationDecision.APPROVE,
                    rationale="All checks passed.",
                    checks=["ci", "docs", "requirements"],
                ),
            }
        )
        return {
            **state,
            "task": updated,
            "messages": [*state["messages"], "AVA: approve."],
            "worktree_path": state.get("worktree_path", ""),
        }


class FakeAlwaysRejectAVA(BaseAgent):
    """Always rejects, causing escalation after max_retries."""

    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        task = state["task"]
        retry_count = state.get("retry_count", 0)
        architect_retry_count = state.get("architect_retry_count", 0)

        if retry_count >= task.max_retries or architect_retry_count >= 2:
            updated = task.model_copy(
                update={
                    "status": TaskStatus.ESCALATED,
                    "validation_result": ValidationResult(
                        task_id=task.id,
                        decision=ValidationDecision.ESCALATE,
                        rationale="Retry limit reached.",
                        checks=[],
                    ),
                }
            )
            return {
                **state,
                "task": updated,
                "messages": [*state["messages"], "AVA: escalate."],
                "worktree_path": state.get("worktree_path", ""),
            }

        new_retry_count = retry_count + 1
        updated = task.model_copy(
            update={
                "status": TaskStatus.REJECTED,
                "retry_count": new_retry_count,
                "validation_result": ValidationResult(
                    task_id=task.id,
                    decision=ValidationDecision.REJECT,
                    rationale="Validation failed.",
                    checks=["ci"],
                ),
            }
        )
        return {
            **state,
            "task": updated,
            "retry_count": new_retry_count,
            "architect_retry_count": architect_retry_count,
            "messages": [*state["messages"], "AVA: reject."],
            "worktree_path": state.get("worktree_path", ""),
        }


class FakeAlwaysEscalateAVA(BaseAgent):
    """Escalates immediately on first call."""

    def __init__(self) -> None:
        self.llm = MagicMock()
        self.system_prompt = ""
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
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
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def task_store() -> InMemoryTaskStore:
    return InMemoryTaskStore()


@pytest.fixture()
def project_store() -> InMemoryProjectStore:
    return InMemoryProjectStore()


@pytest.fixture()
def dispatcher(
    project_store: InMemoryProjectStore, task_store: InMemoryTaskStore
) -> ProjectDispatcher:
    return ProjectDispatcher(project_store, task_store)


@pytest.fixture()
def registered_project(dispatcher: ProjectDispatcher) -> Project:
    project = Project(
        name="Test Project",
        repo_url="https://github.com/test/repo.git",
        local_path=Path("/tmp/test-repo"),
    )
    return dispatcher.register_project(project)


@pytest.fixture()
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.with_structured_output.return_value = MagicMock()
    return llm


def make_task(
    title: str = "Test Task",
    intent: str = "Implement a feature.",
    max_retries: int = 3,
) -> Task:
    return Task(
        title=title,
        intent=intent,
        success_criteria=["Feature passes tests."],
        owner=Role.DEVELOPER,
        max_retries=max_retries,
    )
