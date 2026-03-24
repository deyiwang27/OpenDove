from langchain_core.language_models import BaseChatModel

from opendove.config import Settings
from opendove.models.task import Role


def build_llm(provider: str, model: str, settings: Settings) -> BaseChatModel:
    """Instantiate a BaseChatModel for the given provider and model."""
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=settings.anthropic_api_key or None)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=settings.openai_api_key or None)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=settings.gemini_api_key or None)
    if provider == "deepseek":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.deepseek_api_key or None,
            base_url="https://api.deepseek.com/v1",
        )
    raise ValueError(f"Unsupported LLM provider: {provider!r}")


_ROLE_PROVIDER_FIELD = {
    Role.PRODUCT_MANAGER: ("product_manager_llm_provider", "product_manager_llm_model"),
    Role.PROJECT_MANAGER: ("project_manager_llm_provider", "project_manager_llm_model"),
    Role.LEAD_ARCHITECT: ("architect_llm_provider", "architect_llm_model"),
    Role.DEVELOPER: ("developer_llm_provider", "developer_llm_model"),
    Role.AVA: ("ava_llm_provider", "ava_llm_model"),
}


def build_llm_for_role(role: Role, settings: Settings) -> BaseChatModel:
    """Resolve provider/model for a role (role-specific override > global default)."""
    provider_field, model_field = _ROLE_PROVIDER_FIELD[role]
    provider = getattr(settings, provider_field) or settings.llm_provider
    model = getattr(settings, model_field) or settings.llm_model
    return build_llm(provider, model, settings)
