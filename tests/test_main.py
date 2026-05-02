import pytest
from fastapi.testclient import TestClient
import json
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

def test_get_beliefs():
    response = client.get("/beliefs")
    assert response.status_code == 200
    assert "rules" in response.json()
    assert "past_decisions" in response.json()

def test_post_beliefs():
    response = client.post("/beliefs", json={"type": "rules", "value": "New global rule"})
    assert response.status_code == 200
    assert "New global rule" in response.json()["beliefs"]["rules"]

def test_post_review():
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
        
        response = client.post(
            "/webhook",
            content=payload,
            headers={"X-Hub-Signature-256": signature, "X-GitHub-Event": "pull_request"}
        )
        assert response.status_code == 200
        mock_pipeline.assert_called_once()

def test_post_webhook_invalid_signature():
    with patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": "my_secret"}):
        response = client.post(
            "/webhook",
            content=b'{"action": "opened"}',
            headers={"X-Hub-Signature-256": "sha256=invalid", "X-GitHub-Event": "pull_request"}
        )
        assert response.status_code == 401

def test_get_stats():
    response = client.get("/stats")
    assert response.status_code == 200
    assert "total_reviews" in response.json()
