"""Celery application and scheduled-post publishing task.

The worker polls for scheduled posts that are due and publishes them
(via mock or real Meta publisher depending on settings.USE_MOCK).

Start with:
  celery -A app.celery_worker.worker worker --loglevel=info
  celery -A app.celery_worker.worker beat  --loglevel=info
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

from .settings import settings

log = logging.getLogger(__name__)

worker = Celery(
    "socialpilot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

worker.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Beat schedule: check every minute for due posts
    beat_schedule={
        "publish-due-posts": {
            "task": "app.celery_worker.publish_due_posts",
            "schedule": crontab(minute="*"),  # every minute
        }
    },
)


@worker.task(name="app.celery_worker.publish_due_posts", bind=True, max_retries=3, default_retry_delay=60)
def publish_due_posts(self):
    """Find all scheduled posts whose time has arrived and publish them.

    Uses asyncio.run() because the DB layer and publisher are async.
    If publishing fails the task retries up to 3 times with 60 s back-off.
    """
    try:
        asyncio.run(_publish_due_posts_async())
    except Exception as exc:
        log.error("publish_due_posts failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _publish_due_posts_async() -> None:
    """Async body: query DB for due posts and publish each one.

    * Prevent duplicate publishing – if a ``PublishedPost`` already exists for a
      ``ScheduledPost`` we skip it.
    * Load the stored Meta token for the post's owner, decrypt it, and verify it
      hasn't expired. If it is missing or expired we mark the post as ``failed``
      and record the reason.
    * On any exception from the publisher we record ``failed`` with the error.
    """
    from sqlalchemy import select, exists
    from .db import AsyncSessionLocal
    from .models.content import ScheduledPost, PublishedPost
    from .models.meta_token import MetaToken
    from .services import meta_publisher
    from .utils.security import decrypt_token
    from .settings import settings

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with AsyncSessionLocal() as db:
        # Find all scheduled posts that are due and not already published
        result = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == "scheduled",
                ScheduledPost.scheduled_time <= now,
            )
        )
        due_posts = result.scalars().all()

        if not due_posts:
            log.debug("No posts due for publishing at %s", now)
            return

        for post in due_posts:
            # Skip if already published (duplicate protection)
            dup_check = await db.execute(
                select(exists().where(PublishedPost.scheduled_post_id == post.id))
            )
            if dup_check.scalar():
                log.info("Post %s already published – skipping", post.id)
                continue

            log.info(
                "Publishing scheduled post %s (caption: %.40s)",
                post.id,
                post.caption or "",
            )
            pub_status = "success"
            pub_error = None
            platform_post_id = None

            # Retrieve the stored token for the user that scheduled the post
            token_row = None
            if not settings.USE_MOCK:
                token_res = await db.execute(
                    select(MetaToken).where(MetaToken.user_id == post.user_id)
                )
                token_row = token_res.scalar_one_or_none()

            access_token: str | None = None
            ig_user_id: str | None = None
            if token_row:
                # Check expiry
                if token_row.expires_at and token_row.expires_at < datetime.utcnow():
                    log.warning(
                        "Meta token for user %s expired – cannot publish post %s",
                        post.user_id,
                        post.id,
                    )
                    access_token = None
                else:
                    access_token = decrypt_token(token_row.encrypted_token)
                    ig_user_id = token_row.ig_user_id
            else:
                # In mock mode we still want to run but without a real token
                if settings.USE_MOCK:
                    access_token = "MOCK_TOKEN"
                    ig_user_id = "MOCK_IG_USER_ID"

            if not access_token:
                pub_status = "failed"
                pub_error = "Missing or expired Meta access token"
                post.status = "failed"
            else:
                try:
                    result_data = await meta_publisher.publish_image(
                        ig_user_id=ig_user_id or "",
                        access_token=access_token,
                        image_url=post.image_url or "",
                        caption=post.caption or "",
                    )
                    platform_post_id = result_data.get("publish_id")
                    post.status = "published"
                except Exception as exc:
                    log.error("Failed to publish post %s: %s", post.id, exc)
                    pub_status = "failed"
                    pub_error = str(exc)
                    post.status = "failed"

            # Record in published_posts (even on failure for audit)
            published = PublishedPost(
                scheduled_post_id=post.id,
                platform_post_id=platform_post_id,
                published_at=datetime.utcnow(),
                status=pub_status,
                error_message=pub_error,
            )
            db.add(published)

        await db.commit()
        log.info("Processed %d due post(s)", len(due_posts))

        await db.commit()
        log.info("Processed %d due post(s)", len(due_posts))
