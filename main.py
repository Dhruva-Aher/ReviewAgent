import hmac
import hashlib
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import beliefs as belief_store
import github
import reviewer
import formatter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("review_agent")

_beliefs: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _beliefs
    _beliefs = belief_store.load()
    logger.info(
        f"ReviewAgent started — "
        f"{len(_beliefs['rules'])} rule(s), "
        f"{len(_beliefs['past_decisions'])} past decision(s)"
    )
    yield


app = FastAPI(
    title="ReviewAgent",
    description="Autonomous PR review agent with persistent belief system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    repo: str
    pr_number: int
    diff: Optional[str] = None
    post_comment: bool = False

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        parts = v.strip().split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("repo must be in 'owner/repo' format")
        return v.strip()

    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("pr_number must be a positive integer")
        return v


class AddBeliefRequest(BaseModel):
    type: str
    value: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("rules", "past_decisions"):
            raise ValueError("type must be 'rules' or 'past_decisions'")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("value must not be empty")
        return v


def _run_pipeline(
    repo: str,
    pr_number: int,
    diff: Optional[str],
    post_comment_flag: bool,
    installation_id: int = None,
) -> dict:
    global _beliefs

    owner, repo_name = repo.split("/")
    meta = {}

    if not diff:
        logger.info(f"[FETCH] Fetching diff — {repo} PR #{pr_number}")
        diff = github.fetch_pr_diff(owner, repo_name, pr_number, installation_id)
        try:
            meta = github.fetch_pr_meta(owner, repo_name, pr_number, installation_id)
        except HTTPException:
            meta = {}

    diff = diff.strip()
    if not diff:
        raise HTTPException(status_code=422, detail="Diff is empty — nothing to review")

    beliefs_text = belief_store.format_for_prompt(_beliefs)
    logger.info(f"[REVIEW] Starting — {repo} PR #{pr_number} ({len(diff)} chars)")

    review_result = reviewer.run_review(
        diff=diff,
        beliefs_text=beliefs_text,
        repo=repo,
        pr_number=pr_number,
    )

    issue_count = len(review_result.get("issues", []))
    high_count = sum(1 for i in review_result.get("issues", []) if i.get("severity") == "high")
    logger.info(f"[REVIEW] Complete — {repo} PR #{pr_number} — {issue_count} issue(s), {high_count} high severity")

    comment_body = formatter.to_github_comment(review_result, repo, pr_number)
    comment_url = None

    if post_comment_flag:
        logger.info(f"[GITHUB] Posting comment — {repo} PR #{pr_number}")
        comment_url = github.post_comment(owner, repo_name, pr_number, comment_body, installation_id)
        if comment_url:
            logger.info(f"[GITHUB] Comment posted — {comment_url}")
        else:
            logger.warning(f"[GITHUB] Comment failed — review printed to console")

    high_issues = [i for i in review_result.get("issues", []) if i.get("severity") == "high"]
    if high_issues:
        decision = (
            f"PR #{pr_number} in {repo}: flagged {len(high_issues)} "
            f"high-severity issue(s) — {high_issues[0]['message'][:80]}"
        )
        belief_store.append_decision(decision)
        _beliefs = belief_store.load()
        logger.info(f"[BELIEFS] Updated with finding from {repo} PR #{pr_number}")

    return {
        "repo": repo,
        "pr_number": pr_number,
        "meta": meta,
        "review": review_result,
        "comment": comment_body,
        "comment_url": comment_url,
        "beliefs_updated": bool(high_issues),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "beliefs": len(_beliefs.get("rules", [])),
        "mode": "github_app" if os.getenv("GITHUB_APP_ID") else "personal_token"
    }


@app.get("/beliefs")
def get_beliefs():
    return belief_store.load()


@app.post("/beliefs")
def add_belief(req: AddBeliefRequest):
    global _beliefs
    current = belief_store.load()
    if req.value in current[req.type]:
        return {"status": "already_exists", "beliefs": current}
    current[req.type].append(req.value)
    belief_store.save(current)
    _beliefs = current
    logger.info(f"[BELIEFS] Added to '{req.type}': {req.value[:60]}")
    return {"status": "added", "beliefs": current}


@app.post("/review")
def review(req: ReviewRequest):
    logger.info(f"[MANUAL] Review triggered — {req.repo} PR #{req.pr_number}")
    return _run_pipeline(
        repo=req.repo,
        pr_number=req.pr_number,
        diff=req.diff,
        post_comment_flag=req.post_comment,
    )


@app.post("/webhook")
async def webhook(request: Request):
    event = request.headers.get("X-GitHub-Event", "")
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "").strip()
    if webhook_secret:
        expected = "sha256=" + hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.warning("[WEBHOOK] Invalid signature — rejected")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if event == "installation":
        payload = await request.json()
        action = payload.get("action", "")
        account = payload.get("installation", {}).get("account", {}).get("login", "unknown")
        logger.info(f"[APP] Installation {action} by {account}")
        return {"status": "ok", "action": action}

    if event != "pull_request":
        logger.info(f"[WEBHOOK] Ignored event: {event}")
        return {"status": "ignored", "event": event}

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action", "")
    if action not in ("opened", "synchronize"):
        logger.info(f"[WEBHOOK] Ignored PR action: {action}")
        return {"status": "ignored", "action": action}

    try:
        pr = payload["pull_request"]
        repo_data = payload["repository"]
        owner = repo_data["owner"]["login"]
        repo_name = repo_data["name"]
        pr_number = pr["number"]
        repo = f"{owner}/{repo_name}"
        installation_id = payload.get("installation", {}).get("id")
    except (KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Malformed webhook payload: {e}")

    logger.info(f"[WEBHOOK] Received — {repo} PR #{pr_number} action={action}")

    try:
        result = _run_pipeline(
            repo=repo,
            pr_number=pr_number,
            diff=None,
            post_comment_flag=True,
            installation_id=installation_id,
        )
        logger.info(f"[WEBHOOK] Processed — {repo} PR #{pr_number}")
        return {
            "status": "reviewed",
            "repo": repo,
            "pr_number": pr_number,
            "issues": len(result["review"].get("issues", [])),
            "comment_url": result.get("comment_url"),
        }
    except HTTPException as e:
        logger.error(f"[WEBHOOK] Review failed for {repo} PR #{pr_number}: {e.detail}")
        return {"status": "error", "detail": e.detail}
    except Exception as e:
        logger.error(f"[WEBHOOK] Unexpected error for {repo} PR #{pr_number}: {e}")
        return {"status": "error", "detail": str(e)}
