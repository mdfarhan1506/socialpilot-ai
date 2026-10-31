"""Meta Instagram publishing service.

In real mode:
  1. Create a media container: POST /{ig_user_id}/media
  2. Poll container status until FINISHED.
  3. Publish: POST /{ig_user_id}/media_publish

In mock mode returns a clearly labeled fake response without making any
HTTP calls.

NOTE: Real publishing requires:
  - A valid user or system user access token with instagram_content_publish permission.
  - An Instagram Business or Creator (Professional) account.
  - The image/video must be publicly accessible (a signed MinIO/S3 URL works).
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from ..settings import settings

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _parse_meta_error(resp_text: str, default_msg: str) -> str:
    """Extract actionable error diagnostics from a Meta Graph API error response."""
    try:
        import json
        err_json = json.loads(resp_text)
        err = err_json.get("error", {})
        code = err.get("code")
        msg = err.get("message", default_msg)
        if code == 190:
            return f"Meta authentication failed (code 190): Access token is invalid or expired. Re-authorization required."
        elif code in (36003, 36004):
            return f"Instagram aspect ratio error (code {code}): Image aspect ratio must be between 4:5 (0.80) and 1.91:1."
        elif code == 2207001 or "could not be fetched" in msg.lower():
            return f"Instagram media download error: Meta was unable to fetch the image URL. Ensure it is a publicly accessible HTTPS image."
        elif code in (10, 100):
            return f"Meta permission error (code {code}): {msg}. Verify the account has 'instagram_content_publish' granted."
        return f"{default_msg}: {msg}"
    except Exception:
        return f"{default_msg}: {resp_text}"


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
            raise RuntimeError(_parse_meta_error(create_resp.text, "Media container creation failed"))
        creation_id: str = create_resp.json().get("id")
        if not creation_id:
            raise RuntimeError("No container ID returned in Meta response")

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
                raise RuntimeError("Media container processing failed on Meta's servers (invalid image encoding or dimensions)")
            await asyncio.sleep(3)
        else:
            raise RuntimeError("Media container timed out before FINISHED state")

        # Step 3 – publish
        pub_resp = await client.post(
            f"{GRAPH_BASE}/{ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": access_token},
        )
        if pub_resp.status_code != 200:
            raise RuntimeError(_parse_meta_error(pub_resp.text, "Media publish failed"))
        publish_id = pub_resp.json().get("id")
        return {
            "creation_id": creation_id,
            "publish_id": publish_id,
            "status": "published",
            "mock": False,
        }
