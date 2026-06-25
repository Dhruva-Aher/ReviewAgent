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
            # We keep beliefs for backward compatibility during migration
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
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT,
                    kind TEXT,
                    text TEXT,
                    category TEXT DEFAULT 'maintainability',
                    priority TEXT DEFAULT 'medium',
                    scope TEXT DEFAULT 'repository',
                    enabled BOOLEAN DEFAULT 1,
                    source TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS review_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT,
                    pr_number INTEGER,
                    text TEXT,
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
    
    _migrate_json()
    _migrate_v2()

def _migrate_json():
    if LEGACY_JSON_PATH.exists():
        logger.info("Migrating beliefs.json to SQLite")
        try:
            with open(LEGACY_JSON_PATH, "r") as f:
                data = json.loads(f.read())

            global_rules = data.get("rules", [])
            global_decisions = data.get("past_decisions", [])
            _migrate_insert(None, "rule", global_rules)
            _migrate_insert(None, "decision", global_decisions)

            repos = data.get("repos", {})
            for r, rdata in repos.items():
                _migrate_insert(r, "rule", rdata.get("rules", []))
                _migrate_insert(r, "decision", rdata.get("past_decisions", []))

            LEGACY_JSON_PATH.rename(LEGACY_JSON_PATH.with_suffix(".json.bak"))
            logger.info("JSON Migration complete.")
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

def _migrate_v2():
    """Migrates from beliefs table to knowledge and review_history"""
    with _get_conn() as conn:
        # Check if we already migrated
        count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        count_rh = conn.execute("SELECT COUNT(*) FROM review_history").fetchone()[0]
        if count > 0 or count_rh > 0:
            return

        cursor = conn.execute("SELECT * FROM beliefs")
        rows = cursor.fetchall()
        if not rows:
            return
            
        logger.info(f"Migrating {len(rows)} rows from beliefs to v2 schema...")
        now = datetime.now(timezone.utc).isoformat()
        
        with conn:
            for r in rows:
                repo = r["repo"]
                btype = r["type"]
                val = r["value"]
                created_at = r["created_at"]
                
                if btype == "rule":
                    scope = "global" if not repo else "repository"
                    conn.execute('''
                        INSERT INTO knowledge (repo, kind, text, category, priority, scope, enabled, source, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (repo, "rule", val, "maintainability", "medium", scope, 1, "migration", created_at, now))
                elif btype == "decision":
                    if "[PR #" in val or val.startswith("PR #"):
                        # Attempt to extract PR number if possible, else 0
                        import re
                        match = re.search(r'PR #(\d+)', val)
                        pr_num = int(match.group(1)) if match else 0
                        conn.execute('''
                            INSERT INTO review_history (repo, pr_number, text, created_at)
                            VALUES (?, ?, ?, ?)
                        ''', (repo, pr_num, val, created_at))
                    else:
                        scope = "global" if not repo else "repository"
                        conn.execute('''
                            INSERT INTO knowledge (repo, kind, text, category, priority, scope, enabled, source, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (repo, "architecture", val, "maintainability", "medium", scope, 1, "migration", created_at, now))

def load(repo=None) -> list:
    results = []
    with _get_conn() as conn:
        # Load global
        cursor = conn.execute("SELECT * FROM knowledge WHERE repo IS NULL AND enabled = 1")
        for row in cursor:
            results.append(dict(row))
            
        # Load repo
        if repo:
            cursor = conn.execute("SELECT * FROM knowledge WHERE repo = ? AND enabled = 1", (repo,))
            for row in cursor:
                results.append(dict(row))
    return results

def load_review_history(repo=None) -> list:
    results = []
    with _get_conn() as conn:
        if repo:
            cursor = conn.execute("SELECT * FROM review_history WHERE repo = ? ORDER BY created_at DESC", (repo,))
        else:
            cursor = conn.execute("SELECT * FROM review_history ORDER BY created_at DESC")
        for row in cursor:
            results.append(dict(row))
    return results

def append_review_history(text: str, repo: str = None, pr_number: int = 0) -> None:
    if not text or not text.strip():
        return
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        with conn:
            conn.execute("INSERT INTO review_history (repo, pr_number, text, created_at) VALUES (?, ?, ?, ?)",
                         (repo, pr_number, text, now))

def add_knowledge(repo: str, kind: str, text: str, category: str = "maintainability", priority: str = "medium", scope: str = "repository") -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        with conn:
            cur = conn.execute('''
                INSERT INTO knowledge (repo, kind, text, category, priority, scope, enabled, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (repo, kind, text, category, priority, scope, 1, "api", now, now))
            return cur.lastrowid

def format_for_prompt(knowledge_items: list, repo: str = None) -> str:
    rules_critical = []
    rules_high = []
    rules_medium = []
    rules_low = []
    architecture = []
    
    for k in knowledge_items:
        text = k["text"]
        if k["kind"] == "rule":
            pri = k.get("priority", "medium").lower()
            if pri == "critical":
                rules_critical.append(text)
            elif pri == "high":
                rules_high.append(text)
            elif pri == "low":
                rules_low.append(text)
            else:
                rules_medium.append(text)
        elif k["kind"] == "architecture":
            architecture.append(text)

    parts = []
    if rules_critical or rules_high or rules_medium or rules_low:
        parts.append("Repository Engineering Rules")
        if rules_critical:
            parts.append("Critical\\n" + "\\n".join(f"- {r}" for r in rules_critical))
        if rules_high:
            parts.append("High\\n" + "\\n".join(f"- {r}" for r in rules_high))
        if rules_medium:
            parts.append("Medium\\n" + "\\n".join(f"- {r}" for r in rules_medium))
        if rules_low:
            parts.append("Low\\n" + "\\n".join(f"- {r}" for r in rules_low))
            
    if architecture:
        parts.append("Architecture Decisions\\n" + "\\n".join(f"- {a}" for a in architecture))

    # Add Context section
    parts.append(f"Context\\nRepository: {repo or 'Unknown'}\\nLanguage: Python\\nFramework: None")
    
    return "\\n\\n".join(parts)

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
