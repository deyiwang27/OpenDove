from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Transient errors that warrant a retry
_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = ()

try:
    from anthropic import APIConnectionError as AnthropicConnectionError
    from anthropic import APITimeoutError as AnthropicTimeoutError
    from anthropic import RateLimitError as AnthropicRateLimitError

    _RETRYABLE_EXCEPTIONS += (
        AnthropicRateLimitError,
        AnthropicTimeoutError,
        AnthropicConnectionError,
    )
except ImportError:
    pass

try:
    from openai import APIConnectionError as OpenAIConnectionError
    from openai import APITimeoutError as OpenAITimeoutError
    from openai import RateLimitError as OpenAIRateLimitError

    _RETRYABLE_EXCEPTIONS += (
        OpenAIRateLimitError,
        OpenAITimeoutError,
        OpenAIConnectionError,
    )
except ImportError:
    pass


class LLMCallError(RuntimeError):
    """Raised when an LLM call fails after all retry attempts are exhausted."""


_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


def _backoff(attempt: int) -> float:
    """Exponential backoff with full jitter: sleep in [0, base * 2^attempt]."""
    return random.uniform(0, _BASE_DELAY * (2**attempt))  # noqa: S311


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

    def _call_with_retry(self, fn: Callable[[], T], label: str = "LLM call") -> T:
        """Execute *fn* with exponential-backoff retry on transient LLM errors.

        Retries up to _MAX_RETRIES times on known transient exceptions.
        Raises LLMCallError if all attempts are exhausted.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return fn()
            except _RETRYABLE_EXCEPTIONS as exc:  # type: ignore[misc]
                last_exc = exc
                delay = _backoff(attempt)
                logger.warning(
                    "%s failed (attempt %d/%d), retrying in %.1fs: %s",
                    label,
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                    exc,
                )
                time.sleep(delay)
            except Exception:
                raise
        raise LLMCallError(
            f"{label} failed after {_MAX_RETRIES} attempts"
        ) from last_exc

    def _call_llm(self, user_message: str) -> str:
        """Call the LLM, using a ReAct agent when tools are configured."""
        if self._react_agent is not None:
            def _invoke() -> str:
                result = self._react_agent.invoke(
                    {
                        "messages": [
                            SystemMessage(content=self.system_prompt),
                            HumanMessage(content=user_message),
                        ]
                    }
                )
                return str(result["messages"][-1].content)

            return self._call_with_retry(_invoke, label="ReAct LLM call")

        def _invoke_plain() -> str:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_message),
            ]
            response = self.llm.invoke(messages)
            return str(response.content)

        return self._call_with_retry(_invoke_plain, label="LLM call")

    def _call_llm_structured(self, user_message: str, schema: type[T]) -> T:
        """Call the LLM and return a validated Pydantic object.

        Uses `llm.with_structured_output` when no tools are configured,
        falling back to a two-step call for ReAct agents.
        Raises `ValueError` if the response cannot be validated.
        Raises `LLMCallError` if retries are exhausted on a transient error.
        """
        if self._react_agent is not None:
            raw = self._call_llm(user_message)
            structured_llm = self.llm.with_structured_output(schema)

            def _structure() -> T:
                return structured_llm.invoke(  # type: ignore[return-value]
                    [
                        SystemMessage(content="Convert the following text into the required JSON structure."),
                        HumanMessage(content=raw),
                    ]
                )

            return self._call_with_retry(_structure, label="structured LLM call")

        structured_llm = self.llm.with_structured_output(schema)
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

        def _invoke_structured() -> T:
            result = structured_llm.invoke(messages)
            if not isinstance(result, schema):
                raise ValueError(f"LLM returned unexpected type: {type(result)}")
            return result  # type: ignore[return-value]

        return self._call_with_retry(_invoke_structured, label="structured LLM call")

    @abstractmethod
    def run(self, state: Any) -> Any:
        """Process the graph state and return the updated state."""
        raise NotImplementedError
