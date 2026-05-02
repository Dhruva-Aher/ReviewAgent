import json
import logging
from .base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

class SupervisorAgent:
    name = "supervisor"
    
    async def get_relevant_agents(self, context: AgentContext) -> list[str]:
        # Dummy implementation to avoid huge groq calls for now, fall back to all
        return ["security", "architecture", "performance", "test_coverage", "dependency"]
