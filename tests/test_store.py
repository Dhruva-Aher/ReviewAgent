from store import load_review_history, append_review_history

def test_load_empty(tmp_db):
    rh = load_review_history()
    assert rh == []

def test_append_review_history(tmp_db):
    append_review_history("DECISION: Approved ignoring pylint for tests", "test/repo", 1)
    rh = load_review_history("test/repo")
    assert len(rh) == 1
    assert rh[0]["text"] == "DECISION: Approved ignoring pylint for tests"
    assert rh[0]["pr_number"] == 1
