import os
import json
from datetime import datetime, timedelta, timezone
from store import load, append_decision, format_for_prompt, _add_rule

def test_load_empty(tmp_db):
    beliefs = load()
    assert beliefs["rules"] == []
    assert beliefs["past_decisions"] == []

def test_save_and_load_round_trip(tmp_db):
    _add_rule("Always use typing", None)
    _add_rule("No print statements in this repo", "test/repo")

    b_global = load()
    assert len(b_global["rules"]) == 1
    assert "Always use typing" in b_global["rules"][0]["value"]

    b_repo = load("test/repo")
    assert len(b_repo["rules"]) == 2

def test_append_decision(tmp_db):
    append_decision("Approved ignoring pylint for tests", "test/repo")
    b = load("test/repo")
    assert len(b["past_decisions"]) == 1
    assert b["past_decisions"][0]["value"] == "Approved ignoring pylint for tests"

def test_format_for_prompt_historical_and_exclusion(tmp_db):
    from store import _get_conn
    with _get_conn() as conn:
        with conn:
            # Add new belief
            conn.execute("INSERT INTO beliefs (type, value, created_at) VALUES (?, ?, ?)",
                         ("rule", "New rule", datetime.now(timezone.utc).isoformat()))

            # Add 100-day old belief
            old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
            conn.execute("INSERT INTO beliefs (type, value, created_at) VALUES (?, ?, ?)",
                         ("decision", "Old decision", old_date))

            # Add 200-day old belief
            ancient_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
            conn.execute("INSERT INTO beliefs (type, value, created_at) VALUES (?, ?, ?)",
                         ("decision", "Ancient decision", ancient_date))

    b = load()
    prompt_lines = format_for_prompt(b)

    # Excludes entries > 180 days
    assert "Ancient decision" not in prompt_lines

    # Prefixes [HISTORICAL] for 90-day-old entries
    assert "New rule" in prompt_lines
    assert "[HISTORICAL - may be outdated] Old decision" in prompt_lines

def test_beliefs_json_migration(tmp_db, tmp_path):
    json_path = tmp_path / "beliefs.json"
    with open(json_path, 'w') as f:
        json.dump({"rules": ["Migrated rule"]}, f)

    import store
    store.LEGACY_JSON_PATH = json_path

    store.init_db()

    # Verify data in SQLite
    b = store.load()
    assert "Migrated rule" in b["rules"][0]["value"]

    # Verify beliefs.json.bak exists and original is gone
    assert os.path.exists(f"{str(json_path)}.bak")
    assert not os.path.exists(str(json_path))
