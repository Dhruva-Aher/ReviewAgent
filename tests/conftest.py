import pytest
import sqlite3
import json
import os
from unittest.mock import patch, AsyncMock
from store import init_db

@pytest.fixture
def sample_diff():
    return """diff --git a/main.py b/main.py
index e69de29..d95f3ad 100644
--- a/main.py
+++ b/main.py
@@ -1,3 +1,6 @@
+import os
+import json
+
 def process_data(data):
-    pass
+    return json.loads(data)
diff --git a/utils.py b/utils.py
index e69de29..d95f3ad 100644
--- a/utils.py
+++ b/utils.py
@@ -0,0 +1,5 @@
+def helper():
+    print("help")
+    return True
diff --git a/config.py b/config.py
index e69de29..d95f3ad 100644
--- a/config.py
+++ b/config.py
@@ -0,0 +1,3 @@
+def get_password():
+    return "secret_token_123"
"""

@pytest.fixture
def sample_context(sample_diff):
    from agents.base import AgentContext
    return AgentContext(
        diff=sample_diff,
        beliefs_text="RULES:\\n  - No plain text passwords",
        repo="test-owner/test-repo",
        pr_number=42,
        pr_title="Add new features",
        pr_description="This PR adds some features",
        changed_files=["main.py", "utils.py", "config.py"],
        config={}
    )

@pytest.fixture
def mock_groq():
    mock_call = AsyncMock()
    mock_call.return_value = json.dumps({
        "comments": [{"type": "security", "severity": "high", "message": "Do not commit passwords", "suggestion": "Use env var", "reference": None, "confidence": 100, "file": "config.py", "line": 2}],
        "issues": [{"type": "security", "severity": "high", "message": "Do not commit passwords", "suggestion": "Use env var", "reference": None, "confidence": 100, "file": "config.py", "line": 2}],
        "summary": "Found security issues.",
        "confidence": 85
    })
    
    with patch("reviewer._call_groq", mock_call), \
         patch("agents.impl._call_groq", mock_call), \
         patch("os.getenv", side_effect=lambda k, *d: "test-key" if k == "GROQ_API_KEY" else os.environ.get(k, d[0] if d else None)):
        yield mock_call

@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test_beliefs.db"
    os.environ["DB_PATH"] = str(db_path)
    # Ensure init_db is called using the new path
    import store
    store.DB_PATH = db_path
    
    init_db()
    yield str(db_path)
