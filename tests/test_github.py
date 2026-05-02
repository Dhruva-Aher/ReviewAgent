import pytest
from unittest.mock import patch, MagicMock
from github import fetch_pr_review_comments, post_review_with_inline_comments, post_comment

@pytest.fixture(autouse=True)
def set_github_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

def test_fetch_pr_review_comments():
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"body": "Comment 1"}, {"body": "Comment 2"}]
        mock_get.return_value = mock_resp

        comments = fetch_pr_review_comments("owner", "repo", 1)
        assert len(comments) == 4 # Called twice (commits and issues), returning 2 each
        assert "Comment 1" in comments

def test_post_review_with_inline_comments_success():
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html_url": "http://example.com"}
        mock_post.return_value = mock_resp

        url = post_review_with_inline_comments(
            "owner", "repo", 1,
            {"issues": [{"file": "main.py", "line": 1, "message": "msg", "suggestion": "sug", "type": "bug", "severity": "high"}]}
        )
        assert url == "http://example.com"
        mock_post.assert_called_once()

def test_post_review_with_inline_comments_fallback():
    with patch("httpx.post") as mock_post:
        mock_resp_422 = MagicMock()
        mock_resp_422.status_code = 422

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {"html_url": "http://example.com/fallback"}

        mock_post.side_effect = [mock_resp_422, mock_resp_200]

        url = post_review_with_inline_comments(
            "owner", "repo", 1,
            {"issues": [{"file": "main.py", "line": 1, "message": "msg", "suggestion": "sug", "type": "bug", "severity": "high"}]}
        )
        assert url == "http://example.com/fallback"
        assert mock_post.call_count == 2

def test_post_comment():
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html_url": "http://example.com/comment"}
        mock_post.return_value = mock_resp

        url = post_comment("owner", "repo", 1, "Body")
        assert url == "http://example.com/comment"
