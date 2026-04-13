import time
import os
import logging
import httpx
import jwt

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"
TIMEOUT = 15


def _get_app_credentials() -> tuple:
    app_id = os.getenv("GITHUB_APP_ID", "").strip()
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private-key.pem")
    if os.path.exists(key_path):
        with open(key_path) as f:
            private_key = f.read().strip()
    else:
        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n").strip()
    if not app_id or not private_key:
        raise RuntimeError("GITHUB_APP_ID and private-key.pem must be set")
    return app_id, private_key


def generate_jwt() -> str:
    app_id, private_key = _get_app_credentials()
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + (10 * 60), "iss": app_id}
    return jwt.encode(payload, private_key, algorithm="RS256")


def get_installation_token(installation_id: int) -> str:
    token = generate_jwt()
    url = f"{BASE_URL}/app/installations/{installation_id}/access_tokens"
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["token"]
    except Exception as e:
        logger.error(f"Failed to get installation token: {e}")
        raise RuntimeError(f"Could not get installation token: {e}")


def get_app_headers(installation_id: int) -> dict:
    token = get_installation_token(installation_id)
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }