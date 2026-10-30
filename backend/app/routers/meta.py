"""Meta Instagram OAuth and publishing router.

GET  /meta/status          – connection status (mock/live, linked account)
GET  /meta/oauth/start     – redirect browser to Facebook login
GET  /meta/oauth/callback  – handle code exchange; encrypt & store token in DB
POST /meta/publish         – publish using stored token (never requires raw token)

SECURITY: Access tokens are NEVER returned in API responses.
They are encrypted at rest with Fernet and decrypted only server-side
when a publish call is made.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, deps
from ..models.meta_token import MetaToken
from ..services import meta_oauth, meta_publisher
from ..utils.security import encrypt_token, decrypt_token
from ..settings import settings

router = APIRouter()


class PublishRequest(BaseModel):
    image_url: str
    caption: str


@router.get("/status")
async def meta_status(
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Return mock/live mode, whether Meta credentials are configured,
    and whether the current user has linked an Instagram account."""
    linked = False
    ig_user_id = None
    expires_at = None
    days_left = None
    token_expired = False

    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == current_user.id)
    )
    token_row = result.scalar_one_or_none()
    if token_row:
        linked = True
        ig_user_id = token_row.ig_user_id
        expires_at = token_row.expires_at
        if expires_at:
            delta = expires_at - datetime.utcnow()
            days_left = max(0, delta.days)
            token_expired = delta.total_seconds() <= 0

    return {
        "mock_mode": settings.USE_MOCK,
        "meta_configured": bool(settings.META_APP_ID and settings.META_APP_SECRET),
        "account_linked": linked,
        "ig_user_id": ig_user_id,
        "expires_at": expires_at,
        "days_left": days_left,
        "token_expired": token_expired,
        "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
    }


@router.post("/token/refresh")
async def refresh_token_endpoint(
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Refresh the user's stored long-lived Meta token before it expires."""
    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == current_user.id)
    )
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No linked Instagram account to refresh",
        )

    active_token = decrypt_token(token_row.encrypted_token)
    try:
        new_token_data = await meta_oauth.refresh_long_lived_token(active_token)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    new_access_token = new_token_data.get("access_token", active_token)
    token_row.encrypted_token = encrypt_token(new_access_token)
    expires_in = new_token_data.get("expires_in")
    token_row.expires_at = (
        datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    )
    token_row.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "status": "success",
        "message": "Meta token refreshed successfully",
        "expires_at": token_row.expires_at,
        "mock_mode": settings.USE_MOCK,
    }


@router.get("/oauth/start")
async def oauth_start(current_user: models.User = Depends(deps.get_current_user)):
    """Redirect to Facebook OAuth authorization page.
    In mock mode returns the URL as JSON instead of redirecting."""
    url = meta_oauth.build_oauth_redirect_url()
    if settings.USE_MOCK:
        return {
            "mock_mode": True,
            "oauth_url": url,
            "note": "[MOCK] Real redirect skipped. Visit the URL manually when credentials are configured.",
        }
    return RedirectResponse(url=url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    current_user: models.User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Handle OAuth callback: exchange code, encrypt token, store in DB.
    The raw access token is NEVER included in the response."""
    try:
        token_data = await meta_oauth.exchange_code_for_token(code)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    access_token = token_data.get("access_token", "")
    ig_user_id = await meta_oauth.get_instagram_user_id(access_token)

    # Encrypt and upsert the token
    encrypted = encrypt_token(access_token)
    expires_in = token_data.get("expires_in")
    expires_at = (
        datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    )

    result = await db.execute(
        select(MetaToken).where(MetaToken.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_token = encrypted
        existing.ig_user_id = ig_user_id
        existing.expires_at = expires_at
        existing.updated_at = datetime.utcnow()
    else:
        db.add(MetaToken(
            user_id=current_user.id,
            ig_user_id=ig_user_id,
            encrypted_token=encrypted,
            expires_at=expires_at,
        ))
    await db.commit()

    return {
        "mock_mode": settings.USE_MOCK,
        "account_linked": True,
        "ig_user_id": ig_user_id,
        "token_stored": True,
        "note": (
            "[MOCK] Mock token encrypted and stored"
            if settings.USE_MOCK
            else "Token encrypted and stored securely"
        ),
    }


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
