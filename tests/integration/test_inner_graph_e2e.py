"""End-to-end tests for the inner LangGraph graph with mocked agents."""
from __future__ import annotations

from unittest.mock import MagicMock


from opendove.agents.base import BaseAgent
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.graph import GraphState, build_graph
from opendove.validation.contracts import ValidationDecision, ValidationResult


# ---------------------------------------------------------------------------
# Fake agent helpers
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
            update={"artifact": "revised_implementation_stub", "status": TaskStatus.AWAITING_VALIDATION}
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
            update={"artifact": "implementation_stub", "status": TaskStatus.AWAITING_VALIDATION}
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
            # First call: reject
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
                "messages": [*state["messages"], "AVA: reject. First check failed."],
                "worktree_path": state.get("worktree_path", ""),
            }

        # Second call: approve
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

        # Check if we've hit the limit
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
                "messages": [*state["messages"], "AVA: escalate. Retry limit reached."],
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
            "messages": [*state["messages"], "AVA: reject. Validation failed."],
            "worktree_path": state.get("worktree_path", ""),
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task(max_retries: int = 3) -> Task:
    return Task(
        title="Test Task",
        intent="Implement a feature.",
        success_criteria=["Feature passes tests."],
        owner=Role.DEVELOPER,
        max_retries=max_retries,
    )


def _initial_state(task: Task) -> GraphState:
    return {
        "task": task,
        "messages": [],
        "retry_count": 0,
        "architect_retry_count": 0,
        "worktree_path": "",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_task_approved() -> None:
    """All agents run in sequence; final task status is APPROVED."""
    task = _make_task()
    graph = build_graph(
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=FakeApproveAVA(),
    )
    result = graph.invoke(_initial_state(task))
    assert result["task"].status == TaskStatus.APPROVED
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision == ValidationDecision.APPROVE


def test_ava_rejection_routes_to_architect_review() -> None:
    """AVA rejects on first call, approves on second; architect_retry_count incremented."""
    task = _make_task(max_retries=3)
    fake_ava = FakeRejectThenApproveAVA()
    graph = build_graph(
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=fake_ava,
    )
    result = graph.invoke(_initial_state(task))

    # AVA was called twice
    assert fake_ava._call_count == 2
    # architect_retry_count was incremented
    assert result["architect_retry_count"] >= 1
    # Final status is APPROVED
    assert result["task"].status == TaskStatus.APPROVED


def test_escalation_after_max_retries() -> None:
    """AVA always rejects; with max_retries=2, final status is ESCALATED."""
    task = _make_task(max_retries=2)
    graph = build_graph(
        product_manager_agent=FakeProductManager(),
        project_manager_agent=FakeProjectManager(),
        lead_architect_agent=FakeLeadArchitect(),
        architect_review_agent=FakeArchitectReview(),
        developer_agent=FakeDeveloper(),
        ava_agent=FakeAlwaysRejectAVA(),
    )
    result = graph.invoke(_initial_state(task))
    assert result["task"].status == TaskStatus.ESCALATED
    assert result["task"].validation_result is not None
    assert result["task"].validation_result.decision == ValidationDecision.ESCALATE


def test_agent_llm_exception_falls_back_gracefully() -> None:
    """Real agents with a mock LLM that raises RuntimeError still complete without exception."""
    from opendove.agents.product_manager import ProductManagerAgent
    from opendove.agents.project_manager import ProjectManagerAgent
    from opendove.agents.lead_architect import LeadArchitectAgent
    from opendove.agents.developer import DeveloperAgent
    from opendove.agents.ava import AVAAgent

    mock_llm = MagicMock()
    # Make with_structured_output raise RuntimeError so _call_llm_structured fails
    mock_llm.with_structured_output.side_effect = RuntimeError("LLM unavailable")
    mock_llm.invoke.side_effect = RuntimeError("LLM unavailable")

    pm_agent = ProductManagerAgent(llm=mock_llm, system_prompt="test")
    proj_manager = ProjectManagerAgent(llm=mock_llm, system_prompt="test")
    architect = LeadArchitectAgent(llm=mock_llm, system_prompt="test")
    developer = DeveloperAgent(llm=mock_llm, system_prompt="test")
    ava = AVAAgent(llm=mock_llm, system_prompt="test")

    task = _make_task(max_retries=3)
    graph = build_graph(
        product_manager_agent=pm_agent,
        project_manager_agent=proj_manager,
        lead_architect_agent=architect,
        developer_agent=developer,
        ava_agent=ava,
    )

    # Should not raise; graph should complete
    result = graph.invoke(_initial_state(task))
    final_status = result["task"].status
    assert final_status in (TaskStatus.APPROVED, TaskStatus.ESCALATED, TaskStatus.REJECTED)
