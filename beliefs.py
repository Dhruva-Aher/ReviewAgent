import json
import logging
from pathlib import Path

BELIEFS_PATH = Path("beliefs.json")

DEFAULT_BELIEFS = {
    "rules": [
        "All public functions must have explicit return type annotations",
        "Never use bare except clauses — always catch specific exceptions",
        "Database queries must never be constructed with string formatting (SQL injection risk)",
        "All API endpoints must validate and sanitize input before processing",
        "Secrets and credentials must never be hardcoded — use environment variables"
    ],
    "past_decisions": [
        "We use httpx over requests for all HTTP calls — decided for async compatibility",
        "SQLite for local persistence, PostgreSQL in production — do not introduce new ORMs",
        "Pydantic v2 for all data validation — do not use dataclasses for API models",
        "All errors must be raised as HTTPException with a clear detail message — no silent failures"
    ]
}

logger = logging.getLogger(__name__)


def load() -> dict:
    if not BELIEFS_PATH.exists():
        logger.info("beliefs.json not found — creating with defaults")
        save(DEFAULT_BELIEFS)
        return dict(DEFAULT_BELIEFS)
    try:
        data = json.loads(BELIEFS_PATH.read_text())
        if not isinstance(data, dict):
            raise ValueError("beliefs.json root must be a JSON object")
        data.setdefault("rules", [])
        data.setdefault("past_decisions", [])
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Corrupt beliefs.json ({e}) — resetting to defaults")
        save(DEFAULT_BELIEFS)
        return dict(DEFAULT_BELIEFS)
    except Exception as e:
        logger.error(f"Failed to read beliefs.json ({e}) — using in-memory defaults")
        return dict(DEFAULT_BELIEFS)


def save(beliefs: dict) -> None:
    try:
        BELIEFS_PATH.write_text(json.dumps(beliefs, indent=2))
    except Exception as e:
        logger.error(f"Failed to save beliefs.json: {e}")


def append_decision(decision: str) -> None:
    if not decision or not decision.strip():
        return
    beliefs = load()
    if decision not in beliefs["past_decisions"]:
        beliefs["past_decisions"].append(decision)
        save(beliefs)


def format_for_prompt(beliefs: dict) -> str:
    parts = []
    if beliefs.get("rules"):
        rules_text = "\n".join(f"  - {r}" for r in beliefs["rules"])
        parts.append(f"RULES:\n{rules_text}")
    if beliefs.get("past_decisions"):
        decisions_text = "\n".join(f"  - {d}" for d in beliefs["past_decisions"])
        parts.append(f"PAST DECISIONS:\n{decisions_text}")
    return "\n\n".join(parts) if parts else "No beliefs loaded."
