from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from opendove.agents.llm_factory import build_llm, build_llm_for_role
from opendove.config import Settings
from opendove.models.task import Role


def test_build_llm_for_role_uses_global_default() -> None:
    """When no role override is set, global provider/model is used."""
    settings = Settings(
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        anthropic_api_key="test-key",
        _env_file=None,
    )

    result = build_llm_for_role(Role.PRODUCT_MANAGER, settings)

    assert isinstance(result, ChatAnthropic)


def test_build_llm_for_role_uses_role_override() -> None:
    """When role override is set, it takes precedence over global default."""
    settings = Settings(
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        developer_llm_provider="openai",
        developer_llm_model="gpt-4o-mini",
        _env_file=None,
    )

    result = build_llm_for_role(Role.DEVELOPER, settings)

    assert isinstance(result, ChatOpenAI)


def test_build_llm_raises_on_unknown_provider() -> None:
    """build_llm raises ValueError for unknown provider."""
    settings = Settings(
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        anthropic_api_key="test-key",
        _env_file=None,
    )

    try:
        build_llm("unknown", "model", settings)
    except ValueError as exc:
        assert "Unsupported LLM provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown provider")


def test_all_roles_resolve() -> None:
    """Every Role enum value resolves without error."""
    settings = Settings(
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        anthropic_api_key="test-key",
        _env_file=None,
    )

    for role in Role:
        result = build_llm_for_role(role, settings)
        assert isinstance(result, ChatAnthropic)
