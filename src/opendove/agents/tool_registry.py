from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future
from collections.abc import Coroutine
from threading import Thread
from typing import Any

from langchain_core.tools import BaseTool

from opendove.agents.tool_config import (
    CLAUDE_CODE,
    CODEX,
    WEB_FETCH,
    WEB_SEARCH,
    get_tool_groups_for_role,
)
from opendove.config import Settings
from opendove.models.task import Role

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Loads MCP tools for each role. Tool groups not configured are skipped."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tool_cache: dict[str, list[BaseTool]] = {}

    def get_tools_for_role(self, role: Role) -> list[BaseTool]:
        """Return LangChain tools for the given role."""
        groups = get_tool_groups_for_role(role, self._settings)
        tools: list[BaseTool] = []
        for group in sorted(groups):
            tools.extend(self._load_group(group))
        return tools

    def _load_group(self, group: str) -> list[BaseTool]:
        if group in self._tool_cache:
            return self._tool_cache[group]

        loaded: list[BaseTool] = []
        try:
            loaded = self._connect_group(group)
        except Exception as exc:  # pragma: no cover - exercised through public behavior
            logger.warning("MCP tool group %r unavailable: %s", group, exc)

        self._tool_cache[group] = loaded
        return loaded

    def _connect_group(self, group: str) -> list[BaseTool]:
        """Connect to the MCP server for a tool group and return its tools."""
        if group == CLAUDE_CODE:
            return self._load_stdio_mcp(
                name="claude_code",
                command=self._settings.claude_code_mcp_command,
                args=["mcp", "serve"],
            )
        if group == CODEX:
            return self._load_stdio_mcp(
                name="codex",
                command=self._settings.codex_mcp_command,
                args=["--approval-policy", "on-failure"],
            )
        if group == WEB_SEARCH:
            if not self._settings.brave_search_api_key:
                logger.warning("MCP tool group 'web_search' skipped: BRAVE_SEARCH_API_KEY not set")
                return []
            return self._load_stdio_mcp(
                name="brave_search",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-brave-search"],
                env={"BRAVE_API_KEY": self._settings.brave_search_api_key},
            )
        if group == WEB_FETCH:
            return self._load_stdio_mcp(
                name="fetch",
                command=self._settings.fetch_mcp_command,
                args=["-y", "@modelcontextprotocol/server-fetch"],
            )

        logger.warning("Unknown tool group: %r", group)
        return []

    def _load_stdio_mcp(
        self,
        name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> list[BaseTool]:
        """Load tools from a stdio MCP server using langchain_mcp_adapters."""
        if not command:
            logger.warning("MCP tool group %r skipped: command not configured", name)
            return []

        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[import]

        server_config: dict[str, object] = {
            "command": command,
            "args": args,
            "transport": "stdio",
        }
        if env:
            server_config["env"] = env

        async def _get_tools() -> list[BaseTool]:
            async with MultiServerMCPClient({name: server_config}) as client:
                return await client.get_tools()

        return _run_coroutine(_get_tools())


def _run_coroutine(coro: Coroutine[Any, Any, list[BaseTool]]) -> list[BaseTool]:
    """Run an async MCP client call from sync code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    future: Future[list[BaseTool]] = Future()

    def _runner() -> None:
        try:
            result = asyncio.run(coro)
        except Exception as exc:
            future.set_exception(exc)
        else:
            future.set_result(result)

    thread = Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    return future.result()
