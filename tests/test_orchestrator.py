import pytest
import asyncio
from unittest.mock import patch
from orchestrator import run_multi_agent_review
from agents.base import AgentResult


@pytest.mark.asyncio
async def test_run_multi_agent_review_parallel(sample_context, tmp_db):
    """Agents run concurrently: both must start before either finishes."""
    call_order = []

    class TrackedAgent:
        def __init__(self, name, delay):
            self.name = name
            self.delay = delay

        def relevance_hint(self, context): return True

        async def run(self, context):
            call_order.append(f"{self.name}_start")
            await asyncio.sleep(self.delay)
            call_order.append(f"{self.name}_end")
            return AgentResult(self.name, [], "Done", False)

    a1 = TrackedAgent("SecurityAgent", 0.05)
    a2 = TrackedAgent("ArchitectureAgent", 0.05)

    # Patch the _ALL_AGENTS registry so orchestrator instantiates our tracked agents
    patched_agents = {
        "SecurityAgent": lambda: a1,
        "ArchitectureAgent": lambda: a2,
    }
    with patch("orchestrator._ALL_AGENTS", patched_agents):
        result = await run_multi_agent_review(sample_context, ["SecurityAgent", "ArchitectureAgent"])

        # Both agents must have run
        assert "SecurityAgent_start" in call_order
        assert "ArchitectureAgent_start" in call_order
        assert "SecurityAgent_end" in call_order
        assert "ArchitectureAgent_end" in call_order

        # Result must be a valid review dict
        assert "issues" in result
        assert "summary" in result


@pytest.mark.asyncio
async def test_crashed_agent_does_not_fail_pipeline(sample_context, tmp_db):
    """A crashing agent must not bring down the pipeline."""
    class CrashingAgent:
        name = "SecurityAgent"
        def relevance_hint(self, context): return True
        async def run(self, context):
            raise ValueError("I crashed!")

    with patch("orchestrator._ALL_AGENTS", {"SecurityAgent": CrashingAgent}):
        result = await run_multi_agent_review(sample_context, ["SecurityAgent"])
        assert "issues" in result
        assert "summary" in result


@pytest.mark.asyncio
async def test_agent_runs_table_populated(sample_context, tmp_db):
    """Each agent run must be logged to the agent_runs table."""
    class DummyAgent:
        name = "SecurityAgent"
        def relevance_hint(self, context): return True
        async def run(self, context):
            return AgentResult(self.name, [], "Done", False)

    with patch("orchestrator._ALL_AGENTS", {"SecurityAgent": DummyAgent}), \
         patch("store.log_agent_run") as mock_record:

        await run_multi_agent_review(sample_context, ["SecurityAgent"])
        mock_record.assert_called_once()
