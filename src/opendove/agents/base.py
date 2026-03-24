from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool


class BaseAgent(ABC):
    def __init__(
        self,
        llm: BaseChatModel,
        system_prompt: str,
        tools: list[BaseTool] | None = None,
    ) -> None:
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools: list[BaseTool] = tools or []
        self._react_agent: Any = None

        if self.tools:
            from langgraph.prebuilt import create_react_agent

            self._react_agent = create_react_agent(self.llm, self.tools)

    def _call_llm(self, user_message: str) -> str:
        """Call the LLM, using a ReAct agent when tools are configured."""
        if self._react_agent is not None:
            result = self._react_agent.invoke(
                {
                    "messages": [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=user_message),
                    ]
                }
            )
            return str(result["messages"][-1].content)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]
        response = self.llm.invoke(messages)
        return str(response.content)

    @abstractmethod
    def run(self, state: Any) -> Any:
        """Process the graph state and return the updated state."""
        raise NotImplementedError
