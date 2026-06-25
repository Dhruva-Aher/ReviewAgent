import asyncio
import time
import logging
from agents.base import AgentContext, AgentResult
from agents.impl import (
    SecurityAgent, ArchitectureAgent, PerformanceAgent,
    TestCoverageAgent, DependencyAgent, synthesize_results,
)
import store

logger = logging.getLogger(__name__)

_ALL_AGENTS = {
    "SecurityAgent": SecurityAgent,
    "ArchitectureAgent": ArchitectureAgent,
    "PerformanceAgent": PerformanceAgent,
    "TestCoverageAgent": TestCoverageAgent,
    "DependencyAgent": DependencyAgent,
}


async def run_multi_agent_review(context: AgentContext, selected_agents: list[str]) -> dict:
    agents = [_ALL_AGENTS[name]() for name in selected_agents if name in _ALL_AGENTS]
    relevant = [a for a in agents if a.relevance_hint(context)]

    async def run_timed(agent) -> AgentResult:
        start = time.monotonic()
        try:
            result = await agent.run(context)
        except Exception as e:
            logger.error(f"Agent {agent.name} crashed: {e}")
            result = AgentResult(agent.name, [], f"Crashed: {e}", skipped=True, skip_reason=str(e))
        duration_ms = int((time.monotonic() - start) * 1000)
        store.log_agent_run(context.repo, context.pr_number, agent.name, duration_ms, result.skipped, len(result.issues))
        return result

    results = await asyncio.gather(*[run_timed(a) for a in relevant])
    return synthesize_results(list(results))
