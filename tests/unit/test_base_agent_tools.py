from typing import Any
from unittest.mock import Mock, patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.tools import tool as lc_tool

from opendove.agents.base import BaseAgent


class DummyAgent(BaseAgent):
    def run(self, state: Any) -> Any:
        return state


@lc_tool("fake_tool")
def fake_tool() -> str:
    """Fake tool for BaseAgent tests."""
    return "ok"


def test_base_agent_no_tools_uses_plain_invoke() -> None:
    agent = DummyAgent(
        llm=FakeListChatModel(responses=["plain response"]),
        system_prompt="system",
    )

    result = agent._call_llm("user")

    assert agent._react_agent is None
    assert result == "plain response"


def test_base_agent_with_tools_builds_react_agent() -> None:
    fake_react_agent = Mock()
    fake_react_agent.invoke.return_value = {"messages": [Mock(content="react response")]}

    with patch("langgraph.prebuilt.create_react_agent", return_value=fake_react_agent) as mock_create:
        agent = DummyAgent(
            llm=FakeListChatModel(responses=["unused"]),
            system_prompt="system",
            tools=[fake_tool],
        )

    result = agent._call_llm("user")

    assert agent._react_agent is fake_react_agent
    assert result == "react response"
    mock_create.assert_called_once()
