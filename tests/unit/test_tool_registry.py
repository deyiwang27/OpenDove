from unittest.mock import patch

from langchain_core.tools import tool as lc_tool

from opendove.agents.tool_config import WEB_SEARCH
from opendove.agents.tool_registry import MCPToolRegistry
from opendove.config import Settings
from opendove.models.task import Role


@lc_tool("claude_tool")
def claude_tool() -> str:
    """Fake Claude tool."""
    return "claude"


@lc_tool("fetch_tool")
def fetch_tool() -> str:
    """Fake fetch tool."""
    return "fetch"


def test_get_tools_for_role_returns_empty_when_all_groups_unavailable() -> None:
    settings = Settings(_env_file=None)
    registry = MCPToolRegistry(settings)

    with patch.object(MCPToolRegistry, "_connect_group", side_effect=RuntimeError("offline")):
        tools = registry.get_tools_for_role(Role.DEVELOPER)

    assert tools == []


def test_get_tools_for_role_skips_unavailable_group_gracefully() -> None:
    settings = Settings(_env_file=None)
    registry = MCPToolRegistry(settings)

    def connect_group(_self: MCPToolRegistry, group: str):  # type: ignore[no-untyped-def]
        if group == "codex":
            raise RuntimeError("codex unavailable")
        if group == "claude_code":
            return [claude_tool]
        if group == "web_fetch":
            return [fetch_tool]
        raise AssertionError(f"Unexpected group: {group}")

    with patch.object(MCPToolRegistry, "_connect_group", autospec=True, side_effect=connect_group):
        tools = registry.get_tools_for_role(Role.DEVELOPER)

    assert tools == [claude_tool, fetch_tool]


def test_tool_cache_prevents_reconnect() -> None:
    settings = Settings(_env_file=None)
    registry = MCPToolRegistry(settings)

    def connect_group(_self: MCPToolRegistry, group: str):  # type: ignore[no-untyped-def]
        @lc_tool(f"{group}_tool")
        def group_tool() -> str:
            """Group-specific fake tool."""
            return group

        return [group_tool]

    with patch.object(MCPToolRegistry, "_connect_group", autospec=True, side_effect=connect_group) as mock_connect:
        first_tools = registry.get_tools_for_role(Role.DEVELOPER)
        second_tools = registry.get_tools_for_role(Role.DEVELOPER)

    assert first_tools == second_tools
    assert mock_connect.call_count == 3


def test_web_search_skipped_when_api_key_missing() -> None:
    settings = Settings(brave_search_api_key="", _env_file=None)
    registry = MCPToolRegistry(settings)

    tools = registry._load_group(WEB_SEARCH)

    assert tools == []
