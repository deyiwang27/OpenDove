from __future__ import annotations

from opendove.models.task import Role

# Canonical tool group names
CLAUDE_CODE = "claude_code"
CODEX = "codex"
WEB_SEARCH = "web_search"
WEB_FETCH = "web_fetch"

ALL_TOOL_GROUPS = {CLAUDE_CODE, CODEX, WEB_SEARCH, WEB_FETCH}

_ROLE_DEFAULT_TOOLS: dict[Role, frozenset[str]] = {
    Role.PRODUCT_MANAGER: frozenset({CLAUDE_CODE, WEB_SEARCH, WEB_FETCH}),
    Role.PROJECT_MANAGER: frozenset({CLAUDE_CODE, WEB_SEARCH, WEB_FETCH}),
    Role.LEAD_ARCHITECT: frozenset({CLAUDE_CODE, CODEX, WEB_SEARCH, WEB_FETCH}),
    Role.DEVELOPER: frozenset({CLAUDE_CODE, CODEX, WEB_FETCH}),
    Role.AVA: frozenset({CLAUDE_CODE, WEB_FETCH}),
}

_ROLE_TOOL_SETTING: dict[Role, str] = {
    Role.PRODUCT_MANAGER: "product_manager_tools",
    Role.PROJECT_MANAGER: "project_manager_tools",
    Role.LEAD_ARCHITECT: "architect_tools",
    Role.DEVELOPER: "developer_tools",
    Role.AVA: "ava_tools",
}


def get_tool_groups_for_role(role: Role, settings: object) -> frozenset[str]:
    """Return the set of tool group names active for this role."""
    setting_value = str(getattr(settings, _ROLE_TOOL_SETTING[role], ""))
    if not setting_value.strip():
        return _ROLE_DEFAULT_TOOLS[role]
    return frozenset(group.strip() for group in setting_value.split(",") if group.strip())
