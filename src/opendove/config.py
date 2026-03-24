from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPENDOVE_", extra="ignore")

    env: str = "local"
    workspace_dir: Path = Path.home() / ".opendove"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/opendove"

    llm_provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
    llm_model: str = "claude-sonnet-4-6"

    product_manager_llm_provider: str = ""
    product_manager_llm_model: str = ""
    project_manager_llm_provider: str = ""
    project_manager_llm_model: str = ""
    architect_llm_provider: str = ""
    architect_llm_model: str = ""
    developer_llm_provider: str = ""
    developer_llm_model: str = ""
    ava_llm_provider: str = ""
    ava_llm_model: str = ""

    # Per-role tool groups (comma-separated, empty = no tools)
    # Available groups: claude_code, codex, web_search, web_fetch
    product_manager_tools: str = "claude_code,web_search,web_fetch"
    project_manager_tools: str = "claude_code,web_search,web_fetch"
    architect_tools: str = "claude_code,codex,web_search,web_fetch"
    developer_tools: str = "claude_code,codex,web_fetch"
    ava_tools: str = "claude_code,web_fetch"

    # MCP server endpoints (empty = server not available)
    claude_code_mcp_command: str = "claude"
    codex_mcp_command: str = "codex"
    brave_search_api_key: str = ""
    fetch_mcp_command: str = "npx"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""


settings = Settings()
