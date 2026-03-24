"""Unit tests for LLM retry logic in BaseAgent."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from opendove.agents.base import BaseAgent, LLMCallError, _MAX_RETRIES
from opendove.orchestration.graph import GraphState, build_graph
from opendove.models.task import Role, Task, TaskStatus
from opendove.validation.contracts import ValidationDecision


# ---------------------------------------------------------------------------
# Minimal concrete agent for testing
# ---------------------------------------------------------------------------


class ConcreteAgent(BaseAgent):
    def __init__(self, llm: Any) -> None:
        self.llm = llm
        self.system_prompt = "You are a test agent."
        self.tools = []
        self._react_agent = None

    def run(self, state: GraphState) -> GraphState:
        return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_retryable_error() -> Exception:
    """Return an Anthropic RateLimitError if available, else a plain RuntimeError subclass."""
    try:
        from anthropic import RateLimitError
        response = MagicMock()
        response.status_code = 429
        return RateLimitError("rate limited", response=response, body={})
    except (ImportError, TypeError):
        pass
    try:
        from anthropic import APIConnectionError
        return APIConnectionError(request=MagicMock())
    except (ImportError, TypeError):
        pass
    # Fallback: patch _RETRYABLE_EXCEPTIONS directly in the test
    return RuntimeError("synthetic transient error")


# ---------------------------------------------------------------------------
# _call_with_retry tests
# ---------------------------------------------------------------------------


def test_call_with_retry_succeeds_on_first_attempt() -> None:
    llm = MagicMock()
    agent = ConcreteAgent(llm)

    result = agent._call_with_retry(lambda: "ok")
    assert result == "ok"


def test_call_with_retry_returns_after_transient_failures() -> None:
    """Succeeds on the third attempt after two transient failures."""
    llm = MagicMock()
    agent = ConcreteAgent(llm)

    err = _make_retryable_error()
    call_count = 0

    def _flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise err
        return "recovered"

    with patch("opendove.agents.base._RETRYABLE_EXCEPTIONS", (type(err),)), \
         patch("opendove.agents.base.time.sleep"):
        result = agent._call_with_retry(_flaky, label="test call")

    assert result == "recovered"
    assert call_count == 3


def test_call_with_retry_raises_llm_call_error_after_max_retries() -> None:
    """Exhausts all retries and raises LLMCallError."""
    llm = MagicMock()
    agent = ConcreteAgent(llm)

    err = _make_retryable_error()

    def _always_fail():
        raise err

    with patch("opendove.agents.base._RETRYABLE_EXCEPTIONS", (type(err),)), \
         patch("opendove.agents.base.time.sleep"):
        with pytest.raises(LLMCallError):
            agent._call_with_retry(_always_fail, label="always fails")


def test_call_with_retry_does_not_retry_non_transient_errors() -> None:
    """Non-retryable errors propagate immediately without retrying."""
    llm = MagicMock()
    agent = ConcreteAgent(llm)

    call_count = 0

    def _value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("permanent error")

    with patch("opendove.agents.base._RETRYABLE_EXCEPTIONS", ()):
        with pytest.raises(ValueError, match="permanent error"):
            agent._call_with_retry(_value_error)

    assert call_count == 1


def test_call_with_retry_attempt_count_matches_max_retries() -> None:
    """The callable is invoked exactly _MAX_RETRIES times before giving up."""
    llm = MagicMock()
    agent = ConcreteAgent(llm)

    err = _make_retryable_error()
    call_count = 0

    def _always_fail():
        nonlocal call_count
        call_count += 1
        raise err

    with patch("opendove.agents.base._RETRYABLE_EXCEPTIONS", (type(err),)), \
         patch("opendove.agents.base.time.sleep"):
        with pytest.raises(LLMCallError):
            agent._call_with_retry(_always_fail)

    assert call_count == _MAX_RETRIES


# ---------------------------------------------------------------------------
# _call_llm_structured fallback tests
# ---------------------------------------------------------------------------


class StructuredResponse(BaseModel):
    answer: str
    score: int


def test_call_llm_structured_falls_back_on_bad_request() -> None:
    """When with_structured_output raises BadRequestError, falls back to plain JSON call."""
    llm = MagicMock()
    llm.with_structured_output.side_effect = Exception(
        "400 - This response_format type is unavailable now"
    )
    llm.invoke.return_value = MagicMock(content='{"answer":"fallback","score":7}')

    agent = ConcreteAgent(llm)

    result = agent._call_llm_structured("Return the result.", StructuredResponse)

    assert result == StructuredResponse(answer="fallback", score=7)
    assert llm.with_structured_output.call_count == 1
    llm.invoke.assert_called_once()
    messages = llm.invoke.call_args.args[0]
    assert messages[0].content == agent.system_prompt
    assert "Return the result." in messages[1].content
    assert "Respond with a valid JSON object only." in messages[1].content
    assert "answer: str" in messages[1].content
    assert "score: int" in messages[1].content


def test_call_llm_structured_fallback_strips_markdown_fences() -> None:
    """Fallback correctly strips ```json ... ``` fences before parsing."""
    llm = MagicMock()
    llm.with_structured_output.side_effect = Exception(
        "400 - This response_format type is unavailable now"
    )
    llm.invoke.return_value = MagicMock(
        content='```json\n{"answer":"react fallback","score":3}\n```'
    )

    agent = ConcreteAgent(llm)
    agent._react_agent = MagicMock()
    agent._react_agent.invoke.return_value = {
        "messages": [MagicMock(content="Tool output summary")]
    }

    result = agent._call_llm_structured("Use tools first.", StructuredResponse)

    assert result == StructuredResponse(answer="react fallback", score=3)
    assert llm.with_structured_output.call_count == 1
    llm.invoke.assert_called_once()
    messages = llm.invoke.call_args.args[0]
    assert messages[0].content == "Convert the following text into the required JSON structure."
    assert "Tool output summary" in messages[1].content
    assert "Respond with a valid JSON object only." in messages[1].content


# ---------------------------------------------------------------------------
# Graph escalation on LLMCallError
# ---------------------------------------------------------------------------


def _make_task() -> Task:
    return Task(
        title="Retry Test",
        intent="Test LLM retry escalation.",
        success_criteria=["Task escalates on LLM failure."],
        owner=Role.DEVELOPER,
    )


class _LLMFailProductManager(MagicMock):
    """Fake agent whose run() raises LLMCallError."""
    def run(self, state: GraphState) -> GraphState:
        raise LLMCallError("LLM exhausted for product_manager_node")


def test_graph_escalates_task_on_llm_call_error() -> None:
    """When a node raises LLMCallError, the graph escalates the task and ends cleanly."""
    graph = build_graph(product_manager_agent=_LLMFailProductManager())

    initial: GraphState = {
        "task": _make_task(),
        "messages": [],
        "retry_count": 0,
        "architect_retry_count": 0,
        "worktree_path": "",
    }

    result = graph.invoke(initial)
    final_task: Task = result["task"]

    assert final_task.status is TaskStatus.ESCALATED
    assert final_task.validation_result is not None
    assert final_task.validation_result.decision is ValidationDecision.ESCALATE
    assert "LLM call failed" in final_task.validation_result.rationale
    assert any("escalated" in msg for msg in result["messages"])
