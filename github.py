import logging
import os
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"
TIMEOUT = 15


def _get_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not set")
    return token


def _headers(accept: str = "application/vnd.github+json") -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _handle_response(resp: httpx.Response, context: str) -> None:
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="GitHub token is invalid or expired")
    if resp.status_code == 403:
        raise HTTPException(status_code=429, detail=f"GitHub API rate limit exceeded on {context}")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Not found: {context}")
    if resp.status_code == 422:
        raise HTTPException(status_code=422, detail=f"GitHub rejected request on {context}: {resp.text[:200]}")
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error {resp.status_code} on {context}: {resp.text[:200]}"
        )


def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    if not owner or not repo:
        raise HTTPException(status_code=422, detail="owner and repo must not be empty")
    if pr_number < 1:
        raise HTTPException(status_code=422, detail="pr_number must be a positive integer")

    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        resp = httpx.get(
            url,
            headers=_headers("application/vnd.github.diff"),
            timeout=TIMEOUT,
            follow_redirects=True,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"GitHub timed out fetching diff for {owner}/{repo} PR #{pr_number}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error fetching diff: {e}")

    _handle_response(resp, f"PR #{pr_number} diff in {owner}/{repo}")
    diff = resp.text.strip()
    if not diff:
        raise HTTPException(status_code=422, detail=f"PR #{pr_number} has no diff — may be empty or already merged")
    return diff


def fetch_pr_meta(owner: str, repo: str, pr_number: int) -> dict:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        resp = httpx.get(url, headers=_headers(), timeout=TIMEOUT, follow_redirects=True)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GitHub timed out fetching PR metadata")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error fetching PR metadata: {e}")

    _handle_response(resp, f"PR #{pr_number} metadata in {owner}/{repo}")
    data = resp.json()
    return {
        "title": data.get("title", ""),
        "author": data.get("user", {}).get("login", ""),
        "base": data.get("base", {}).get("ref", ""),
        "head": data.get("head", {}).get("ref", ""),
        "additions": data.get("additions", 0),
        "deletions": data.get("deletions", 0),
        "changed_files": data.get("changed_files", 0),
    }


def post_comment(owner: str, repo: str, pr_number: int, body: str) -> str:
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    try:
        resp = httpx.post(
            url,
            headers=_headers(),
            json={"body": body},
            timeout=TIMEOUT,
        )
    except httpx.TimeoutException:
        logger.error(f"GitHub timed out posting comment to {owner}/{repo} PR #{pr_number}")
        logger.info(f"Review output (not posted):\n{body}")
        return ""
    except httpx.RequestError as e:
        logger.error(f"Network error posting comment: {e}")
        logger.info(f"Review output (not posted):\n{body}")
        return ""

    try:
        _handle_response(resp, f"posting comment on {owner}/{repo} PR #{pr_number}")
    except HTTPException as e:
        logger.error(f"Failed to post GitHub comment: {e.detail}")
        logger.info(f"Review output (not posted):\n{body}")
        return ""

    url = resp.json().get("html_url", "")
    logger.info(f"Comment posted: {url}")
    return url
