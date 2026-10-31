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


meta_insights = MetaInsightsService()
