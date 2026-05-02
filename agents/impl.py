import json
import logging
from typing import List
from agents.base import BaseAgent, AgentContext, AgentResult
from reviewer import _call_groq, _clean_json, _validate, _get_api_key, FALLBACK_REVIEW

logger = logging.getLogger(__name__)

async def _agent_run_impl(agent_name: str, focus: str, context: AgentContext) -> AgentResult:
    prompt = f"""You are the {agent_name}. Focus your review STRICTLY on: {focus}.
REPO: {context.repo}
PR: #{context.pr_number}

--- BELIEF SYSTEM ---
{context.beliefs_text}

--- DIFF ---
{context.diff[:80000]}"""

    messages = [
        {"role": "system", "content": "Return ONLY valid JSON. Schema: {'issues': [{'type': 'bug', 'severity': 'high', 'message': '...', 'suggestion': '...', 'reference': null, 'confidence': 85, 'file': '...', 'line': 123}], 'summary': '...'}"},
        {"role": "user", "content": prompt},
    ]

    try:
        raw = await _call_groq(messages, _get_api_key())
        data = json.loads(_clean_json(raw))
        validated = _validate(data)
        return AgentResult(
            agent_name=agent_name,
            issues=validated.get("issues", []),
            summary=validated.get("summary", ""),
            skipped=False
        )
    except Exception as e:
        logger.error(f"{agent_name} run failed: {e}")
        return AgentResult(agent_name=agent_name, issues=[], summary="Failed", skipped=True, skip_reason=str(e))


class SecurityAgent(BaseAgent):
    name = "SecurityAgent"
    
    def relevance_hint(self, context: AgentContext) -> bool:
        return any(f.endswith((".py", ".js", ".yml", ".yaml", ".json")) for f in context.changed_files) or "password" in context.diff.lower() or "token" in context.diff.lower()
        
    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, "Security vulnerabilities, injections, secrets", context)


class ArchitectureAgent(BaseAgent):
    name = "ArchitectureAgent"
    
    def relevance_hint(self, context: AgentContext) -> bool:
        return any(f.endswith(".py") and not f.startswith("tests/") for f in context.changed_files)
        
    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, "Project patterns, structural design", context)


class PerformanceAgent(BaseAgent):
    name = "PerformanceAgent"
    
    def relevance_hint(self, context: AgentContext) -> bool:
        return "for " in context.diff or "while " in context.diff or any(f.endswith((".py", ".js")) for f in context.changed_files)
        
    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, "Algorithmic complexity, expensive operations", context)


class TestCoverageAgent(BaseAgent):
    name = "TestCoverageAgent"
    
    def relevance_hint(self, context: AgentContext) -> bool:
        return any("test" in f.lower() for f in context.changed_files)
        
    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, "Missing assertions, edge cases", context)


class DependencyAgent(BaseAgent):
    name = "DependencyAgent"
    
    def relevance_hint(self, context: AgentContext) -> bool:
        req_files = {"requirements.txt", "package.json", "Pipfile"}
        return any(f in req_files for f in context.changed_files) or "import " in context.diff
        
    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, "Outdated packages, licensing issues", context)


class SynthesisAgent(BaseAgent):
    name = "SynthesisAgent"
    
    def relevance_hint(self, context: AgentContext) -> bool:
        return True
        
    async def run(self, context: AgentContext, results: List[AgentResult] = None) -> dict:
        if not results:
            results = []
            
        valid_results = [r for r in results if not r.skipped]
        
        if len(valid_results) == 1:
            return {
                "issues": valid_results[0].issues,
                "summary": valid_results[0].summary
            }
            
        all_issues = []
        for r in valid_results:
            all_issues.extend(r.issues)
            
        if not all_issues:
            return {"issues": [], "summary": "No issues found by agents."}
            
        # Deduplicate with Groq
        prompt = f"""Aggregate and deduplicate the following issues found by specialized agents:
{json.dumps(all_issues, indent=2)}
"""
        messages = [
            {"role": "system", "content": "Return ONLY valid JSON. Schema: {'issues': [...], 'summary': '...'} combining all unique issues."},
            {"role": "user", "content": prompt},
        ]
        
        try:
            raw = await _call_groq(messages, _get_api_key())
            data = json.loads(_clean_json(raw))
            return _validate(data)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"issues": all_issues, "summary": f"Synthesis failed, returning raw combined issues. ({e})"}
