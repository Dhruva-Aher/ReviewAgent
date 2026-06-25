import yaml
from typing import Optional, List
from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger(__name__)

class Rule(BaseModel):
    text: str
    category: Optional[str] = "maintainability"
    priority: Optional[str] = "medium"
    message: Optional[str] = None

class ReviewSettings(BaseModel):
    exclude: Optional[List[str]] = []
    max_findings: Optional[int] = 5
    strictness: Optional[str] = "medium"

class RepoConfig(BaseModel):
    version: int = 1
    extends: Optional[List[str]] = []
    review: Optional[ReviewSettings] = None
    rules: Optional[List[Rule]] = []
    architecture: Optional[List[str]] = []

def parse_yaml(yaml_str: str) -> RepoConfig:
    """
    Parses a YAML string into a valid RepoConfig.
    Fails gracefully and returns an empty config if YAML is invalid.
    """
    if not yaml_str or not yaml_str.strip():
        return RepoConfig()

    try:
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            logger.warning("[CONFIG] YAML does not contain a dictionary. Using empty config.")
            return RepoConfig()
            
        return RepoConfig(**data)
    except yaml.YAMLError as e:
        logger.warning(f"[CONFIG] YAML syntax error: {e}. Proceeding with empty config.")
        return RepoConfig()
    except ValidationError as e:
        logger.warning(f"[CONFIG] Schema validation error: {e}. Proceeding with empty config.")
        return RepoConfig()
    except Exception as e:
        logger.error(f"[CONFIG] Unexpected error parsing config: {e}. Proceeding with empty config.")
        return RepoConfig()

def format_for_prompt(config: RepoConfig, repo: str = None) -> str:
    """
    Formats the parsed RepoConfig into the text block expected by the LLM.
    """
    rules_critical = []
    rules_high = []
    rules_medium = []
    rules_low = []
    
    for rule in config.rules:
        text = rule.text
        if rule.message:
            text += f" (Custom Message to output: {rule.message})"
        pri = (rule.priority or "medium").lower()
        if pri == "critical":
            rules_critical.append(text)
        elif pri == "high":
            rules_high.append(text)
        elif pri == "low":
            rules_low.append(text)
        else:
            rules_medium.append(text)

    parts = []
    
    if rules_critical or rules_high or rules_medium or rules_low:
        parts.append("Repository Engineering Rules")
        if rules_critical:
            parts.append("Critical\n" + "\n".join(f"- {text}" for text in rules_critical))
        if rules_high:
            parts.append("High\n" + "\n".join(f"- {text}" for text in rules_high))
        if rules_medium:
            parts.append("Medium\n" + "\n".join(f"- {text}" for text in rules_medium))
        if rules_low:
            parts.append("Low\n" + "\n".join(f"- {text}" for text in rules_low))
            
    if config.architecture:
        parts.append("Architecture Decisions\n" + "\n".join(f"- {text}" for text in config.architecture))

    parts.append(f"Context\nRepository: {repo or 'Unknown'}\nLanguage: Python\nFramework: None")
    
    return "\n\n".join(parts)
