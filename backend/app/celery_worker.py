"""Celery application and scheduled-post publishing task.

The worker polls for scheduled posts that are due and publishes them
(via mock or real Meta publisher depending on settings.USE_MOCK).
Also runs recurring autonomous creator planning loops and analytics ingestion.

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
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "publish-due-posts": {
            "task": "app.celery_worker.publish_due_posts",
            "schedule": crontab(minute="*"),  # every minute
        },
        "autonomous-creator-cycles": {
            "task": "app.celery_worker.run_autonomous_cycles",
            "schedule": crontab(minute="0", hour="*"),  # every hour
        },
        "collect-analytics-cycles": {
            "task": "app.celery_worker.collect_analytics_cycles",
            "schedule": crontab(minute="30", hour="*/2"),  # every 2 hours
        },
    },
)


@worker.task(name="app.celery_worker.publish_due_posts", bind=True, max_retries=3, default_retry_delay=60)
def publish_due_posts(self):
    """Find all scheduled posts whose time has arrived and publish them."""
    try:
        asyncio.run(_publish_due_posts_async())
    except Exception as exc:
        log.error("publish_due_posts failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@worker.task(name="app.celery_worker.run_autonomous_cycles", bind=True, max_retries=2, default_retry_delay=120)
def run_autonomous_cycles(self):
    """Run rolling autonomous planning loop for all active workspaces."""
    try:
        asyncio.run(_run_autonomous_cycles_async())
    except Exception as exc:
        log.error("run_autonomous_cycles failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@worker.task(name="app.celery_worker.collect_analytics_cycles", bind=True, max_retries=2, default_retry_delay=120)
def collect_analytics_cycles(self):
    """Ingest recurring analytics observations across workspaces."""
    try:
        asyncio.run(_collect_analytics_cycles_async())
    except Exception as exc:
        log.error("collect_analytics_cycles failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _run_autonomous_cycles_async() -> None:
    from sqlalchemy import select
    from .db import AsyncSessionLocal
    from .models.workspace import Workspace
    from .models.autonomous import AutonomousConfig
    from .services.autonomous_engine import autonomous_engine

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Workspace))
        workspaces = res.scalars().all()
        for ws in workspaces:
            try:
                # Check config
                cfg_res = await db.execute(
                    select(AutonomousConfig).where(AutonomousConfig.workspace_id == ws.id)
                )
                cfg = cfg_res.scalar_one_or_none()
                if cfg and not cfg.is_active:
                    log.info("Workspace %s is paused – skipping autonomous cycle", ws.id)
                    continue

                log.info("Running autonomous creator loop for workspace %s", ws.id)
                await autonomous_engine.run_autonomous_cycle(db, ws.id)
            except Exception as e:
                log.error("Autonomous cycle failed for workspace %s: %s", ws.id, e)


async def _collect_analytics_cycles_async() -> None:
    from sqlalchemy import select
    from .db import AsyncSessionLocal
    from .models.workspace import Workspace
    from .services.learning_engine import learning_engine

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Workspace))
        workspaces = res.scalars().all()
        for ws in workspaces:
            try:
                log.info("Collecting analytics observations for workspace %s", ws.id)
                await learning_engine.ingest_post_observations(
                    db, ws.id, is_mock=settings.USE_MOCK
                )
                await learning_engine.update_strategy_insights(
                    db, ws.id, is_mock=settings.USE_MOCK
                )
            except Exception as e:
                log.error("Analytics collection failed for workspace %s: %s", ws.id, e)


async def _publish_due_posts_async() -> None:
    """Query DB for due posts and publish each one.
    
    * Verifies workspace policy is not paused.
    * Checks requires_approval (skips if pending manual approval).
    * Prevents duplicate publishing.
    * Decrypts token securely and checks expiration.
    * In mock mode simulates publish and audits result.
    """
    from sqlalchemy import select, exists
    from .db import AsyncSessionLocal
    from .models.content import ScheduledPost, PublishedPost
    from .models.meta_token import MetaToken
    from .models.autonomous import AutonomousConfig, AutomationAuditLog
    from .services import meta_publisher
    from .utils.security import decrypt_token
    from .settings import settings

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with AsyncSessionLocal() as db:
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
            # Skip if flagged for approval
            if post.requires_approval:
                log.info("Post %s requires manual approval – skipping", post.id)
                continue

            # Check workspace pause policy
            if post.workspace_id:
                cfg_res = await db.execute(
                    select(AutonomousConfig).where(AutonomousConfig.workspace_id == post.workspace_id)
                )
                cfg = cfg_res.scalar_one_or_none()
                if cfg and not cfg.is_active:
                    log.info("Workspace %s is paused – postponing post %s", post.workspace_id, post.id)
                    continue

            # Skip if already published (duplicate protection)
            dup_check = await db.execute(
                select(exists().where(PublishedPost.scheduled_post_id == post.id))
            )
            if dup_check.scalar():
                log.info("Post %s already published – skipping", post.id)
                continue

            log.info("Publishing post %s (caption: %.40s)", post.id, post.caption or "")
            pub_status = "success"
            pub_error = None
            platform_post_id = None

            is_instagram_mock = settings.MOCK_INSTAGRAM or not (settings.META_APP_ID and settings.META_APP_SECRET)
            token_row = None
            if not is_instagram_mock:
                token_res = await db.execute(
                    select(MetaToken).where(MetaToken.user_id == post.user_id)
                )
                token_row = token_res.scalar_one_or_none()

            access_token: str | None = None
            ig_user_id: str | None = None
            if token_row:
                if token_row.expires_at and token_row.expires_at < datetime.utcnow():
                    log.warning("Meta token for user %s expired – cannot publish post %s", post.user_id, post.id)
                    access_token = None
                else:
                    access_token = decrypt_token(token_row.encrypted_token)
                    ig_user_id = token_row.ig_user_id
            else:
                if is_instagram_mock:
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

            published = PublishedPost(
                scheduled_post_id=post.id,
                platform_post_id=platform_post_id,
                published_at=datetime.utcnow(),
                status=pub_status,
                error_message=pub_error,
            )
            db.add(published)

            if post.workspace_id:
                audit = AutomationAuditLog(
                    workspace_id=post.workspace_id,
                    action="publish",
                    status=pub_status,
                    summary=f"Post {post.id} publish status: {pub_status}" if not pub_error else f"Post {post.id} publish failed: {pub_error}",
                    details={
                        "post_id": str(post.id),
                        "platform_post_id": platform_post_id,
                        "error": pub_error,
                        "is_mock": settings.USE_MOCK,
                    },
                    created_at=datetime.utcnow(),
                )
                db.add(audit)

        await db.commit()
        log.info("Processed %d due post(s)", len(due_posts))
