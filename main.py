import hmac
import hashlib
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import store as belief_store
import github
import reviewer
import formatter
import orchestrator
from rate_limiter import check_rate_limit
from agents.base import AgentContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("review_agent")

_knowledge: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    belief_store.init_db()
    global _knowledge
    _knowledge = belief_store.load()
    logger.info(
        f"ReviewAgent started — loaded {len(_knowledge)} active knowledge item(s)"
    )
    yield


app = FastAPI(
    title="ReviewAgent",
    description="Autonomous PR review agent with persistent knowledge system",
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


class AddKnowledgeRequest(BaseModel):
    kind: str
    text: str
    repo: Optional[str] = None
    category: str = "maintainability"
    priority: str = "medium"
    scope: str = "repository"

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in ("rule", "architecture"):
            raise ValueError("kind must be 'rule' or 'architecture'")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        return v
        
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ("critical", "high", "medium", "low"):
            raise ValueError("priority must be critical, high, medium, or low")
        return v
        
    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v not in ("global", "repository", "directory", "file"):
            raise ValueError("scope must be global, repository, directory, or file")
        return v


CONFIDENCE_THRESHOLD = int(os.getenv("CONFIDENCE_THRESHOLD", "60"))
MULTI_AGENT = os.getenv("MULTI_AGENT", "true").lower() != "false"

async def _run_pipeline(
    repo: str,
    pr_number: int,
    diff: Optional[str],
    post_comment_flag: bool,
    installation_id: int = None,
) -> dict:
    global _knowledge

    owner, repo_name = repo.split("/")
    meta = {}
    req_txt = None

    if not diff:
        logger.info(f"[FETCH] Fetching diff — {repo} PR #{pr_number}")
        diff = github.fetch_pr_diff(owner, repo_name, pr_number, installation_id)
        try:
            meta = github.fetch_pr_meta(owner, repo_name, pr_number, installation_id)
        except HTTPException:
            meta = {}

    # Try fetching requirements.txt
    try:
        req_txt = github.fetch_file_content(owner, repo_name, "requirements.txt", meta.get("head", ""), installation_id)
    except Exception:
        req_txt = None

    diff = diff.strip()
    if not diff:
        raise HTTPException(status_code=422, detail="Diff is empty — nothing to review")

    beliefs_text = belief_store.format_for_prompt(_knowledge, repo=repo)
    logger.info(f"[REVIEW] Starting — {repo} PR #{pr_number} ({len(diff)} chars)")

    # Parse changed files from diff
    changed_files = []
    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            changed_files.append(line[6:].strip())

    if MULTI_AGENT:
        context = AgentContext(
            diff=diff,
            beliefs_text=beliefs_text,
            repo=repo,
            pr_number=pr_number,
            pr_title=meta.get("title", ""),
            pr_description=meta.get("body", ""),
            changed_files=changed_files,
            config={"requirements_txt": req_txt}
        )
        agents_to_run = ["SecurityAgent", "ArchitectureAgent", "PerformanceAgent", "TestCoverageAgent", "DependencyAgent"]
        review_result = await orchestrator.run_multi_agent_review(context, agents_to_run)
    else:
        review_result = await reviewer.run_review(
            diff=diff,
            beliefs_text=beliefs_text,
            repo=repo,
            pr_number=pr_number,
        )

    original_issues = review_result.get("issues", [])
    filtered_issues = [i for i in original_issues if i.get("confidence", 100) >= CONFIDENCE_THRESHOLD]
    filtered_count = len(original_issues) - len(filtered_issues)
    if filtered_count > 0:
        logger.info(f"[FILTER] Filtered {filtered_count} issues below confidence threshold {CONFIDENCE_THRESHOLD}")
    review_result["issues"] = filtered_issues

    issue_count = len(filtered_issues)
    high_count = sum(1 for i in filtered_issues if i.get("severity") == "high")
    belief_store.log_review(repo, pr_number, issue_count, high_count)
    logger.info(f"[REVIEW] Complete — {repo} PR #{pr_number} — {issue_count} issue(s), {high_count} high severity")

    comment_body = formatter.to_github_comment(review_result, repo, pr_number)
    comment_url = None

    if post_comment_flag:
        logger.info(f"[GITHUB] Posting comment — {repo} PR #{pr_number}")

        inline_comments_posted = False
        if any(i.get("file") and i.get("line") for i in filtered_issues):
            try:
                comment_url = github.post_review_with_inline_comments(owner, repo_name, pr_number, review_result, installation_id)
                if comment_url:
                    logger.info(f"[GITHUB] Inline review posted — {comment_url}")
                    inline_comments_posted = True
            except Exception as e:
                logger.warning(f"Failed to post inline comments, falling back to regular comment. ({e})")

        if not inline_comments_posted:
            comment_url = github.post_comment(owner, repo_name, pr_number, comment_body, installation_id)
            if comment_url:
                logger.info(f"[GITHUB] Comment posted — {comment_url}")
            else:
                logger.warning("[GITHUB] Comment failed — review printed to console")

    high_issues = [i for i in filtered_issues if i.get("severity") == "high"]
    if high_issues:
        decision = (
            f"PR #{pr_number} in {repo}: flagged {len(high_issues)} "
            f"high-severity issue(s) — {high_issues[0]['message'][:80]}"
        )
        belief_store.append_review_history(decision, repo=repo, pr_number=pr_number)
        logger.info(f"[HISTORY] Appended high severity findings to review history for {repo} PR #{pr_number}")

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
        "knowledge_count": len(_knowledge),
        "mode": "github_app" if os.getenv("GITHUB_APP_ID") else "personal_token"
    }


@app.get("/knowledge")
def get_knowledge(repo: Optional[str] = None):
    return belief_store.load(repo=repo)


@app.post("/knowledge")
def add_knowledge(req: AddKnowledgeRequest):
    global _knowledge
    repo_msg = f" for repo {req.repo}" if req.repo else " globally"

    belief_store.add_knowledge(
        repo=req.repo,
        kind=req.kind,
        text=req.text,
        category=req.category,
        priority=req.priority,
        scope=req.scope
    )

    _knowledge = belief_store.load()
    logger.info(f"[KNOWLEDGE] Added {req.kind}{repo_msg}: {req.text[:60]}")
    return {"status": "added", "knowledge": belief_store.load(req.repo)}


@app.get("/review-history")
def get_review_history(repo: Optional[str] = None):
    return belief_store.load_review_history(repo=repo)


@app.post("/review")
async def review(req: ReviewRequest):
    logger.info(f"[MANUAL] Review triggered — {req.repo} PR #{req.pr_number}")
    return await _run_pipeline(
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

    # check rate limit
    if installation_id:
        check_rate_limit(installation_id)

    # auto-extract decisions from closed PRs into review_history
    if action == "closed" and pr.get("merged"):
        logger.info(f"[WEBHOOK] PR #{pr_number} merged in {repo}. Scanning for DECISION comments...")
        comments = github.fetch_pr_review_comments(owner, repo_name, pr_number, installation_id)
        found = 0
        for m in comments:
            msg = m.strip()
            if msg.startswith("DECISION:"):
                decision_text = msg[len("DECISION:"):].strip()
                if decision_text:
                    belief_store.append_review_history(f"DECISION: {decision_text}", repo=repo, pr_number=pr_number)
                    found += 1
        return {"status": "merged_processed", "decisions_extracted": found}

    if action not in ("opened", "synchronize"):
        logger.info(f"[WEBHOOK] Ignored PR action: {action}")
        return {"status": "ignored", "action": action}

    logger.info(f"[WEBHOOK] Received — {repo} PR #{pr_number} action={action}")

    try:
        result = await _run_pipeline(
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

@app.get("/stats")
def get_stats():
    return belief_store.get_stats()
