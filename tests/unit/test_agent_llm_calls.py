"""Tests verifying that each agent calls _call_llm_structured and parses output."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from opendove.agents.developer import DeveloperAgent
from opendove.agents.lead_architect import LeadArchitectAgent
from opendove.agents.product_manager import ProductManagerAgent
from opendove.agents.project_manager import ProjectManagerAgent
from opendove.agents.schemas import (
    ArchitectReviewOutput,
    DeveloperOutput,
    LeadArchitectOutput,
    ProductManagerOutput,
    ProjectManagerOutput,
)
from opendove.models.task import Role, Task, TaskStatus
from opendove.orchestration.graph import GraphState
from opendove.validation.contracts import ValidationDecision, ValidationResult


def _make_task(**kwargs) -> Task:
    defaults = dict(
        title="Add health endpoint",
        intent="Add GET /health that returns 200 OK",
        success_criteria=["GET /health returns 200", "response body contains status: ok"],
        owner=Role.DEVELOPER,
    )
    defaults.update(kwargs)
    return Task(**defaults)


def _make_state(task: Task, **kwargs) -> GraphState:
    return GraphState(
        task=task,
        messages=[],
        retry_count=0,
        architect_retry_count=kwargs.get("architect_retry_count", 0),
        worktree_path=kwargs.get("worktree_path", "/tmp/worktree"),
    )


def _fake_llm():
    return MagicMock()


# ---------------------------------------------------------------------------
# ProductManagerAgent
# ---------------------------------------------------------------------------

class TestProductManagerAgent:
    def test_calls_llm_structured_and_updates_criteria(self):
        agent = ProductManagerAgent(llm=_fake_llm(), system_prompt="x")
        expected = ProductManagerOutput(
            success_criteria=["GET /health returns HTTP 200", "body contains {'status': 'ok'}"],
            scope_note="Does not include authentication or rate limiting.",
        )
        with patch.object(agent, "_call_llm_structured", return_value=expected) as mock_call:
            state = _make_state(_make_task())
            result = agent.run(state)

        mock_call.assert_called_once()
        assert result["task"].success_criteria == expected.success_criteria
        assert result["task"].status == TaskStatus.IN_PROGRESS
        assert "Out of scope" in result["messages"][-1]

    def test_falls_back_gracefully_on_llm_failure(self):
        agent = ProductManagerAgent(llm=_fake_llm(), system_prompt="x")
        with patch.object(agent, "_call_llm_structured", side_effect=RuntimeError("timeout")):
            state = _make_state(_make_task())
            result = agent.run(state)

        # Original criteria preserved, no crash
        assert result["task"].success_criteria == state["task"].success_criteria
        assert result["task"].status == TaskStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# ProjectManagerAgent
# ---------------------------------------------------------------------------

class TestProjectManagerAgent:
    def test_calls_llm_structured_and_updates_owner_and_retries(self):
        agent = ProjectManagerAgent(llm=_fake_llm(), system_prompt="x")
        expected = ProjectManagerOutput(
            owner="developer",
            max_retries=3,
            readiness_note="Task is well-specified and ready.",
        )
        with patch.object(agent, "_call_llm_structured", return_value=expected) as mock_call:
            state = _make_state(_make_task())
            result = agent.run(state)

        mock_call.assert_called_once()
        assert result["task"].owner == Role.DEVELOPER
        assert result["task"].max_retries == 3
        assert "ready" in result["messages"][-1].lower()

    def test_includes_github_issue_number_in_message(self):
        agent = ProjectManagerAgent(llm=_fake_llm(), system_prompt="x")
        expected = ProjectManagerOutput(owner="developer", max_retries=3, readiness_note="ok")
        with patch.object(agent, "_call_llm_structured", return_value=expected):
            state = _make_state(_make_task(github_issue_number=42))
            result = agent.run(state)

        assert "issue #42" in result["messages"][-1]

    def test_falls_back_on_llm_failure(self):
        agent = ProjectManagerAgent(llm=_fake_llm(), system_prompt="x")
        with patch.object(agent, "_call_llm_structured", side_effect=ValueError("bad")):
            task = _make_task(max_retries=2)
            result = agent.run(_make_state(task))

        assert result["task"].max_retries == 2  # original preserved


# ---------------------------------------------------------------------------
# LeadArchitectAgent — initial planning
# ---------------------------------------------------------------------------

class TestLeadArchitectAgent:
    def test_calls_llm_structured_and_updates_risk_level(self):
        agent = LeadArchitectAgent(llm=_fake_llm(), system_prompt="x")
        expected = LeadArchitectOutput(
            technical_approach="1. Add route in app.py\n2. Return JSON",
            risk_level="low",
            affected_files=["src/app.py", "tests/unit/test_app.py"],
        )
        with patch.object(agent, "_call_llm_structured", return_value=expected) as mock_call:
            state = _make_state(_make_task())
            result = agent.run(state)

        mock_call.assert_called_once()
        assert result["task"].risk_level == "low"
        assert "risk=low" in result["messages"][-1]
        assert "src/app.py" in result["messages"][-1]

    def test_architect_review_mode_when_retry_count_positive(self):
        agent = LeadArchitectAgent(llm=_fake_llm(), system_prompt="x")
        validation = ValidationResult(
            task_id=uuid4(),
            decision=ValidationDecision.REJECT,
            rationale="CI failed: missing test coverage",
            checks=["ci", "docs"],
        )
        task = _make_task(validation_result=validation)
        expected = ArchitectReviewOutput(
            revised_approach="Add tests for the new endpoint in tests/unit/test_health.py",
            root_cause="Developer did not add unit tests.",
        )
        with patch.object(agent, "_call_llm_structured", return_value=expected) as mock_call:
            state = _make_state(task, architect_retry_count=1)
            result = agent.run(state)

        mock_call.assert_called_once()
        assert result["architect_retry_count"] == 2
        assert "Root cause" in result["messages"][-1]
        assert result["task"].artifact == expected.revised_approach

    def test_falls_back_on_llm_failure(self):
        agent = LeadArchitectAgent(llm=_fake_llm(), system_prompt="x")
        with patch.object(agent, "_call_llm_structured", side_effect=RuntimeError("oops")):
            state = _make_state(_make_task())
            result = agent.run(state)

        # No crash; task unchanged
        assert result["task"].title == "Add health endpoint"


# ---------------------------------------------------------------------------
# DeveloperAgent
# ---------------------------------------------------------------------------

class TestDeveloperAgent:
    def test_calls_llm_structured_and_sets_artifact(self):
        agent = DeveloperAgent(llm=_fake_llm(), system_prompt="x")
        expected = DeveloperOutput(
            artifact="Added GET /health in src/app.py. Tests in tests/unit/test_health.py.",
            files_changed=["src/app.py", "tests/unit/test_health.py"],
        )
        with patch.object(agent, "_call_llm_structured", return_value=expected) as mock_call:
            state = _make_state(_make_task())
            result = agent.run(state)

        mock_call.assert_called_once()
        assert result["task"].artifact == expected.artifact
        assert result["task"].status == TaskStatus.AWAITING_VALIDATION
        assert "src/app.py" in result["messages"][-1]

    def test_falls_back_to_stub_on_llm_failure(self):
        agent = DeveloperAgent(llm=_fake_llm(), system_prompt="x")
        with patch.object(agent, "_call_llm_structured", side_effect=ConnectionError("offline")):
            state = _make_state(_make_task())
            result = agent.run(state)

        assert result["task"].artifact == "implementation_stub"
        assert result["task"].status == TaskStatus.AWAITING_VALIDATION


# ---------------------------------------------------------------------------
# Structured output schema validation
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_product_manager_output_rejects_empty_criteria(self):
        with pytest.raises(Exception):
            ProductManagerOutput(success_criteria=[], scope_note="x")

    def test_project_manager_output_rejects_zero_retries(self):
        with pytest.raises(Exception):
            ProjectManagerOutput(owner="developer", max_retries=0, readiness_note="x")

    def test_project_manager_output_rejects_too_many_retries(self):
        with pytest.raises(Exception):
            ProjectManagerOutput(owner="developer", max_retries=6, readiness_note="x")

    def test_lead_architect_output_accepts_valid_risk_levels(self):
        out = LeadArchitectOutput(technical_approach="do stuff", risk_level="low")
        assert out.risk_level == "low"
        out2 = LeadArchitectOutput(technical_approach="big change", risk_level="architectural")
        assert out2.risk_level == "architectural"
