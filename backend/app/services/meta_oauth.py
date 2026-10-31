"""Meta (Facebook/Instagram) OAuth service.

Handles the OAuth 2.0 code exchange flow and long-lived token retrieval.
In mock mode the actual HTTP calls to graph.facebook.com are skipped.

Required Meta App permissions:
  - instagram_basic
  - pages_show_list
  - instagram_content_publish
  - pages_read_engagement  (for comments/analytics)

Required setup (outside this codebase):
  1. Create a Facebook App at developers.facebook.com.
  2. Add the Instagram Graph API product.
  3. Set META_APP_ID, META_APP_SECRET, META_OAUTH_REDIRECT_URI in .env.
  4. Register the redirect URI in the Facebook App dashboard under
     "Valid OAuth Redirect URIs".
  5. The Instagram account must be a Business or Creator account linked to
     a Facebook Page that is managed by the app user.
"""
from __future__ import annotations

import urllib.parse
from typing import Optional

import httpx

from ..settings import settings

GRAPH_BASE = "https://graph.facebook.com/v19.0"
AUTH_BASE = "https://www.facebook.com/v19.0/dialog/oauth"


def build_oauth_redirect_url(state: Optional[str] = None) -> str:
    """Return the Facebook OAuth authorization URL the user must visit."""
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
        "scope": "instagram_basic,pages_show_list,instagram_content_publish,pages_read_engagement,instagram_manage_insights",
        "response_type": "code",
    }
    if state:
        params["state"] = state
    return f"{AUTH_BASE}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """Exchange an OAuth authorization code for a short-lived access token,
    then immediately exchange that for a long-lived token.

    Returns a dict with keys: access_token, token_type, expires_in.
    Raises RuntimeError on failure.
    """
    if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
        # Mock: return a dummy token clearly labeled as fake.
        return {
            "access_token": "MOCK_ACCESS_TOKEN",
            "token_type": "bearer",
            "expires_in": 5183944,
            "mock": True,
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: short-lived token
        resp = await client.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Meta token exchange failed: {resp.text}")
        short_token = resp.json().get("access_token")
        if not short_token:
            raise RuntimeError("No access_token in Meta response")

        # Step 2: long-lived token
        resp2 = await client.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
        if resp2.status_code != 200:
            raise RuntimeError(f"Meta long-lived token exchange failed: {resp2.text}")
        return resp2.json()


async def refresh_long_lived_token(access_token: str) -> dict:
    """Refresh an active long-lived Meta user access token before it expires."""
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
    """Fetch the Instagram Business Account user ID associated with the token.
    
    Verifies that the account is an eligible Instagram Professional (Business or Creator) account.
    """
    if settings.USE_MOCK:
        return "MOCK_IG_USER_ID"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me/accounts",
            params={"fields": "name,instagram_business_account", "access_token": access_token},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch Facebook Pages: {resp.text}")
        data = resp.json()
        pages = data.get("data", [])
        if not pages:
            raise RuntimeError(
                "No Facebook Pages found for this account. Meta requires an Instagram Professional "
                "account to be linked to a Facebook Page you manage."
            )

        for page in pages:
            ig = page.get("instagram_business_account")
            if ig and ig.get("id"):
                return ig["id"]

        raise RuntimeError(
            "No Instagram Professional (Business or Creator) account is linked to your Facebook Pages. "
            "Please link an Instagram Professional account to your Page in Meta Business Suite or Instagram settings."
        )
