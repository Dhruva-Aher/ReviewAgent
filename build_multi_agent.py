import os

os.makedirs('agents', exist_ok=True)

open('agents/__init__.py', 'w').close()

with open('agents/base.py', 'w') as f:
    f.write('''\
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
''')

with open('agents/supervisor.py', 'w') as f:
    f.write('''\
import json
import logging
from .base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

class SupervisorAgent:
    name = "supervisor"

    async def get_relevant_agents(self, context: AgentContext) -> list[str]:
        # Dummy implementation to avoid huge groq calls for now, fall back to all
        return ["security", "architecture", "performance", "test_coverage", "dependency"]
''')

with open('orchestrator.py', 'w') as f:
    f.write('''\
import asyncio
import time
import logging
from agents.base import AgentContext, AgentResult

logger = logging.getLogger(__name__)

async def run_multi_agent_review(context: AgentContext, selected_agents: list[str]) -> dict:
    return {"issues": [], "summary": "Multi agent review summary."}
''')

print("Created multi_agent structure")
