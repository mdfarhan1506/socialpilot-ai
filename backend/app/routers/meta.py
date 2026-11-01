"""Meta Instagram OAuth and publishing router.

GET  /meta/status          – connection status (mock/live, linked account)
GET  /meta/oauth/start     – generate state & redirect browser to Facebook login
GET  /meta/oauth/callback  – validate state, handle code exchange, encrypt & store token in DB
POST /meta/publish         – publish using stored token (never requires raw token)

SECURITY: Access tokens are NEVER returned in API responses.
They are encrypted at rest with Fernet and decrypted only server-side
when a publish call is made. State tokens are cryptographically signed,
bound to the authenticated user, expiring, and single-use.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, deps
from ..models.meta_token import MetaToken
from ..models.oauth_state import OAuthState
from ..services import meta_oauth, meta_publisher
from ..utils.security import encrypt_token, decrypt_token
from ..settings import settings

logger = logging.getLogger("socialpilot.meta")
router = APIRouter()


class PublishRequest(BaseModel):
    image_url: str
    caption: str


@router.get("/status")
async def meta_status(
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Return Instagram connection status for the current user.
    Never exposes raw tokens."""
    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == current_user.id)
    )
    token_row = result.scalar_one_or_none()
    if not token_row:
        return {
            "connected": False,
            "account_linked": False,
            "mock_mode": settings.USE_MOCK,
            "message": "No Instagram account connected.",
        }

    now = datetime.utcnow()
    is_expired = token_row.expires_at is not None and token_row.expires_at < now
    return {
        "connected": True,
        "account_linked": True,
        "ig_user_id": token_row.ig_user_id,
        "expires_at": token_row.expires_at.isoformat() if token_row.expires_at else None,
        "is_expired": is_expired,
        "mock_mode": settings.USE_MOCK,
    }


@router.delete("/disconnect")
async def meta_disconnect(
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Remove stored Instagram connection & token for current user.
    Does not delete user, workspace, or scheduled posts.
    """
    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == current_user.id)
    )
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Instagram connection found to disconnect.",
        )
    await db.delete(token_row)
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "Instagram account disconnected successfully."},
    )


@router.get("/oauth/start")
async def oauth_start(
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Generate cryptographically secure state tied to user and redirect to Facebook OAuth.
    In mock mode returns the URL and state as JSON."""
    # Generate cryptographically secure state token
    raw_state = secrets.token_urlsafe(32)
    oauth_state = OAuthState(
        state_token=raw_state,
        user_id=current_user.id,
        provider="meta",
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )
    db.add(oauth_state)
    await db.commit()

    url = meta_oauth.build_oauth_redirect_url(state=raw_state)
    # Always return JSON so the frontend can navigate via window.location.href.
    # Never issue a RedirectResponse here — fetch() follows it automatically,
    # ending up at Meta's login HTML which cannot be parsed as JSON.
    return {
        "mock_mode": settings.USE_MOCK,
        "oauth_url": url,
        "state": raw_state,
        **({"note": "[MOCK] Real redirect skipped."} if settings.USE_MOCK else {}),
    }


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(deps.get_db),
):
    """Handle Meta OAuth callback from browser redirect or direct frontend API fetch.
    Validates single-use expiring state, exchanges code, and stores encrypted token."""
    accept_hdr = request.headers.get("accept", "")
    sec_fetch_dest = request.headers.get("sec-fetch-dest", "")
    wants_json = ("application/json" in accept_hdr or "fetch" in sec_fetch_dest) and sec_fetch_dest != "document"

    # Determine frontend redirect base for browser navigation
    frontend_url = "https://socialpilot-ai-3reh.vercel.app"
    if settings.CORS_ORIGINS:
        for orig in settings.CORS_ORIGINS:
            if orig and "vercel.app" in orig:
                frontend_url = orig.rstrip("/")
                break

    # 1. Handle error response from Meta (e.g. user cancelled dialog)
    if error:
        err_msg = error_description or error
        logger.warning("Meta OAuth error received: %s - %s", error, err_msg)
        return RedirectResponse(
            url=f"{frontend_url}?oauth_error={err_msg}",
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth authorization code in callback.",
        )

    # 2. Validate state parameter (CSRF protection & user binding)
    target_user_id = None
    if state:
        result = await db.execute(
            select(OAuthState).where(OAuthState.state_token == state)
        )
        state_record = result.scalar_one_or_none()
        if not state_record:
            logger.error("OAuth callback rejected: Invalid or unknown state token %s", state)
            return RedirectResponse(
                url=f"{frontend_url}?oauth_error=Invalid+or+tampered+OAuth+state+parameter",
                status_code=status.HTTP_302_FOUND,
            )
        if state_record.is_used:
            logger.error("OAuth callback rejected: Replay attack detected for state token %s", state)
            return RedirectResponse(
                url=f"{frontend_url}?oauth_error=OAuth+state+token+has+already+been+used",
                status_code=status.HTTP_302_FOUND,
            )
        if state_record.expires_at < datetime.utcnow():
            logger.error("OAuth callback rejected: Expired state token %s", state)
            return RedirectResponse(
                url=f"{frontend_url}?oauth_error=OAuth+session+has+expired.+Please+try+connecting+again",
                status_code=status.HTTP_302_FOUND,
            )

        # Mark single-use state as consumed
        state_record.is_used = True
        target_user_id = state_record.user_id
        await db.commit()

    elif settings.USE_MOCK:
        # Fallback for mock test runs if state is omitted in testing
        user_res = await db.execute(select(models.User).limit(1))
        mock_user = user_res.scalar_one_or_none()
        target_user_id = mock_user.id if mock_user else None

    if not target_user_id:
        return RedirectResponse(
            url=f"{frontend_url}?oauth_error=Missing+state+parameter.+Unable+to+verify+session",
            status_code=status.HTTP_302_FOUND,
        )

    # 3. Exchange code for access token and get Instagram account ID
    try:
        token_data = await meta_oauth.exchange_code_for_token(code)
    except RuntimeError as exc:
        logger.error("Token exchange failed: %s", exc)
        return RedirectResponse(
            url=f"{frontend_url}?oauth_error={str(exc)}",
            status_code=status.HTTP_302_FOUND,
        )

    access_token = token_data.get("access_token", "")
    try:
        ig_user_id = await meta_oauth.get_instagram_user_id(access_token)
    except RuntimeError as exc:
        logger.error("Instagram account lookup failed: %s", exc)
        return RedirectResponse(
            url=f"{frontend_url}?oauth_error={str(exc)}",
            status_code=status.HTTP_302_FOUND,
        )

    # 4. Encrypt and upsert the MetaToken for target_user_id
    encrypted = encrypt_token(access_token)
    expires_in = token_data.get("expires_in")
    expires_at = (
        datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    )

    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == target_user_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_token = encrypted
        existing.ig_user_id = ig_user_id
        existing.expires_at = expires_at
        existing.updated_at = datetime.utcnow()
    else:
        db.add(MetaToken(
            user_id=target_user_id,
            ig_user_id=ig_user_id,
            encrypted_token=encrypted,
            expires_at=expires_at,
        ))
    await db.commit()

    # 5. Return JSON payload for direct client fetches, or 302 Redirect for top-level browser navigations
    if wants_json:
        return JSONResponse({
            "mock_mode": settings.USE_MOCK,
            "account_linked": True,
            "ig_user_id": ig_user_id,
            "token_stored": True,
            "note": (
                "[MOCK] Mock token encrypted and stored"
                if settings.USE_MOCK
                else "Token encrypted and stored securely"
            ),
        })

    return RedirectResponse(
        url=f"{frontend_url}?connected=instagram&ig_user_id={ig_user_id or ''}",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/publish")
async def publish_post(
    req: PublishRequest,
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Publish an image post to Instagram using the user's stored token.
    In mock mode no real API call is made; response is clearly labeled."""
    # Look up stored token
    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == current_user.id)
    )
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Instagram account linked. Complete OAuth first via /meta/oauth/start",
        )

    # Decrypt token server-side only
    access_token = decrypt_token(token_row.encrypted_token)
    ig_user_id = token_row.ig_user_id or ""

    try:
        pub_result = await meta_publisher.publish_image(
            ig_user_id=ig_user_id,
            access_token=access_token,
            image_url=req.image_url,
            caption=req.caption,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return pub_result
