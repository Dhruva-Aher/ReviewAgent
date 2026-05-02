import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path("beliefs.db")
LEGACY_JSON_PATH = Path("beliefs.json")

@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with _get_conn() as conn:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS beliefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT,
                    type TEXT,
                    value TEXT,
                    created_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS review_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT,
                    pr_number INTEGER,
                    reviewed_at TEXT,
                    issue_count INTEGER,
                    high_count INTEGER
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_hits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_text TEXT,
                    repo TEXT,
                    hit_count INTEGER DEFAULT 0,
                    UNIQUE(rule_text, repo)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT,
                    pr_number INTEGER,
                    agent_name TEXT,
                    duration_ms INTEGER,
                    skipped BOOLEAN,
                    issues_found INTEGER,
                    ran_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS pr_status_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT,
                    pr_number INTEGER,
                    comment_id INTEGER,
                    posted_at TEXT
                )
            ''')

    if LEGACY_JSON_PATH.exists():
        logger.info("Migrating beliefs.json to SQLite")
        try:
            with open(LEGACY_JSON_PATH, "r") as f:
                data = json.loads(f.read())

            # Migrate global rules/decisions
            global_rules = data.get("rules", [])
            global_decisions = data.get("past_decisions", [])
            _migrate_insert(None, "rule", global_rules)
            _migrate_insert(None, "decision", global_decisions)

            # Migrate repo specific
            repos = data.get("repos", {})
            for r, rdata in repos.items():
                _migrate_insert(r, "rule", rdata.get("rules", []))
                _migrate_insert(r, "decision", rdata.get("past_decisions", []))

            LEGACY_JSON_PATH.rename(LEGACY_JSON_PATH.with_suffix(".json.bak"))
            logger.info("Migration complete.")
        except Exception as e:
            logger.error(f"Failed to migrate beliefs.json: {e}")

def _migrate_insert(repo, btype, values):
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        with conn:
            for v in values:
                conn.execute(
                    "INSERT INTO beliefs (repo, type, value, created_at) VALUES (?, ?, ?, ?)",
                    (repo, btype, v, now)
                )

def load(repo=None) -> dict:
    result = {"rules": [], "past_decisions": []}
    with _get_conn() as conn:
        # Load global
        cursor = conn.execute("SELECT type, value, created_at FROM beliefs WHERE repo IS NULL")
        for row in cursor:
            k = "rules" if row["type"] == "rule" else "past_decisions"
            result[k].append({"value": row["value"], "created_at": row["created_at"]})

        # Load repo
        if repo:
            cursor = conn.execute("SELECT type, value, created_at FROM beliefs WHERE repo = ?", (repo,))
            for row in cursor:
                k = "rules" if row["type"] == "rule" else "past_decisions"
                result[k].append({"value": row["value"], "created_at": row["created_at"]})
    return result

def save(data: dict, repo=None) -> None:
    pass

def append_decision(decision: str, repo: str = None) -> None:
    if not decision or not decision.strip():
        return
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        curr = conn.execute("SELECT 1 FROM beliefs WHERE (repo IS ? OR repo = ?) AND type = 'decision' AND value = ?",
                            (repo, repo, decision)).fetchone()
        if not curr:
            with conn:
                conn.execute("INSERT INTO beliefs (repo, type, value, created_at) VALUES (?, ?, ?, ?)",
                             (repo, "decision", decision, now))

def _add_rule(rule: str, repo: str = None) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        curr = conn.execute("SELECT 1 FROM beliefs WHERE (repo IS ? OR repo = ?) AND type = 'rule' AND value = ?",
                            (repo, repo, rule)).fetchone()
        if not curr:
            with conn:
                conn.execute("INSERT INTO beliefs (repo, type, value, created_at) VALUES (?, ?, ?, ?)",
                             (repo, "rule", rule, now))
            return True
    return False

def format_for_prompt(beliefs: dict, repo: str = None) -> str:
    rules = beliefs.get("rules", [])
    decisions = beliefs.get("past_decisions", [])

    parts = []
    if rules:
        rules_text = "\\n".join(f"  - {r['value']}" if isinstance(r, dict) else f"  - {r}" for r in rules)
        parts.append(f"RULES:\\n{rules_text}")

    if decisions:
        now = datetime.now(timezone.utc)
        valid_decisions = []
        for d in decisions:
            val = d['value'] if isinstance(d, dict) else d
            created_at_str = d.get('created_at') if isinstance(d, dict) else None

            try:
                if created_at_str:
                    # Handle Z suffix for fromisoformat in 3.10
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = now
            except ValueError:
                dt = now

            days_old = (now - dt).days
            if days_old > 180:
                continue
            if days_old > 90:
                val = f"[HISTORICAL - may be outdated] {val}"
            valid_decisions.append(val)

        if valid_decisions:
            decisions_text = "\\n".join(f"  - {d}" for d in valid_decisions)
            parts.append(f"PAST DECISIONS:\\n{decisions_text}")

    return "\\n\\n".join(parts) if parts else "No beliefs loaded."

def log_review(repo, pr_number, issue_count, high_count):
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        with conn:
            conn.execute('''
                INSERT INTO review_log (repo, pr_number, reviewed_at, issue_count, high_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (repo, pr_number, now, issue_count, high_count))

def log_rule_hit(rule_text, repo):
    with _get_conn() as conn:
        with conn:
            conn.execute('''
                INSERT INTO rule_hits (rule_text, repo, hit_count)
                VALUES (?, ?, 1)
                ON CONFLICT(rule_text, repo) DO UPDATE SET hit_count = hit_count + 1
            ''', (rule_text, repo))

def log_agent_run(repo, pr_number, agent_name, duration_ms, skipped, issues_found):
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        with conn:
            conn.execute('''
                INSERT INTO agent_runs (repo, pr_number, agent_name, duration_ms, skipped, issues_found, ran_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (repo, pr_number, agent_name, duration_ms, skipped, issues_found, now))

def get_stats():
    stats = {
        "total_reviews": 0,
        "top_violated_rules": [],
        "reviews_by_repo": {}
    }
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM review_log").fetchone()
        stats["total_reviews"] = row[0] if row else 0

        cursor = conn.execute("SELECT rule_text, SUM(hit_count) as total_hits FROM rule_hits GROUP BY rule_text ORDER BY total_hits DESC LIMIT 5")
        stats["top_violated_rules"] = [dict(r) for r in cursor]

        cursor = conn.execute("SELECT repo, COUNT(*) as c FROM review_log GROUP BY repo")
        stats["reviews_by_repo"] = {r["repo"]: r["c"] for r in cursor}

    return stats
