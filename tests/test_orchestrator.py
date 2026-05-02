import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from orchestrator import run_multi_agent_review

@pytest.mark.asyncio
async def test_run_multi_agent_review_parallel(sample_context, tmp_db):
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
            from agents.base import AgentResult
            return AgentResult(self.name, [], "Done", False)

    a1 = TrackedAgent("SecurityAgent", 0.1)
    a2 = TrackedAgent("ArchitectureAgent", 0.1)
    
    with patch("orchestrator.SecurityAgent", return_value=a1), \
         patch("orchestrator.ArchitectureAgent", return_value=a2), \
         patch("orchestrator.SynthesisAgent") as MockSynth:
         
        synth_instance = MockSynth.return_value
        synth_instance.run = AsyncMock(return_value={"issues": [], "summary": "Final"})
        
        await run_multi_agent_review(sample_context, ["SecurityAgent", "ArchitectureAgent"])
        
        # Verify parallelism: all starts must happen before any ends
        assert "SecurityAgent_start" in call_order[:2]
        assert "ArchitectureAgent_start" in call_order[:2]
        assert "SecurityAgent_end" in call_order[2:]
        assert "ArchitectureAgent_end" in call_order[2:]
        
        # Verify SynthesisAgent was called after
        synth_instance.run.assert_called_once()

@pytest.mark.asyncio
async def test_crashed_agent_does_not_fail_pipeline(sample_context, tmp_db):
    class CrashingAgent:
        name = "SecurityAgent"
        def relevance_hint(self, diff): return True
        async def run(self, context):
            raise ValueError("I crashed!")
            
    with patch("orchestrator.SecurityAgent", return_value=CrashingAgent()), \
         patch("orchestrator.SynthesisAgent") as MockSynth:
         
        synth_instance = MockSynth.return_value
        synth_instance.run = AsyncMock(return_value={"issues": [], "summary": "Final"})
        
        # Should not raise
        result = await run_multi_agent_review(sample_context, ["SecurityAgent"])
        assert result["summary"] == "Final"

@pytest.mark.asyncio
async def test_agent_runs_table_populated(sample_context, tmp_db):
    class DummyAgent:
        name = "SecurityAgent"
        def relevance_hint(self, diff): return True
        async def run(self, context):
            from agents.base import AgentResult
            return AgentResult(self.name, [], "Done", False)
            
    with patch("orchestrator.SecurityAgent", return_value=DummyAgent()), \
         patch("orchestrator.SynthesisAgent") as MockSynth, \
         patch("store.log_agent_run") as mock_record:
         
        synth_instance = MockSynth.return_value
        synth_instance.run = AsyncMock(return_value={"issues": [], "summary": "Final"})
        
        await run_multi_agent_review(sample_context, ["SecurityAgent"])
        mock_record.assert_called_once()
