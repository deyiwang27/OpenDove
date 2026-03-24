from __future__ import annotations

from opendove.agents.ava import AVAAgent
from opendove.agents.base import BaseAgent
from opendove.agents.developer import DeveloperAgent
from opendove.agents.lead_architect import LeadArchitectAgent
from opendove.agents.llm_factory import build_llm_for_role
from opendove.agents.product_manager import ProductManagerAgent
from opendove.agents.project_manager import ProjectManagerAgent
from opendove.config import Settings
from opendove.models.task import Role


def build_all_agents(settings: Settings) -> dict[str, BaseAgent]:
    """Instantiate all active role agents using per-role LLM config."""
    return {
        "product_manager_agent": ProductManagerAgent(
            llm=build_llm_for_role(Role.PRODUCT_MANAGER, settings),
            system_prompt=ProductManagerAgent.DEFAULT_SYSTEM_PROMPT,
        ),
        "project_manager_agent": ProjectManagerAgent(
            llm=build_llm_for_role(Role.PROJECT_MANAGER, settings),
            system_prompt=ProjectManagerAgent.DEFAULT_SYSTEM_PROMPT,
        ),
        "lead_architect_agent": LeadArchitectAgent(
            llm=build_llm_for_role(Role.LEAD_ARCHITECT, settings),
            system_prompt=LeadArchitectAgent.DEFAULT_SYSTEM_PROMPT,
        ),
        "developer_agent": DeveloperAgent(
            llm=build_llm_for_role(Role.DEVELOPER, settings),
            system_prompt=DeveloperAgent.DEFAULT_SYSTEM_PROMPT,
        ),
        "ava_agent": AVAAgent(
            llm=build_llm_for_role(Role.AVA, settings),
            system_prompt=AVAAgent.DEFAULT_SYSTEM_PROMPT,
        ),
    }
