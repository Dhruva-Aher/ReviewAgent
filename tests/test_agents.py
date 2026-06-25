import pytest
from unittest.mock import patch, AsyncMock
from agents.impl import SecurityAgent, ArchitectureAgent, PerformanceAgent, DependencyAgent, synthesize_results
from agents.base import AgentResult


@pytest.mark.asyncio
async def test_relevance_hint(sample_context):
    assert SecurityAgent().relevance_hint(sample_context) is True
    assert ArchitectureAgent().relevance_hint(sample_context) is True
    assert PerformanceAgent().relevance_hint(sample_context) is True
    assert DependencyAgent().relevance_hint(sample_context) is True


@pytest.mark.asyncio
async def test_agent_run_valid_json(sample_context, mock_groq):
    agent = SecurityAgent()
    result = await agent.run(sample_context)
    assert not result.skipped
    assert len(result.issues) == 1
    assert result.issues[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_agent_run_malformed_json(sample_context):
    with patch("agents.impl._call_groq", new_callable=AsyncMock) as mock_call, \
         patch("agents.impl._get_api_key", return_value="test-key"):
        mock_call.return_value = "This is not json"
        agent = SecurityAgent()
        result = await agent.run(sample_context)
        assert result.skipped is True
        assert len(result.issues) == 0


def test_synthesize_single_result():
    """Single agent result passes through without modification."""
    results = [AgentResult("SecurityAgent", [{"message": "only issue"}], "Summary", False)]
    result = synthesize_results(results)
    assert len(result["issues"]) == 1
    assert result["issues"][0]["message"] == "only issue"


def test_synthesize_multiple_results():
    """Multiple agents' issues are merged and deduplicated."""
    results = [
        AgentResult("A1", [{"type": "bug", "severity": "high", "message": "issue 1", "suggestion": "fix 1", "file": "a.py", "line": 10}], "Sum 1", False),
        AgentResult("A2", [{"type": "bug", "severity": "low",  "message": "issue 2", "suggestion": "fix 2", "file": "b.py", "line": 20}], "Sum 2", False),
    ]
    result = synthesize_results(results)
    assert len(result["issues"]) == 2


def test_synthesize_deduplication():
    """Issues referencing the same file+line are deduplicated — keep highest severity."""
    results = [
        AgentResult("A1", [{"type": "bug", "severity": "low",  "message": "thing wrong here", "suggestion": "fix", "file": "a.py", "line": 5}], "Sum 1", False),
        AgentResult("A2", [{"type": "bug", "severity": "high", "message": "thing wrong here", "suggestion": "fix", "file": "a.py", "line": 5}], "Sum 2", False),
    ]
    result = synthesize_results(results)
    assert len(result["issues"]) == 1


def test_synthesize_all_skipped():
    """All skipped agents → empty review."""
    results = [AgentResult("A1", [], "Failed", skipped=True)]
    result = synthesize_results(results)
    assert result["issues"] == []


def test_synthesize_caps_at_five():
    """Never returns more than 5 issues regardless of agent count."""
    many_issues = [
        {"type": "bug", "severity": "low", "message": f"unique issue {i} is different from all others",
         "suggestion": "fix", "file": f"file{i}.py", "line": i * 100}
        for i in range(10)
    ]
    # _deduplicate_issues caps at 5; synthesize_results calls it
    results = [AgentResult("A1", many_issues, "Many issues", False),
               AgentResult("A2", many_issues[:3], "A2 issues", False)]
    result = synthesize_results(results)
    assert len(result["issues"]) <= 5
