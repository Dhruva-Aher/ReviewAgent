import logging
import os
import httpx
from fastapi import HTTPException
import base64

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"
TIMEOUT = 15


def _get_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not set")
    return token


def _personal_headers(accept: str = "application/vnd.github+json") -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _app_headers(installation_id: int, accept: str = "application/vnd.github+json") -> dict:
    from github_app import get_installation_token
    token = get_installation_token(installation_id)
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _headers(installation_id: int = None, accept: str = "application/vnd.github+json") -> dict:
    if installation_id and os.getenv("GITHUB_APP_ID"):
        return _app_headers(installation_id, accept)
    return _personal_headers(accept)


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


def fetch_pr_diff(owner: str, repo: str, pr_number: int, installation_id: int = None) -> str:
    if not owner or not repo:
        raise HTTPException(status_code=422, detail="owner and repo must not be empty")
    if pr_number < 1:
        raise HTTPException(status_code=422, detail="pr_number must be a positive integer")

    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        resp = httpx.get(
            url,
            headers=_headers(installation_id, "application/vnd.github.diff"),
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


def fetch_pr_meta(owner: str, repo: str, pr_number: int, installation_id: int = None) -> dict:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        resp = httpx.get(url, headers=_headers(installation_id), timeout=TIMEOUT, follow_redirects=True)
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


def fetch_file_content(owner: str, repo: str, path: str, ref: str, installation_id: int = None) -> str:
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref} if ref else {}
    try:
        resp = httpx.get(url, params=params, headers=_headers(installation_id), timeout=TIMEOUT)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error fetching file {path}: {e}")

    _handle_response(resp, f"fetching {path} in {owner}/{repo}")
    data = resp.json()
    if "content" in data:
        return base64.b64decode(data["content"]).decode('utf-8')
    raise HTTPException(status_code=404, detail="File content not found")


def fetch_pr_review_comments(owner: str, repo: str, pr_number: int, installation_id: int = None) -> list:
    url_commits = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    url_issues = f"{BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"

    comments = []

    try:
        resp1 = httpx.get(url_commits, headers=_headers(installation_id), timeout=TIMEOUT)
        if resp1.status_code == 200:
            comments.extend([c.get("body", "") for c in resp1.json() if c.get("body")])

        resp2 = httpx.get(url_issues, headers=_headers(installation_id), timeout=TIMEOUT)
        if resp2.status_code == 200:
            comments.extend([c.get("body", "") for c in resp2.json() if c.get("body")])
    except httpx.RequestError as e:
        logger.error(f"Network error fetching PR comments: {e}")

    return comments


def fetch_bot_comments(owner: str, repo: str, pr_number: int, installation_id: int = None) -> list:
    url_issues = f"{BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"

    comments = []

    try:
        resp = httpx.get(url_issues, headers=_headers(installation_id), timeout=TIMEOUT)
        if resp.status_code == 200:
            for c in resp.json():
                login = c.get("user", {}).get("login", "")
                if login.endswith("[bot]") and c.get("body"):
                    comments.append(c["body"])
    except httpx.RequestError as e:
        logger.error(f"Network error fetching bot comments: {e}")

    return comments


def post_review_with_inline_comments(owner: str, repo: str, pr_number: int, review_result: dict, installation_id: int = None) -> str:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

    issues = review_result.get("issues", [])
    inline_comments = []

    for i in issues:
        file_path = i.get("file")
        line = i.get("line")
        if file_path and line:
            body = f"**[{i.get('type', 'style')}]** {i.get('severity', 'low').upper()}: {i.get('message')} - {i.get('suggestion')}"
            if i.get("reference"):
                body += f"\\n\\n*Reference: {i['reference']}*"
            inline_comments.append({
                "path": file_path,
                "line": int(line),
                "body": body
            })

    if not inline_comments:
        return ""

    payload = {
        "event": "COMMENT",
        "comments": inline_comments
    }

    try:
        resp = httpx.post(
            url,
            headers=_headers(installation_id),
            json=payload,
            timeout=TIMEOUT,
        )
    except httpx.RequestError as e:
        logger.error(f"Network error posting inline review: {e}")
        return ""

    if resp.status_code == 422:
        logger.warning(f"GitHub returned 422 for inline comments on {owner}/{repo} PR #{pr_number}. Falling back to general comment.")
        import formatter
        body = formatter.to_github_comment(review_result, f"{owner}/{repo}", pr_number)
        return post_comment(owner, repo, pr_number, body, installation_id)

    try:
        _handle_response(resp, f"posting inline review on {owner}/{repo} PR #{pr_number}")
    except HTTPException as e:
        logger.error(f"Failed to post GitHub inline review: {e.detail}")
        return ""

    return resp.json().get("html_url", "")

def post_comment(owner: str, repo: str, pr_number: int, body: str, installation_id: int = None) -> str:
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    try:
        resp = httpx.post(
            url,
            headers=_headers(installation_id),
            json={"body": body},
            timeout=TIMEOUT,
        )
    except httpx.TimeoutException:
        logger.error(f"GitHub timed out posting comment to {owner}/{repo} PR #{pr_number}")
        logger.info(f"Review output (not posted):\\n{body}")
        return ""
    except httpx.RequestError as e:
        logger.error(f"Network error posting comment: {e}")
        logger.info(f"Review output (not posted):\\n{body}")
        return ""

    try:
        _handle_response(resp, f"posting comment on {owner}/{repo} PR #{pr_number}")
    except HTTPException as e:
        logger.error(f"Failed to post GitHub comment: {e.detail}")
        logger.info(f"Review output (not posted):\\n{body}")
        return ""

    url = resp.json().get("html_url", "")
    logger.info(f"Comment posted: {url}")
    return url

def fetch_repo_config(owner: str, repo: str, ref: str, installation_id: int = None) -> str:
    """
    Attempts to fetch PRBeliefs configuration from common repository locations.
    Returns the YAML string if found, or an empty string if none exist.
    """
    paths = [
        ".github/prbeliefs.yml",
        ".github/prbeliefs.yaml",
        ".prbeliefs.yml",
        ".prbeliefs.yaml"
    ]
    
    for path in paths:
        try:
            content = fetch_file_content(owner, repo, path, ref, installation_id)
            logger.info(f"[GITHUB] Found repository configuration at {path}")
            return content
        except HTTPException as e:
            if e.status_code == 404:
                continue
            logger.warning(f"Failed to fetch config at {path}: {e.detail}")
            
    logger.info(f"[GITHUB] No repository configuration found for {owner}/{repo}")
    return ""
