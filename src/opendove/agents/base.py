from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


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

    def _call_llm_structured(self, user_message: str, schema: type[T]) -> T:
        """Call the LLM and return a validated Pydantic object.

        Uses `llm.with_structured_output` when no tools are configured,
        falling back to a two-step call for ReAct agents.
        Raises `ValueError` if the response cannot be validated.
        """
        if self._react_agent is not None:
            # ReAct path: get plain text, then ask the base LLM to structure it.
            raw = self._call_llm(user_message)
            structured_llm = self.llm.with_structured_output(schema)
            return structured_llm.invoke(  # type: ignore[return-value]
                [
                    SystemMessage(content="Convert the following text into the required JSON structure."),
                    HumanMessage(content=raw),
                ]
            )

        structured_llm = self.llm.with_structured_output(schema)
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]
        result = structured_llm.invoke(messages)
        if not isinstance(result, schema):
            raise ValueError(f"LLM returned unexpected type: {type(result)}")
        return result  # type: ignore[return-value]

    @abstractmethod
    def run(self, state: Any) -> Any:
        """Process the graph state and return the updated state."""
        raise NotImplementedError
