from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

if TYPE_CHECKING:
    from opendove.orchestration.graph import GraphState


class BaseAgent(ABC):
    def __init__(self, llm: BaseChatModel, system_prompt: str) -> None:
        self.llm = llm
        self.system_prompt = system_prompt

    def _call_llm(self, user_message: str) -> str:
        """Call the LLM with a system prompt and user message. Returns text content."""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]
        response = self.llm.invoke(messages)
        return str(response.content)

    @abstractmethod
    def run(self, state: GraphState) -> GraphState:
        """Process the graph state and return the updated state."""
        raise NotImplementedError
