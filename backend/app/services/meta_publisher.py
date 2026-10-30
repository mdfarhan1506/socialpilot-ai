"""Meta Instagram publishing service.

In real mode:
  1. Create a media container: POST /{ig_user_id}/media
  2. Poll container status until FINISHED.
  3. Publish: POST /{ig_user_id}/media_publish

In mock mode returns a clearly labeled fake response without making any
HTTP calls to graph.facebook.com.

NOTE: Real publishing requires:
  - A valid long-lived user access token with instagram_content_publish scope.
  - An Instagram Business or Creator account.
  - The image/video must be publicly accessible (a signed MinIO/S3 URL works).
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from ..settings import settings

GRAPH_BASE = "https://graph.facebook.com/v19.0"


async def publish_image(
    ig_user_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> dict:
    """Publish an image post to Instagram.

    Returns a dict with keys: creation_id, publish_id, status, mock.
    Raises RuntimeError on API failure.
    """
    if settings.USE_MOCK or not (settings.META_APP_ID and settings.META_APP_SECRET):
        return {
            "creation_id": "MOCK_CREATION_ID",
            "publish_id": "MOCK_PUBLISH_ID",
            "status": "published",
            "mock": True,
            "message": "[MOCK] Post published successfully (no real API call made)",
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1 – create container
        create_resp = await client.post(
            f"{GRAPH_BASE}/{ig_user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token,
            },
        )
        if create_resp.status_code != 200:
            raise RuntimeError(f"Media container creation failed: {create_resp.text}")
        creation_id: str = create_resp.json().get("id")
        if not creation_id:
            raise RuntimeError("No container ID in Meta response")

        # Step 2 – poll until FINISHED (max 30 s)
        for _ in range(10):
            status_resp = await client.get(
                f"{GRAPH_BASE}/{creation_id}",
                params={"fields": "status_code", "access_token": access_token},
            )
            code = status_resp.json().get("status_code", "")
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError("Media container processing failed")
            await asyncio.sleep(3)
        else:
            raise RuntimeError("Media container timed out before FINISHED state")

        # Step 3 – publish
        pub_resp = await client.post(
            f"{GRAPH_BASE}/{ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": access_token},
        )
        if pub_resp.status_code != 200:
            raise RuntimeError(f"Media publish failed: {pub_resp.text}")
        publish_id = pub_resp.json().get("id")
        return {
            "creation_id": creation_id,
            "publish_id": publish_id,
            "status": "published",
            "mock": False,
        }
