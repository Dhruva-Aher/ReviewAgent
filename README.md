# ReviewAgent

Autonomous PR review agent with persistent belief system.

## Setup

```bash
git clone <repo>
cd review-agent

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY and GITHUB_TOKEN
```

## Run

```bash
export $(cat .env | xargs)
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Endpoints

### POST /review
Review a PR. Fetches diff from GitHub if not provided.

**With diff (no GitHub token needed):**
```bash
curl -s -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/repo",
    "pr_number": 42,
    "diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1,5 +1,10 @@\n import os\n+import subprocess\n \n def run_command(cmd):\n-    return os.system(cmd)\n+    user_input = cmd\n+    result = subprocess.run(user_input, shell=True, capture_output=True)\n+    password = \"hardcoded_secret_123\"\n+    query = \"SELECT * FROM users WHERE id=\" + user_input\n+    return result.stdout",
    "post_comment": false
  }'
```

**From GitHub (fetches diff automatically):**
```bash
curl -s -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/repo",
    "pr_number": 42,
    "post_comment": true
  }'
```

### GET /beliefs
```bash
curl http://localhost:8000/beliefs
```

### POST /beliefs
```bash
curl -s -X POST http://localhost:8000/beliefs \
  -H "Content-Type: application/json" \
  -d '{"type": "rules", "value": "All async functions must handle cancellation"}'
```

---

## Example Output

```json
{
  "repo": "owner/repo",
  "pr_number": 42,
  "meta": {},
  "review": {
    "issues": [
      {
        "type": "bug",
        "severity": "high",
        "message": "run_command passes user_input directly to subprocess.run with shell=True — arbitrary shell injection is possible",
        "suggestion": "Use a list argument instead: subprocess.run(['cmd', arg], shell=False)",
        "reference": "All API endpoints must validate and sanitize input before processing"
      },
      {
        "type": "bug",
        "severity": "high",
        "message": "password = 'hardcoded_secret_123' on line 7 — credential hardcoded in source",
        "suggestion": "Load from environment: os.getenv('APP_PASSWORD')",
        "reference": "Secrets and credentials must never be hardcoded — use environment variables"
      },
      {
        "type": "bug",
        "severity": "high",
        "message": "SQL query built with string concatenation: 'SELECT * FROM users WHERE id=' + user_input — direct injection vector",
        "suggestion": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id=?', (user_input,))",
        "reference": "Database queries must never be constructed with string formatting (SQL injection risk)"
      }
    ],
    "summary": "This diff introduces three critical security vulnerabilities: shell injection via subprocess, a hardcoded credential, and SQL injection. None of these are acceptable for merge. Each violation also directly contradicts established team rules."
  },
  "comment": "## 🤖 ReviewAgent — `owner/repo` PR #42\n\n### Summary\n...",
  "comment_url": null,
  "beliefs_updated": true
}
```

---

## Belief System

Edit `beliefs.json` directly or use `POST /beliefs` to add rules and past decisions.
The agent loads beliefs at startup and references them during every review.
High-severity findings are automatically recorded as past decisions.

```json
{
  "rules": ["Never use bare except clauses"],
  "past_decisions": ["We use httpx over requests — decided for async compatibility"]
}
```
