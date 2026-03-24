from opendove.agents.tool_config import (
    CLAUDE_CODE,
    CODEX,
    WEB_FETCH,
    WEB_SEARCH,
    get_tool_groups_for_role,
)
from opendove.config import Settings
from opendove.models.task import Role


def test_get_tool_groups_for_role_returns_defaults() -> None:
    settings = Settings(_env_file=None)

    groups = get_tool_groups_for_role(Role.DEVELOPER, settings)

    assert groups == frozenset({CLAUDE_CODE, CODEX, WEB_FETCH})
    assert WEB_SEARCH not in groups


def test_get_tool_groups_for_role_respects_settings_override() -> None:
    settings = Settings(developer_tools="claude_code", _env_file=None)

    groups = get_tool_groups_for_role(Role.DEVELOPER, settings)

    assert groups == frozenset({CLAUDE_CODE})


def test_empty_tools_setting_falls_back_to_defaults() -> None:
    settings = Settings(developer_tools="", _env_file=None)

    groups = get_tool_groups_for_role(Role.DEVELOPER, settings)

    assert groups == frozenset({CLAUDE_CODE, CODEX, WEB_FETCH})


def test_all_roles_have_defaults() -> None:
    settings = Settings(_env_file=None)

    for role in Role:
        groups = get_tool_groups_for_role(role, settings)
        assert groups
