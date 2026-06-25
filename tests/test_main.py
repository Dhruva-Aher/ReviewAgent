import pytest
from fastapi.testclient import TestClient
import hmac
import hashlib
from unittest.mock import patch, AsyncMock
import os
from main import app

# Ensure tmp_db is used
@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    pass

client = TestClient(app)

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_post_review():
    with patch("main.github.fetch_repo_config") as mock_fetch:
        mock_fetch.return_value = "version: 1\nrules:\n  - text: test rule"
        with patch("main._run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = {"comments": [], "confidence": 100}
            response = client.post("/review", json={"repo": "owner/repo", "pr_number": 1})
            assert response.status_code == 200
            mock_pipeline.assert_called_once()

def test_post_webhook_valid_signature():
    with patch("main._run_pipeline", new_callable=AsyncMock) as mock_pipeline, \
         patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": "my_secret"}):
        payload = b'{"action": "opened", "pull_request": {"number": 1}, "repository": {"name": "repo", "owner": {"login": "owner"}}}'
        secret = b"my_secret"
        mac = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        signature = f"sha256={mac}"
        mock_pipeline.return_value = {
            "repo": "owner/repo",
            "pr_number": 1,
            "review": {"issues": [], "summary": "ok"},
            "comment": "",
            "comment_url": None,
            "beliefs_updated": False,
            "deduplicated": 0,
        }
        response = client.post(
            "/webhook",
            content=payload,
            headers={"X-Hub-Signature-256": signature, "X-GitHub-Event": "pull_request"}
        )
        assert response.status_code == 200
        mock_pipeline.assert_called_once()

def test_get_export_knowledge():
    response = client.get("/export-knowledge")
    assert response.status_code == 200
    assert "error" in response.json() or "yaml" in response.json()

def test_get_stats():
    response = client.get("/stats")
    assert response.status_code == 200
    assert "total_reviews" in response.json()
