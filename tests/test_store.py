from datetime import datetime, timezone
from store import load, load_review_history, append_review_history, format_for_prompt, add_knowledge, _get_conn

def test_load_empty(tmp_db):
    knowledge = load()
    assert knowledge == []
    
    rh = load_review_history()
    assert rh == []

def test_save_and_load_round_trip(tmp_db):
    add_knowledge(None, "rule", "Always use typing")
    add_knowledge("test/repo", "rule", "No print statements in this repo")

    k_global = load()
    assert len(k_global) == 1
    assert "Always use typing" in k_global[0]["text"]

    k_repo = load("test/repo")
    assert len(k_repo) == 2

def test_append_review_history(tmp_db):
    append_review_history("DECISION: Approved ignoring pylint for tests", "test/repo", 1)
    rh = load_review_history("test/repo")
    assert len(rh) == 1
    assert rh[0]["text"] == "DECISION: Approved ignoring pylint for tests"
    assert rh[0]["pr_number"] == 1

def test_format_for_prompt(tmp_db):
    add_knowledge(None, "rule", "Critical rule", priority="critical")
    add_knowledge(None, "rule", "High rule", priority="high")
    add_knowledge(None, "rule", "Medium rule", priority="medium")
    add_knowledge(None, "architecture", "Use sqlite")
    
    k = load()
    prompt_lines = format_for_prompt(k, repo="test/repo")

    assert "Repository Engineering Rules" in prompt_lines
    assert "Critical\\n- Critical rule" in prompt_lines
    assert "High\\n- High rule" in prompt_lines
    assert "Medium\\n- Medium rule" in prompt_lines
    assert "Architecture Decisions\\n- Use sqlite" in prompt_lines
    assert "Context\\nRepository: test/repo" in prompt_lines

def test_beliefs_v2_migration(tmp_db, tmp_path):
    # Insert old data into beliefs manually
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
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO beliefs (repo, type, value, created_at) VALUES (?, ?, ?, ?)",
                         (None, "rule", "Old rule", now))
            conn.execute("INSERT INTO beliefs (repo, type, value, created_at) VALUES (?, ?, ?, ?)",
                         ("test/repo", "decision", "Old decision", now))
            conn.execute("INSERT INTO beliefs (repo, type, value, created_at) VALUES (?, ?, ?, ?)",
                         ("test/repo", "decision", "[PR #42] Decided to do X", now))

    import store
    store._migrate_v2()

    # Verify data in SQLite
    k = store.load()
    assert len(k) == 1
    assert "Old rule" in k[0]["text"]
    assert k[0]["kind"] == "rule"
    
    k_repo = store.load("test/repo")
    assert len(k_repo) == 2
    # One is global old rule, one is repo specific old decision -> architecture
    arch_item = next(item for item in k_repo if item["kind"] == "architecture")
    assert arch_item["text"] == "Old decision"

    rh = store.load_review_history("test/repo")
    assert len(rh) == 1
    assert rh[0]["text"] == "[PR #42] Decided to do X"
    assert rh[0]["pr_number"] == 42
