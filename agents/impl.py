import json
import logging
from agents.base import BaseAgent, AgentContext, AgentResult
from reviewer import _call_groq, _clean_json, _validate, _get_api_key

logger = logging.getLogger(__name__)


# Shared system prompt for all specialist agents.
# Each agent receives a different focus area in the user message.
_AGENT_SYSTEM_PROMPT = """\
You are a senior software engineer doing a focused code review.

Your job is to find real problems — bugs, vulnerabilities, and design issues — not style nits.

DO NOT comment on: formatting, missing docstrings, import ordering, naming preferences,
or cosmetic issues that do not affect correctness or security.

Return at most 3 issues. Prioritize severity. If there are no real issues, return an empty list.

Every issue must:
- Reference the actual code from the diff (file name and line)
- Explain what is wrong and why it matters in production
- Suggest a concrete fix

Return ONLY valid JSON. No markdown fences.

Schema:
{
  "issues": [
    {
      "type": "bug | security | performance | architecture",
      "severity": "low | medium | high",
      "message": "...",
      "suggestion": "...",
      "reference": null,
      "confidence": 85,
      "file": "path/to/file.py",
      "line": 42
    }
  ],
  "summary": "One sentence on what you checked and what you found."
}"""


_AGENT_FOCUSES = {
    "SecurityAgent": """\
Focus ONLY on security issues:
- Hardcoded secrets, tokens, or passwords in code
- SQL injection via string formatting
- Command injection
- Path traversal
- Missing authentication or authorization checks
- Input not validated before reaching databases or external services
- Insecure deserialization
- Exposed sensitive data in logs or responses

Ignore performance and style entirely.""",

    "ArchitectureAgent": """\
Focus ONLY on architectural and design problems:
- Violations of the team's stated engineering decisions (check the belief system)
- Backwards-incompatible changes to public APIs or data schemas
- Circular dependencies or tight coupling that will make the code hard to change
- Functions doing too many things (violation of single responsibility)
- Shared mutable state that could cause concurrency bugs
- Missing error handling that will cause silent failures

Ignore formatting and style entirely.""",

    "PerformanceAgent": """\
Focus ONLY on performance problems:
- O(n²) or worse algorithms where O(n) or O(n log n) is straightforward
- N+1 database query patterns (query inside a loop)
- Loading entire datasets into memory when streaming is possible
- Repeated expensive computation that could be cached
- Synchronous blocking calls inside async functions
- Unbounded inputs with no size limit

Ignore architecture and style entirely.""",

    "TestCoverageAgent": """\
Focus ONLY on test quality and missing coverage:
- Tests that cannot actually fail (always-true assertions)
- Missing tests for error cases, empty inputs, or edge cases
- Tests that mock so heavily they test nothing real
- Missing validation of important side effects
- Integration paths with no test coverage at all

Only comment if the gap would let a real bug ship undetected.
Ignore style and formatting entirely.""",

    "DependencyAgent": """\
Focus ONLY on dependency and compatibility problems:
- New dependencies added without a clear reason
- Dependencies with known security vulnerabilities
- Version pins that are overly tight or overly loose
- Direct use of a library the team has decided to avoid (check belief system)
- Missing dependency for something the code now imports

Ignore style entirely.""",
}


async def _agent_run_impl(agent_name: str, context: AgentContext) -> AgentResult:
    focus = _AGENT_FOCUSES.get(agent_name, "")
    prompt = f"""{focus}

REPO: {context.repo}
PR: #{context.pr_number}
PR TITLE: {context.pr_title}

--- TEAM RULES AND PAST DECISIONS ---
{context.beliefs_text}

--- DIFF ---
{context.diff[:80000]}"""

    messages = [
        {"role": "system", "content": _AGENT_SYSTEM_PROMPT},
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
            skipped=False,
        )
    except Exception as e:
        logger.error(f"{agent_name} run failed: {e}")
        return AgentResult(agent_name=agent_name, issues=[], summary="Failed", skipped=True, skip_reason=str(e))


def _deduplicate_issues(all_issues: list[dict]) -> list[dict]:
    """
    Deterministic deduplication — no LLM call needed.
    Two issues are considered duplicates if they reference the same file+line,
    or if their messages share more than 60% of words.
    Keeps the highest-severity version when deduplicating.
    Returns at most 5 issues, ordered by severity.
    """
    severity_rank = {"high": 0, "medium": 1, "low": 2}

    def message_words(issue: dict) -> set[str]:
        return set(issue.get("message", "").lower().split())

    def are_duplicates(a: dict, b: dict) -> bool:
        # Same file and line → definite duplicate
        if a.get("file") and a.get("file") == b.get("file"):
            if a.get("line") and a.get("line") == b.get("line"):
                return True
        # Significant word overlap → near-duplicate
        words_a = message_words(a)
        words_b = message_words(b)
        if words_a and words_b:
            overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
            if overlap > 0.6:
                return True
        return False

    kept: list[dict] = []
    for issue in sorted(all_issues, key=lambda i: severity_rank.get(i.get("severity", "low"), 2)):
        is_dup = any(are_duplicates(issue, k) for k in kept)
        if not is_dup:
            kept.append(issue)
        if len(kept) == 5:
            break

    return kept


class SecurityAgent(BaseAgent):
    name = "SecurityAgent"

    def relevance_hint(self, context: AgentContext) -> bool:
        diff_lower = context.diff.lower()
        return (
            any(f.endswith((".py", ".js", ".yml", ".yaml", ".json", ".env")) for f in context.changed_files)
            or "password" in diff_lower
            or "secret" in diff_lower
            or "token" in diff_lower
            or "auth" in diff_lower
        )

    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, context)


class ArchitectureAgent(BaseAgent):
    name = "ArchitectureAgent"

    def relevance_hint(self, context: AgentContext) -> bool:
        return any(f.endswith(".py") and not f.startswith("tests/") for f in context.changed_files)

    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, context)


class PerformanceAgent(BaseAgent):
    name = "PerformanceAgent"

    def relevance_hint(self, context: AgentContext) -> bool:
        return "for " in context.diff or "while " in context.diff or any(
            f.endswith((".py", ".js")) for f in context.changed_files
        )

    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, context)


class TestCoverageAgent(BaseAgent):
    name = "TestCoverageAgent"

    def relevance_hint(self, context: AgentContext) -> bool:
        return any("test" in f.lower() for f in context.changed_files)

    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, context)


class DependencyAgent(BaseAgent):
    name = "DependencyAgent"

    def relevance_hint(self, context: AgentContext) -> bool:
        req_files = {"requirements.txt", "package.json", "Pipfile", "pyproject.toml"}
        return any(f in req_files for f in context.changed_files) or "import " in context.diff

    async def run(self, context: AgentContext) -> AgentResult:
        return await _agent_run_impl(self.name, context)


def synthesize_results(results: list[AgentResult]) -> dict:
    """
    Combine results from all agents into a single review dict.
    Uses deterministic deduplication — no extra LLM call.
    """
    valid = [r for r in results if not r.skipped]

    if not valid:
        return {"issues": [], "summary": "All agents skipped or failed — no review generated."}

    if len(valid) == 1:
        return {"issues": valid[0].issues, "summary": valid[0].summary}

    all_issues = [issue for r in valid for issue in r.issues]
    deduped = _deduplicate_issues(all_issues)

    agent_summaries = "; ".join(r.summary for r in valid if r.summary and r.summary != "Failed")
    summary = agent_summaries if agent_summaries else "Review complete."

    return {"issues": deduped, "summary": summary}
