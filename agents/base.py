from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AgentContext:
    diff: str
    beliefs_text: str
    repo: str
    pr_number: int
    pr_title: str
    pr_description: str
    changed_files: List[str]
    config: dict
    max_findings: int = 5

@dataclass
class AgentResult:
    agent_name: str
    issues: List[dict]
    summary: str
    skipped: bool
    skip_reason: Optional[str] = None

class BaseAgent:
    name: str = "base"
    description: str = "Base agent"

    def relevance_hint(self, context: AgentContext) -> bool:
        return True

    async def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError
