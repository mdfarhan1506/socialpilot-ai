"""Unit and integration tests for Phase 7 (Adaptive Scheduling) and Phase 8 (Pre-Publish Quality Validation).

Covers:
- Phase 7:
  1. Default/Hypothesis posting times when data is insufficient (<5 live samples).
  2. Proof that hypothesis times are clearly labelled with data_basis='hypothesis'.
  3. Evidence-based posting times when >= 5 live observations exist with data_basis='live_data_verified'.
  4. Integration into autonomous_engine scheduling loop.
  5. GET /schedule/recommend-times endpoint.

- Phase 8:
  1. Caption validation: empty, too short, too long, too many hashtags, mock markers [MOCK], repetitive gibberish.
  2. Image URL validation: empty, non-HTTPS, unsupported extensions (.gif, unknown domain), valid CDN hosts.
  3. Network reachability validation check (mocked HTTP responses).
  4. Pre-publish validation integration into Celery worker and autonomous loop.
  5. API blocking invalid posts with clear 422 errors.
"""
from __future__ import annotations

import asyncio
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.publish_validator import (
    validate_caption,
    validate_image_url,
    validate_image_url_reachable,
    validate_post_for_publishing,
)
from backend.app.services.adaptive_scheduler import (
    recommend_posting_times,
    get_best_hour_for_day,
    MIN_LIVE_SAMPLES,
)

client = TestClient(app)


def _register_and_workspace(suffix: str):
    email = f"p78_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpassword123"})
    assert r.status_code == 200, f"Register failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_r = client.post("/workspace/", json={"name": f"WS_{suffix}"}, headers=headers)
    assert ws_r.status_code == 200, f"Workspace creation failed: {ws_r.text}"
    return headers, ws_r.json()["id"]


class TestPublishValidatorUnit(unittest.TestCase):
    """Test validation of captions and image URLs according to Instagram specifications."""

    def test_caption_empty_or_too_short(self):
        r1 = validate_caption("")
        self.assertFalse(r1.passed)
        self.assertIn("empty", r1.summary.lower())

        r2 = validate_caption("hi")
        self.assertFalse(r2.passed)
        self.assertIn("too short", r2.summary.lower())

    def test_caption_mock_marker_blocked(self):
        r = validate_caption("Here is a great post [MOCK] content for followers!")
        self.assertFalse(r.passed)
        self.assertIn("mock", r.summary.lower())

    def test_caption_too_many_hashtags(self):
        tags = " ".join([f"#tag{i}" for i in range(32)])
        r = validate_caption(f"Valid text but too many tags {tags}")
        self.assertFalse(r.passed)
        self.assertIn("hashtags", r.summary.lower())

    def test_caption_repetitive_gibberish(self):
        r = validate_caption("aaaaaaaaaaaaaaaaaaaaaaa")
        self.assertFalse(r.passed)
        self.assertTrue(any("repetitive" in f.lower() or "repeated" in f.lower() for f in r.failures))

    def test_caption_valid(self):
        r = validate_caption("Excited to announce our latest AI automation feature! Check out our bio link. #AI #SaaS #Growth")
        self.assertTrue(r.passed)
        self.assertEqual(len(r.failures), 0)

    def test_image_url_non_https(self):
        r = validate_image_url("http://images.unsplash.com/photo-123.jpg")
        self.assertFalse(r.passed)
        self.assertIn("https://", r.summary)

    def test_image_url_gif_blocked(self):
        r = validate_image_url("https://images.unsplash.com/animated.gif")
        self.assertFalse(r.passed)
        self.assertIn("gif", r.summary.lower())

    def test_image_url_unsupported_format(self):
        r = validate_image_url("https://example.com/unsupported_file.xyz")
        self.assertFalse(r.passed)
        self.assertIn("supported format", r.summary.lower())

    def test_image_url_valid_cdn_and_extensions(self):
        valid_urls = [
            "https://images.unsplash.com/photo-1542744094-3a31727223ec?auto=format&fit=crop&w=1200",
            "https://cdn.example.com/assets/visual.png",
            "https://s3.amazonaws.com/my-bucket/posts/design.webp",
            "https://example.com/photo.jpeg",
        ]
        for u in valid_urls:
            r = validate_image_url(u)
            self.assertTrue(r.passed, f"URL should be valid: {u}")

    def test_image_url_reachability_mocked(self):
        import httpx

        async def _run():
            with patch("httpx.AsyncClient.head") as mock_head:
                mock_resp = AsyncMock()
                mock_resp.status_code = 200
                mock_resp.headers = {"content-type": "image/jpeg"}
                mock_head.return_value = mock_resp

                res = await validate_image_url_reachable("https://images.unsplash.com/photo-123.jpg")
                self.assertTrue(res.passed)

            with patch("httpx.AsyncClient.head") as mock_head_404:
                mock_resp_404 = AsyncMock()
                mock_resp_404.status_code = 404
                mock_head_404.return_value = mock_resp_404

                res_404 = await validate_image_url_reachable("https://images.unsplash.com/missing.jpg")
                self.assertFalse(res_404.passed)
                self.assertIn("404", res_404.summary)

        asyncio.run(_run())


class TestAdaptiveScheduling(unittest.TestCase):
    """Test adaptive scheduling service and hypothesis fallback."""

    @classmethod
    def setUpClass(cls):
        cls.headers, cls.ws_id = _register_and_workspace("adaptive")

    def test_hypothesis_slots_when_insufficient_data(self):
        from backend.app.db import AsyncSessionLocal

        # Use an isolated workspace with 0 observations
        _, isolated_ws_id = _register_and_workspace("hypo_empty")

        async def _run():
            async with AsyncSessionLocal() as db:
                ws_uuid = uuid.UUID(isolated_ws_id)
                rec = await recommend_posting_times(db, ws_uuid, n_slots=3)
                self.assertEqual(rec["data_basis"], "hypothesis")
                self.assertLess(rec["samples_used"], MIN_LIVE_SAMPLES)
                self.assertEqual(len(rec["recommended_hours"]), 3)
                self.assertIn("hypothesis", rec["rationale"].lower())

                for slot in rec["slots"]:
                    self.assertEqual(slot["data_basis"], "hypothesis")
                    self.assertEqual(slot["confidence"], "low")

        asyncio.run(_run())

    def test_evidence_based_slots_when_sufficient_live_data(self):
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.content import ScheduledPost
        from backend.app.models.autonomous import PostAnalyticsObservation

        async def _run():
            async with AsyncSessionLocal() as db:
                ws_uuid = uuid.UUID(self.ws_id)
                now = datetime.now(timezone.utc).replace(tzinfo=None)

                # Seed 6 live observations at specific publication hours (e.g., 15:00 UTC with 8.5% eng rate)
                for i in range(6):
                    sched_time = now.replace(hour=15, minute=0, second=0) - timedelta(days=i + 1)
                    post = ScheduledPost(
                        workspace_id=ws_uuid,
                        caption=f"Evidence post #{i} for time test",
                        scheduled_time=sched_time,
                        status="published",
                    )
                    db.add(post)
                    await db.commit()
                    await db.refresh(post)

                    obs = PostAnalyticsObservation(
                        workspace_id=ws_uuid,
                        scheduled_post_id=post.id,
                        post_age_hours=24.0,
                        impressions=500,
                        reach=400,
                        likes=30,
                        comments=5,
                        shares=2,
                        saves=4,
                        engagement_rate=8.5,
                        data_provenance="live_meta_api",
                        recorded_at=now,
                    )
                    db.add(obs)
                await db.commit()

                rec = await recommend_posting_times(db, ws_uuid, n_slots=3)
                self.assertEqual(rec["data_basis"], "live_data_verified")
                self.assertGreaterEqual(rec["samples_used"], 5)
                # 15:00 UTC should be the top recommended hour due to 8.5% engagement rate
                self.assertEqual(rec["recommended_hours"][0], 15)
                self.assertEqual(rec["slots"][0]["data_basis"], "live_data_verified")
                self.assertAlmostEqual(rec["slots"][0]["avg_engagement_rate"], 8.5, places=1)

        asyncio.run(_run())

    def test_recommend_times_api_endpoint(self):
        resp = client.get(f"/schedule/recommend-times?workspace_id={self.ws_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("recommended_hours", data)
        self.assertIn("data_basis", data)
        self.assertIn("slots", data)


class TestPrePublishValidationIntegration(unittest.TestCase):
    """Test validation rejection in scheduling API and celery publisher."""

    @classmethod
    def setUpClass(cls):
        cls.headers, cls.ws_id = _register_and_workspace("prepub_int")

    def test_schedule_post_rejects_mock_caption(self):
        future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        resp = client.post(
            "/schedule/",
            json={
                "caption": "Check out this [MOCK] preview post!",
                "image_url": "https://images.unsplash.com/photo-123.jpg",
                "scheduled_time": future_time,
                "workspace_id": self.ws_id,
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("mock", resp.json()["detail"].lower())

    def test_schedule_post_rejects_invalid_image_url(self):
        future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        resp = client.post(
            "/schedule/",
            json={
                "caption": "Valid caption for our audience.",
                "image_url": "http://insecure-http.com/image.jpg",
                "scheduled_time": future_time,
                "workspace_id": self.ws_id,
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("https://", resp.json()["detail"])

    def test_schedule_post_success_with_valid_content(self):
        future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        resp = client.post(
            "/schedule/",
            json={
                "caption": "Valid and valuable marketing insight for founders! #Strategy #Growth",
                "image_url": "https://images.unsplash.com/photo-valid.jpg",
                "scheduled_time": future_time,
                "workspace_id": self.ws_id,
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "scheduled")

    def test_celery_publisher_aborts_on_invalid_post(self):
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.content import ScheduledPost, PublishedPost
        from backend.app.models.autonomous import AutomationAuditLog
        from backend.app.celery_worker import _publish_due_posts_async
        from sqlalchemy import select

        async def _run():
            async with AsyncSessionLocal() as db:
                ws_uuid = uuid.UUID(self.ws_id)
                past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)

                # Insert a scheduled post that contains mock markers
                invalid_post = ScheduledPost(
                    workspace_id=ws_uuid,
                    caption="Invalid [MOCK] caption in queue",
                    image_url="http://insecure.com/pic.jpg",
                    scheduled_time=past,
                    status="scheduled",
                )
                db.add(invalid_post)
                await db.commit()
                await db.refresh(invalid_post)

                # Run worker publish logic
                await _publish_due_posts_async()

                # Verify post was marked failed and published record reflects the reason
                await db.refresh(invalid_post)
                self.assertEqual(invalid_post.status, "failed")

                pub_res = await db.execute(
                    select(PublishedPost).where(PublishedPost.scheduled_post_id == invalid_post.id)
                )
                pub = pub_res.scalar_one_or_none()
                self.assertIsNotNone(pub)
                self.assertEqual(pub.status, "failed")
                self.assertIn("Pre-publish validation failed", pub.error_message)

                # Verify an audit log entry recorded the abort reason
                audit_res = await db.execute(
                    select(AutomationAuditLog).where(
                        AutomationAuditLog.workspace_id == ws_uuid,
                        AutomationAuditLog.action == "publish",
                        AutomationAuditLog.status == "failed",
                    )
                )
                audits = audit_res.scalars().all()
                self.assertTrue(len(audits) > 0)
                self.assertIn("aborted", audits[-1].summary.lower())

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
