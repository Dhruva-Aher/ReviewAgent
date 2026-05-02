import pytest
from unittest.mock import patch, AsyncMock
from agents.impl import SecurityAgent, ArchitectureAgent, PerformanceAgent, TestCoverageAgent, DependencyAgent, SynthesisAgent
from agents.base import AgentResult

@pytest.mark.asyncio
async def test_relevance_hint(sample_context):
    sec = SecurityAgent()
    assert sec.relevance_hint(sample_context) is True
    
    arch = ArchitectureAgent()
    assert arch.relevance_hint(sample_context) is True
    
    perf = PerformanceAgent()
    assert perf.relevance_hint(sample_context) is True

    dep = DependencyAgent()
    assert dep.relevance_hint(sample_context) is True

@pytest.mark.asyncio
async def test_agent_run_valid_json(sample_context, mock_groq):
    agent = SecurityAgent()
    result = await agent.run(sample_context)
    assert not result.skipped
    assert len(result.issues) == 1
    assert result.issues[0]["severity"] == "high"

@pytest.mark.asyncio
async def test_agent_run_malformed_json(sample_context):
    with patch("reviewer._call_groq", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "This is not json"
        agent = SecurityAgent()
        result = await agent.run(sample_context)
        assert result.skipped is True
        assert len(result.issues) == 0

@pytest.mark.asyncio
async def test_synthesis_single_result(sample_context, mock_groq):
    agent = SynthesisAgent()
    results = [AgentResult("Agent", [{"message": "only issue"}], "Summary", False)]
    result = await agent.run(sample_context, results)
    
    mock_groq.assert_not_called()
    assert len(result["issues"]) == 1
    assert result["issues"][0]["message"] == "only issue"

@pytest.mark.asyncio
async def test_synthesis_multiple_results(sample_context, mock_groq):
    agent = SynthesisAgent()
    results = [
        AgentResult("A1", [{"type": "bug", "severity": "low", "message": "issue 1", "suggestion": "fix 1"}], "Sum 1", False),
        AgentResult("A2", [{"type": "bug", "severity": "low", "message": "issue 2", "suggestion": "fix 2"}], "Sum 2", False)
    ]
    result = await agent.run(sample_context, results)
    
    mock_groq.assert_called_once()
    assert len(result["issues"]) > 0
