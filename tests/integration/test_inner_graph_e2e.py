"""End-to-end tests for the inner LangGraph graph with mocked agents."""
from __future__ import annotations

from unittest.mock import MagicMock

from opendove.models.task import TaskStatus
from opendove.orchestration.graph import build_graph
from opendove.validation.contracts import ValidationDecision

from tests.integration.conftest import (
    FakeAlwaysRejectAVA,
    FakeApproveAVA,
    FakeArchitectReview,
    FakeDeveloper,
    FakeLeadArchitect,
    FakeProductManager,
    FakeProjectManager,
    FakeRejectThenApproveAVA,
    make_task,
)


def _initial_state(task):
    return {
        "task": task,
        "messages": [],
        "retry_count": 0,
        "architect_retry_count": 0,
        "worktree_path": "",
    }


def test_happy_path_task_approved() -> None:
    """All agents run in sequence; final task status is APPROVED."""
    task = make_task()
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
    task = make_task(max_retries=3)
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

    assert fake_ava._call_count == 2
    assert result["architect_retry_count"] >= 1
    assert result["task"].status == TaskStatus.APPROVED


def test_escalation_after_max_retries() -> None:
    """AVA always rejects; with max_retries=2, final status is ESCALATED."""
    task = make_task(max_retries=2)
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
    assert result["task"].validation_result.decision == ValidationDecision.ESCALATE


def test_agent_llm_exception_falls_back_gracefully() -> None:
    """Real agents with a mock LLM that raises RuntimeError still complete without crashing."""
    from opendove.agents.ava import AVAAgent
    from opendove.agents.developer import DeveloperAgent
    from opendove.agents.lead_architect import LeadArchitectAgent
    from opendove.agents.product_manager import ProductManagerAgent
    from opendove.agents.project_manager import ProjectManagerAgent

    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = RuntimeError("LLM unavailable")
    mock_llm.invoke.side_effect = RuntimeError("LLM unavailable")

    graph = build_graph(
        product_manager_agent=ProductManagerAgent(llm=mock_llm, system_prompt="test"),
        project_manager_agent=ProjectManagerAgent(llm=mock_llm, system_prompt="test"),
        lead_architect_agent=LeadArchitectAgent(llm=mock_llm, system_prompt="test"),
        developer_agent=DeveloperAgent(llm=mock_llm, system_prompt="test"),
        ava_agent=AVAAgent(llm=mock_llm, system_prompt="test"),
    )

    result = graph.invoke(_initial_state(make_task(max_retries=3)))
    assert result["task"].status in (
        TaskStatus.APPROVED,
        TaskStatus.ESCALATED,
        TaskStatus.REJECTED,
    )
