"""
Project Glass X - X API client using Authlib (OAuth1) + httpx.

Clean, modern, works on Python 3.13+.
"""

import os
from typing import Any

import httpx
from authlib.integrations.httpx_client import OAuth1Client
from dotenv import load_dotenv

load_dotenv()

X_API_BASE = "https://api.x.com/2"


def _get_oauth1_client() -> OAuth1Client | None:
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        return None

    return OAuth1Client(
        client_id=api_key,
        client_secret=api_secret,
        token=access_token,
        token_secret=access_secret,
    )


def verify_credentials() -> dict[str, Any]:
    """Test the stored credentials and return basic profile info."""
    client = _get_oauth1_client()
    if client is None:
        return {"ok": False, "error": "No X API credentials configured in .env"}

    try:
        resp = client.get(
            f"{X_API_BASE}/users/me",
            params={"user.fields": "public_metrics,verified"}
        )
        if resp.status_code != 200:
            return {"ok": False, "error": f"X API returned {resp.status_code}: {resp.text[:200]}"}

        user = resp.json().get("data", {})
        metrics = user.get("public_metrics", {})
        return {
            "ok": True,
            "username": user.get("username"),
            "name": user.get("name"),
            "followers": metrics.get("followers_count", 0),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def post_tweet(text: str, media_paths: list[str] | None = None) -> dict[str, Any]:
    """
    Create a post via X API v2.
    Media support is stubbed for the absolute first working version.
    """
    client = _get_oauth1_client()
    if client is None:
        raise RuntimeError("X API credentials missing. Add them in Settings.")

    payload = {"text": text}

    # TODO: implement media upload in next iteration using the v1.1 media endpoint
    # For now we focus on the core loop working with text posts.

    resp = client.post(f"{X_API_BASE}/tweets", json=payload)

    if resp.status_code != 201:
        raise RuntimeError(f"Failed to post tweet: {resp.status_code} - {resp.text}")

    data = resp.json().get("data", {})
    return {
        "id": data.get("id"),
        "text": data.get("text"),
        "url": f"https://x.com/i/web/status/{data.get('id')}",
    }


def get_user_timeline(limit: int = 10) -> list[dict]:
    """Fetch recent posts for analytics (basic version)."""
    client = _get_oauth1_client()
    if client is None:
        return []

    try:
        # First get our own user id
        me = client.get(f"{X_API_BASE}/users/me")
        user_id = me.json()["data"]["id"]

        resp = client.get(
            f"{X_API_BASE}/users/{user_id}/tweets",
            params={
                "max_results": min(limit, 100),
                "tweet.fields": "public_metrics,created_at",
            }
        )
        if resp.status_code != 200:
            return []

        return resp.json().get("data", [])
    except Exception:
        return []
