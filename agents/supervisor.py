import logging
from .base import AgentContext

logger = logging.getLogger(__name__)

class SupervisorAgent:
    name = "supervisor"

    async def get_relevant_agents(self, context: AgentContext) -> list[str]:
        # Dummy implementation to avoid huge groq calls for now, fall back to all
        return ["security", "architecture", "performance", "test_coverage", "dependency"]
