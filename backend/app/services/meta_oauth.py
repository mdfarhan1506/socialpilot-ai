"""Meta Instagram OAuth service — Instagram API with Unified Login.

Handles the OAuth 2.0 code exchange flow using Meta's official Unified Login architecture
(Facebook Login for Business, marked Instagram Login Compatible).

Supports direct login with Instagram credentials without requiring a Facebook Page.

API Architecture:
  - Auth dialog: https://www.facebook.com/v19.0/dialog/oauth (prompt=login)
  - Token exchange: https://graph.facebook.com/v19.0/oauth/access_token
  - Account discovery: https://graph.facebook.com/v19.0/me/assigned_instagram_accounts
  - Direct profile fallback: https://graph.facebook.com/v19.0/me or /me/accounts
"""
from __future__ import annotations

import urllib.parse
from typing import Optional

import httpx

from ..settings import settings

# Meta OAuth & Graph API endpoints
AUTH_BASE = "https://www.facebook.com/v19.0/dialog/oauth"
GRAPH_BASE = "https://graph.facebook.com/v19.0"

# Standard permission scopes for Instagram Unified Login
_IG_SCOPES = (
    "instagram_basic,"
    "instagram_content_publish,"
    "instagram_manage_comments,"
    "instagram_manage_insights"
)


def build_oauth_redirect_url(state: Optional[str] = None) -> str:
    """Return the Meta OAuth authorization URL configured for direct Instagram login."""
    redirect_uri = settings.META_OAUTH_REDIRECT_URI.strip()
    params = {
        "client_id": settings.META_APP_ID.strip(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        # prompt=login forces the prompt to explicitly display both Instagram & Facebook login options
        "prompt": "login",
    }
    # If a config_id is provided in settings, Meta uses the server-side configuration bundle
    if settings.META_CONFIG_ID:
        params["config_id"] = settings.META_CONFIG_ID
    else:
        params["scope"] = _IG_SCOPES

    if state:
        params["state"] = state
    return f"{AUTH_BASE}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """Exchange an OAuth authorization code for an access token.

    Calls GET https://graph.facebook.com/v19.0/oauth/access_token
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
        # Step 1: exchange authorization code for access token
        # Clean the authorization code in case of URL fragments (e.g. #_=_ added by Meta)
        clean_code = code.split("#")[0].strip() if code else ""
        redirect_uri = settings.META_OAUTH_REDIRECT_URI.strip()

        resp = await client.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "client_id": settings.META_APP_ID.strip(),
                "client_secret": settings.META_APP_SECRET.strip(),
                "redirect_uri": redirect_uri,
                "code": clean_code,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Meta token exchange failed: {resp.text}")
        token_data = resp.json()
        short_token = token_data.get("access_token")
        if not short_token:
            raise RuntimeError(f"No access_token in Meta token response: {token_data}")

        # Step 2: If using Unified Login with config_id, the returned token is already a
        # Business Integration System User Access Token and does not use fb_exchange_token.
        if settings.META_CONFIG_ID:
            return token_data

        # For classic user tokens, exchange for a long-lived token (~60 days)
        try:
            resp2 = await client.get(
                f"{GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_APP_ID.strip(),
                    "client_secret": settings.META_APP_SECRET.strip(),
                    "fb_exchange_token": short_token,
                },
            )
            if resp2.status_code == 200:
                long_data = resp2.json()
                if long_data.get("access_token"):
                    return long_data
        except Exception:
            pass

        return token_data


async def refresh_long_lived_token(access_token: str) -> dict:
    """Refresh an active long-lived Meta token before it expires."""
    if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
        return {
            "access_token": "REFRESHED_MOCK_ACCESS_TOKEN",
            "token_type": "bearer",
            "expires_in": 5183944,
            "mock": True,
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": access_token,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Meta token refresh failed: {resp.text}")
        return resp.json()


async def get_instagram_user_id(access_token: str) -> Optional[str]:
    """Fetch the Instagram user ID (numeric) from the authorized account.

    Checks:
      1. /me/assigned_instagram_accounts (standard for Unified Login / Business Login)
      2. /me (direct Instagram Graph user lookup)
      3. /me/accounts (Facebook Page linked Instagram Business Account fallback)
    """
    if settings.USE_MOCK:
        return "MOCK_IG_USER_ID"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Unified Login / Business Login: assigned Instagram accounts (no Page needed)
        try:
            resp = await client.get(
                f"{GRAPH_BASE}/me/assigned_instagram_accounts",
                params={"fields": "id,username", "access_token": access_token},
            )
            if resp.status_code == 200:
                data = resp.json()
                accounts = data.get("data", [])
                if accounts and accounts[0].get("id"):
                    return str(accounts[0]["id"])
        except Exception:
            pass

        # 2. Direct user endpoint check
        try:
            resp = await client.get(
                f"{GRAPH_BASE}/me",
                params={"fields": "id,user_id,username", "access_token": access_token},
            )
            if resp.status_code == 200:
                data = resp.json()
                uid = data.get("user_id") or data.get("id")
                if uid:
                    return str(uid)
        except Exception:
            pass

        # 3. Fallback: /me/accounts -> instagram_business_account
        resp = await client.get(
            f"{GRAPH_BASE}/me/accounts",
            params={"fields": "name,instagram_business_account", "access_token": access_token},
        )
        if resp.status_code == 200:
            data = resp.json()
            pages = data.get("data", [])
            for page in pages:
                ig = page.get("instagram_business_account")
                if ig and ig.get("id"):
                    return str(ig["id"])

        raise RuntimeError(
            "Could not find an Instagram Professional account associated with this token. "
            "Please ensure your Instagram account is a Professional (Business or Creator) account "
            "and was granted during the login prompt."
        )
