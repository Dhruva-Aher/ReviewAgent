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
    "summary": "Unable to generate structured review safely. Please retry.",
}

SYSTEM_PROMPT = """\
You are a senior software engineer reviewing a teammate's pull request.

Your job is to find problems that would matter in production.

REVIEW PRIORITIES (in order):
1. Repository beliefs
2. Previous engineering decisions
3. Architecture consistency
4. Correctness — logic errors, off-by-one errors, wrong conditions
5. Security — injections, hardcoded secrets, authentication gaps
6. Performance — O(n²) loops, N+1 queries, unnecessary allocations
7. Edge cases — empty inputs, None values, concurrent access
8. API misuse — wrong method called, incorrect error handling

STYLE COMMENTS ARE DISABLED.

Never comment on:
* type hints
* return type annotations
* parameter annotations
* docstrings
* formatting
* naming
* whitespace
* import ordering
* line length

These findings are invalid.

If they are the only issues, approve the pull request.

CONFIDENCE CALIBRATION:
- 90–100: You are certain this is a bug or security issue
- 70–89: You are fairly sure this will cause problems in real use
- 50–69: This could become a problem under specific conditions — state them
- Below 50: Do not include this issue

ISSUE LIMIT:
Return at most 5 issues. If you find more, keep the highest severity ones.
If there are no issues worth flagging, return an empty issues list and write
a short summary explaining what looks good about the PR.

EVERY issue must:
- Reference the actual code from the diff (file name and approximate line)
- Explain what is wrong
- Explain why it matters (what could actually go wrong)
- Suggest a concrete fix

Return ONLY valid JSON. No markdown fences. No prose before or after.

Schema:
{
  "issues": [
    {
      "type": "bug | security | performance | architecture",
      "severity": "low | medium | high",
      "message": "What is wrong, referencing the actual code",
      "suggestion": "Concrete fix or alternative",
      "reference": "The team rule or past decision this violates, or null",
      "confidence": 85,
      "file": "path/to/file.py or null",
      "line": 42
    }
  ],
  "summary": "2-4 sentences. What looks good, what needs attention, overall recommendation."
}

STRICT: Every issue must reference actual code from the diff. Do not invent issues."""

CORRECTION_PROMPT = """\
Your previous response was not valid JSON. Return ONLY the JSON object with no extra text.
Do not include markdown fences, explanation, or any prose.
Schema:
{
  "issues": [{"type":"bug","severity":"high","message":"...","suggestion":"...","reference":null,"confidence":80,"file":null,"line":null}],
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

--- TEAM RULES AND PAST DECISIONS ---
{beliefs_text}

--- DIFF ---
{diff}"""


async def _call_groq(messages: list, api_key: str) -> str:
    print(f"=== GROQ REQUEST PAYLOAD ===\n{json.dumps(messages, indent=2)}\n============================")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
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

    valid_types = ("bug", "security", "performance", "architecture", "style")
    for i, issue in enumerate(data["issues"]):
        for field in ("type", "severity", "message", "suggestion"):
            if field not in issue:
                raise ValueError(f"Issue #{i} missing field '{field}'")
        if issue["type"] not in valid_types:
            issue["type"] = "bug"
        if issue["severity"] not in ("low", "medium", "high"):
            issue["severity"] = "low"
        issue.setdefault("reference", None)
        try:
            issue["confidence"] = max(0, min(100, int(issue.get("confidence", 75))))
        except (TypeError, ValueError):
            issue["confidence"] = 75

    # Enforce the 5-issue cap here as a safety net
    data["issues"] = data["issues"][:5]
    return data


async def run_review(diff: str, beliefs_text: str, repo: str, pr_number: int) -> dict:
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
    raw = await _call_groq(messages, api_key)

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
        raw2 = await _call_groq(retry_messages, api_key)
        data = json.loads(_clean_json(raw2))
        return _validate(data)
    except Exception as e:
        logger.error(f"Retry also failed ({e}) — returning safe fallback")
        return dict(FALLBACK_REVIEW)
