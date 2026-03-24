from opendove.agents.base import BaseAgent
from opendove.orchestration.graph import GraphState


class LeadArchitectAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT: str = "Define the implementation approach and integration strategy."

    def run(self, state: GraphState) -> GraphState:
        return {
            **state,
            "messages": [*state["messages"], "Architect: approach defined."],
            "worktree_path": state.get("worktree_path", ""),
        }
