"""Meta Graph API Insights service for Instagram media objects.

Fetches direct media engagement fields (likes, comments) and insights metrics
(reach, saved, impressions) using currently supported Graph API endpoints.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import httpx

from ..settings import settings

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


class MetaInsightsService:
    """Fetches real Instagram media metrics and insights."""

    async def fetch_media_metrics(
        self,
        platform_post_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch verified metrics for an Instagram media object.
        
        Queries:
        1. Media object fields: like_count, comments_count, timestamp, media_type
        2. Media insights: reach, saved (and impressions if supported for media type)
        
        Returns:
            Dict containing success flag, extracted counts, and live engagement rate.
        """
        if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
            return {
                "success": True,
                "mock": True,
                "platform_post_id": platform_post_id,
                "reach": 150,
                "impressions": 210,
                "likes": 12,
                "comments": 4,
                "shares": 2,
                "saved": 5,
                "engagement_rate": 15.33,
            }

        if not platform_post_id:
            return {
                "success": False,
                "error": "Missing platform post ID",
                "mock": False,
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            likes = 0
            comments = 0
            reach = 0
            saved = 0
            impressions = 0
            shares = 0

            # 1. Fetch direct media object metrics
            try:
                media_resp = await client.get(
                    f"{GRAPH_BASE}/{platform_post_id}",
                    params={
                        "fields": "id,like_count,comments_count,media_type,timestamp",
                        "access_token": access_token,
                    },
                )
                if media_resp.status_code == 200:
                    media_data = media_resp.json()
                    likes = int(media_data.get("like_count", 0))
                    comments = int(media_data.get("comments_count", 0))
                else:
                    log.warning(
                        "Failed to fetch media object fields for %s: %s",
                        platform_post_id,
                        media_resp.text,
                    )
                    return {
                        "success": False,
                        "error": f"Meta media object query failed: {media_resp.text}",
                        "mock": False,
                    }
            except Exception as e:
                log.error("Network error fetching media object for %s: %s", platform_post_id, e)
                return {"success": False, "error": str(e), "mock": False}

            # 2. Fetch media insights (reach, saved)
            try:
                insights_resp = await client.get(
                    f"{GRAPH_BASE}/{platform_post_id}/insights",
                    params={
                        "metric": "reach,saved",
                        "access_token": access_token,
                    },
                )
                if insights_resp.status_code == 200:
                    insights_data = insights_resp.json().get("data", [])
                    for item in insights_data:
                        name = item.get("name")
                        values = item.get("values", [])
                        val = values[0].get("value", 0) if values else 0
                        if name == "reach":
                            reach = int(val)
                        elif name == "saved":
                            saved = int(val)
                        elif name == "impressions":
                            impressions = int(val)
                else:
                    log.info(
                        "Insights metrics query returned non-200 for %s: %s",
                        platform_post_id,
                        insights_resp.text,
                    )
            except Exception as e:
                log.warning("Insights request error for %s: %s", platform_post_id, e)

            # If impressions was not provided separately, default to reach + likes
            if impressions == 0 and reach > 0:
                impressions = reach

            total_interactions = likes + comments + saved + shares
            base_denominator = max(1, reach if reach > 0 else (likes + comments))
            engagement_rate = round((total_interactions / base_denominator) * 100, 2)

            return {
                "success": True,
                "mock": False,
                "platform_post_id": platform_post_id,
                "reach": reach,
                "impressions": impressions,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saved": saved,
                "engagement_rate": engagement_rate,
            }

    async def fetch_account_insights(
        self,
        ig_user_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch verified account-level metrics and permissions for an Instagram Professional account.

        Queries:
        1. Token Permissions (/me/permissions)
        2. Account Profile details (/ig_user_id?fields=followers_count,media_count,username)
        3. Account Insights (/ig_user_id/insights?metric=reach&period=day)

        Returns:
            Dict containing live account metrics, granted permissions, and honest diagnostics.
        """
        if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
            return {
                "success": True,
                "mock": True,
                "ig_user_id": ig_user_id,
                "followers_count": 0,
                "media_count": 0,
                "reach": 0,
                "granted_permissions": ["instagram_basic", "instagram_manage_insights"],
                "missing_permissions": [],
                "insights_accessible": True,
            }

        if not ig_user_id or ig_user_id == "MOCK_IG_USER_ID":
            # Attempt dynamic account ID resolution using access token
            try:
                from . import meta_oauth
                resolved_id = await meta_oauth.get_instagram_user_id(access_token)
                if resolved_id and resolved_id != "MOCK_IG_USER_ID":
                    ig_user_id = resolved_id
            except Exception as e:
                log.warning("Could not dynamically resolve Instagram user ID: %s", e)

        if not ig_user_id or ig_user_id == "MOCK_IG_USER_ID":
            return {
                "success": False,
                "mock": False,
                "error": "No valid Instagram Professional Account ID connected.",
                "insights_accessible": False,
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            granted_perms: list[str] = []
            missing_perms: list[str] = []

            # 1. Check granted token permissions
            try:
                perm_resp = await client.get(
                    f"{GRAPH_BASE}/me/permissions",
                    params={"access_token": access_token},
                )
                if perm_resp.status_code == 200:
                    perm_data = perm_resp.json().get("data", [])
                    for p in perm_data:
                        if p.get("status") == "granted":
                            granted_perms.append(p.get("permission", ""))
            except Exception as e:
                log.warning("Failed to fetch token permissions: %s", e)

            # Determine required permissions
            for req in ("instagram_basic", "instagram_manage_insights"):
                if req not in granted_perms:
                    missing_perms.append(req)

            # 2. Fetch basic profile counters (followers, media count)
            followers_count = 0
            media_count = 0
            username = ""
            profile_accessible = False

            try:
                prof_resp = await client.get(
                    f"{GRAPH_BASE}/{ig_user_id}",
                    params={
                        "fields": "id,username,followers_count,follows_count,media_count",
                        "access_token": access_token,
                    },
                )
                if prof_resp.status_code == 200:
                    prof_data = prof_resp.json()
                    followers_count = int(prof_data.get("followers_count", 0))
                    media_count = int(prof_data.get("media_count", 0))
                    username = prof_data.get("username", "")
                    profile_accessible = True
                else:
                    log.warning("Failed to fetch profile for IG user %s: %s", ig_user_id, prof_resp.text)
            except Exception as e:
                log.warning("Profile request error for IG user %s: %s", ig_user_id, e)

            # 3. Query account reach insights if permitted
            reach = 0
            insights_accessible = False
            error_note = None

            try:
                insights_resp = await client.get(
                    f"{GRAPH_BASE}/{ig_user_id}/insights",
                    params={
                        "metric": "reach",
                        "period": "day",
                        "access_token": access_token,
                    },
                )
                if insights_resp.status_code == 200:
                    insights_data = insights_resp.json().get("data", [])
                    for item in insights_data:
                        if item.get("name") == "reach":
                            values = item.get("values", [])
                            if values:
                                reach = int(values[-1].get("value", 0))
                    insights_accessible = True
                else:
                    err_json = insights_resp.json().get("error", {})
                    err_msg = err_json.get("message", insights_resp.text)
                    err_code = err_json.get("code")
                    log.info("Account insights unavailable (code %s): %s", err_code, err_msg)
                    if err_code == 100:
                        error_note = f"Insights require Instagram Professional Account with active traffic and permission."
                    elif err_code == 190:
                        error_note = "Session or access token expired. Re-linking required."
                    else:
                        error_note = err_msg
            except Exception as e:
                log.warning("Account insights request error: %s", e)
                error_note = str(e)

            return {
                "success": True,
                "mock": False,
                "ig_user_id": ig_user_id,
                "username": username,
                "followers_count": followers_count,
                "media_count": media_count,
                "reach": reach,
                "profile_accessible": profile_accessible,
                "insights_accessible": insights_accessible,
                "granted_permissions": granted_perms,
                "missing_permissions": missing_perms,
                "error_note": error_note,
            }


meta_insights = MetaInsightsService()
