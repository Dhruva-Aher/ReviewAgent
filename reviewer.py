import json
import logging
import os
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
MAX_DIFF = 80_000

FALLBACK_REVIEW = {
    "issues": [],
    "summary": "Unable to generate structured review safely. Please retry."
}

SYSTEM_PROMPT = """\
You are a senior software engineer performing a code review.

You will be given a git diff and a belief system of team rules and past decisions.

Return ONLY valid JSON. No markdown. No prose before or after. No code fences.

Schema:
{
  "issues": [
    {
      "type": "bug | style | architecture",
      "severity": "low | medium | high",
      "message": "Specific description referencing actual code in the diff",
      "suggestion": "Exact fix or alternative",
      "reference": "Cited rule or past decision, or null",
      "confidence": 85
    }
  ],
  "summary": "2-3 sentence overall assessment. Be direct. No filler."
}

confidence is an integer 0-100 representing how certain you are about each issue.
STRICT: Every issue must reference actual code from the diff. No hallucinations."""

CORRECTION_PROMPT = """\
Your previous response was not valid JSON. Return ONLY the JSON object with no extra text.
Do not include markdown fences, explanation, or any prose.
The schema is:
{
  "issues": [{"type":"...","severity":"...","message":"...","suggestion":"...","reference":null,"confidence":80}],
  "summary": "..."
}"""


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set")
    return key


def _build_prompt(diff: str, beliefs_text: str, repo: str, pr_number: int) -> str:
    return f"""REPO: {repo}
PR: #{pr_number}

--- BELIEF SYSTEM ---
{beliefs_text}

--- DIFF ---
{diff}"""


def _call_groq(messages: list, api_key: str) -> str:
    try:
        resp = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 2048,
            },
            timeout=30,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Groq API timed out")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error calling Groq: {e}")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Groq API key is invalid")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="Groq rate limit exceeded — wait 60s and retry")
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Groq error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"Unexpected Groq response shape: {e}")


def _clean_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        cleaned = "\n".join(lines[1:end])
    return cleaned.strip()


def _validate(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Response is not a JSON object")
    if "issues" not in data or "summary" not in data:
        raise ValueError(f"Missing required keys. Got: {list(data.keys())}")
    if not isinstance(data["issues"], list):
        raise ValueError("'issues' must be a list")

    for i, issue in enumerate(data["issues"]):
        for field in ("type", "severity", "message", "suggestion"):
            if field not in issue:
                raise ValueError(f"Issue #{i} missing field '{field}'")
        if issue["type"] not in ("bug", "style", "architecture"):
            issue["type"] = "style"
        if issue["severity"] not in ("low", "medium", "high"):
            issue["severity"] = "low"
        issue.setdefault("reference", None)
        try:
            issue["confidence"] = max(0, min(100, int(issue.get("confidence", 75))))
        except (TypeError, ValueError):
            issue["confidence"] = 75

    return data


def run_review(diff: str, beliefs_text: str, repo: str, pr_number: int) -> dict:
    if not diff or len(diff.strip()) < 10:
        raise HTTPException(status_code=422, detail="Diff is empty or too short to review")

    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF] + "\n\n[DIFF TRUNCATED — exceeded 80k characters]"
        logger.warning(f"Diff truncated to {MAX_DIFF} chars for {repo} PR #{pr_number}")

    api_key = _get_api_key()
    prompt = _build_prompt(diff, beliefs_text, repo, pr_number)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    logger.info(f"Calling Groq for {repo} PR #{pr_number}")
    raw = _call_groq(messages, api_key)

    try:
        data = json.loads(_clean_json(raw))
        return _validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"First parse failed ({e}) — retrying with correction prompt")

    retry_messages = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": CORRECTION_PROMPT},
    ]

    try:
        raw2 = _call_groq(retry_messages, api_key)
        data = json.loads(_clean_json(raw2))
        return _validate(data)
    except Exception as e:
        logger.error(f"Retry also failed ({e}) — returning safe fallback")
        return dict(FALLBACK_REVIEW)
