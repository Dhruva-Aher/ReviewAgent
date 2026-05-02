import asyncio
import time
import logging
from agents.base import AgentContext
from agents.impl import SecurityAgent, ArchitectureAgent, PerformanceAgent, TestCoverageAgent, DependencyAgent, SynthesisAgent
import store

logger = logging.getLogger(__name__)

async def run_multi_agent_review(context: AgentContext, selected_agents: list[str]) -> dict:
    all_agent_classes = {
        "SecurityAgent": SecurityAgent,
        "ArchitectureAgent": ArchitectureAgent,
        "PerformanceAgent": PerformanceAgent,
        "TestCoverageAgent": TestCoverageAgent,
        "DependencyAgent": DependencyAgent,
    }
    
    agents_to_run = [all_agent_classes[name]() for name in selected_agents if name in all_agent_classes]
    
    async def run_with_timing(agent):
        start_time = time.monotonic()
        try:
            result = await agent.run(context)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            store.log_agent_run(context.repo, context.pr_number, agent.name, duration_ms, result.skipped, len(result.issues))
            return result
        except Exception as e:
            logger.error(f"Agent {agent.name} crashed: {e}")
            duration_ms = int((time.monotonic() - start_time) * 1000)
            store.log_agent_run(context.repo, context.pr_number, agent.name, duration_ms, True, 0)
            from agents.base import AgentResult
            return AgentResult(agent.name, [], f"Crashed: {e}", True, str(e))

    relevant_agents = [a for a in agents_to_run if a.relevance_hint(context)]
    
    # asyncio.gather receives coroutines
    coroutines = [run_with_timing(agent) for agent in relevant_agents]
    
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    
    # Clean up results in case gather actually returned an exception obj
    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            # This shouldn't happen because of try/except in run_with_timing, but just in case
            logger.error(f"Gather returned exception: {r}")
        else:
            clean_results.append(r)
            
    # SynthesisAgent is called after gather completes
    synth = SynthesisAgent()
    final_review = await synth.run(context, clean_results)
    
    return final_review
