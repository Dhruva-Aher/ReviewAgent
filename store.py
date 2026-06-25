import sqlite3
import logging
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("DB_PATH", "beliefs.db"))
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
    abs_path = DB_PATH.absolute()
    file_exists = DB_PATH.exists()
    cwd = os.getcwd()

    logger.info("====================================")
    logger.info("DATABASE DIAGNOSTICS")
    logger.info("====================================")
    logger.info(f"Database:\n{abs_path}")
    logger.info(f"Exists: {'yes' if file_exists else 'no'}")
    logger.info(f"Current working directory:\n{cwd}")

    if file_exists:
        try:
            with _get_conn() as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row["name"] for row in cursor]
                logger.info(f"Tables:\n{', '.join(tables)}")
        except Exception as e:
            logger.info(f"Tables:\nFailed to read tables: {e}")
    else:
        logger.info("Tables:\n(database file does not exist yet)")
    logger.info("====================================")

    with _get_conn() as conn:
        with conn:
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
