"""Meta Instagram OAuth service — Instagram Login (Business Login for Instagram).

Handles the OAuth 2.0 code exchange flow using the Instagram Login API.
In mock mode the actual HTTP calls are skipped.

Required Meta App permissions (Instagram Login scopes):
  - instagram_business_basic          – profile info
  - instagram_business_content_publish – publish posts
  - instagram_business_manage_comments – read/manage comments
  - instagram_business_manage_insights – media insights

Required setup (outside this codebase):
  1. Go to developers.facebook.com and open your app.
  2. Under "Products", add the "Instagram" product (Instagram Login for Business).
  3. Under Instagram → Instagram Login for Business:
       - Add the callback URI in "Valid OAuth Redirect URIs".
       - Request the scopes listed above.
  4. Set META_APP_ID, META_APP_SECRET, META_OAUTH_REDIRECT_URI in Vercel env vars.
  5. The Instagram account must be a Professional (Business or Creator) account.
     No Facebook Page is required with Instagram Login.
"""
from __future__ import annotations

import urllib.parse
from typing import Optional

import httpx

from ..settings import settings

# Instagram Login API endpoints
AUTH_BASE = "https://api.instagram.com/oauth/authorize"
IG_TOKEN_URL = "https://api.instagram.com/oauth/access_token"        # short-lived (POST)
IG_LONG_LIVED_URL = "https://graph.instagram.com/access_token"       # long-lived (GET)
IG_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"  # refresh (GET)
GRAPH_BASE = "https://graph.instagram.com/v21.0"                     # Graph API for IG Login tokens

# Instagram Login scopes for Business Login
_IG_SCOPES = (
    "instagram_business_basic,"
    "instagram_business_content_publish,"
    "instagram_business_manage_comments,"
    "instagram_business_manage_insights"
)


def build_oauth_redirect_url(state: Optional[str] = None) -> str:
    """Return the Instagram OAuth authorization URL the user must visit."""
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
        "scope": _IG_SCOPES,
        "response_type": "code",
    }
    if state:
        params["state"] = state
    return f"{AUTH_BASE}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """Exchange an Instagram OAuth authorization code for a long-lived token.

    Step 1: POST to api.instagram.com/oauth/access_token  → short-lived token
    Step 2: GET  graph.instagram.com/access_token         → long-lived token (~60 days)

    Returns a dict with keys: access_token, token_type, expires_in.
    Raises RuntimeError on failure.
    """
    if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
        return {
            "access_token": "MOCK_ACCESS_TOKEN",
            "token_type": "bearer",
            "expires_in": 5183944,
            "mock": True,
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: short-lived token via POST (Instagram Login requirement)
        resp = await client.post(
            IG_TOKEN_URL,
            data={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Instagram short-lived token exchange failed: {resp.text}")
        short_data = resp.json()
        short_token = short_data.get("access_token")
        if not short_token:
            raise RuntimeError(f"No access_token in Instagram token response: {short_data}")

        # Step 2: exchange for a long-lived token (~60 days)
        resp2 = await client.get(
            IG_LONG_LIVED_URL,
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.META_APP_SECRET,
                "access_token": short_token,
            },
        )
        if resp2.status_code != 200:
            raise RuntimeError(f"Instagram long-lived token exchange failed: {resp2.text}")
        return resp2.json()


async def refresh_long_lived_token(access_token: str) -> dict:
    """Refresh an active long-lived Instagram user access token before it expires.

    Must be called while the token is still valid (not yet expired).
    """
    if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
        return {
            "access_token": "REFRESHED_MOCK_ACCESS_TOKEN",
            "token_type": "bearer",
            "expires_in": 5183944,
            "mock": True,
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            IG_REFRESH_URL,
            params={
                "grant_type": "ig_refresh_token",
                "access_token": access_token,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Instagram token refresh failed: {resp.text}")
        return resp.json()


async def get_instagram_user_id(access_token: str) -> Optional[str]:
    """Fetch the Instagram user ID (numeric) from the Instagram Login token.

    With Instagram Login (Business Login for Instagram), no Facebook Page lookup
    is needed. The token itself is tied to the Instagram Professional account.
    Returns the numeric Instagram user_id string.
    """
    if settings.USE_MOCK:
        return "MOCK_IG_USER_ID"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me",
            params={
                "fields": "user_id,username,account_type,name",
                "access_token": access_token,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch Instagram user info: {resp.text}")
        data = resp.json()
        user_id = data.get("user_id") or data.get("id")
        if not user_id:
            raise RuntimeError(
                f"Instagram /me response did not contain user_id. "
                f"Ensure the account is a Professional (Business or Creator) account. "
                f"Response: {data}"
            )
        return str(user_id)
