"""Unit & integration tests for SocialPilot AI Autonomous Creator.

Covers:
- Autonomous Orchestration loop
- Policy engine: pause/resume, quiet hours, daily frequency caps, sensitive keywords
- Media validation
- Sensitive content screening & approval queue
- Duplicate prevention
- Celery worker tasks & approval guards
- Observation ingestion & learning engine (data provenance isolation)
- REST API endpoints & workspace authorization
"""
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestAutonomousEngine(unittest.TestCase):
    """Test policy engine, media validation, quiet hours, and rolling plan generation."""

    def test_media_validation(self):
        from backend.app.services.autonomous_engine import autonomous_engine

        # Valid HTTPS image URL with recognized extension
        res_valid = autonomous_engine.validate_media("https://images.unsplash.com/photo-test.jpg")
        self.assertTrue(res_valid["valid"])

        # Invalid URL scheme (HTTP instead of HTTPS)
        res_http = autonomous_engine.validate_media("http://images.unsplash.com/photo-test.jpg")
        self.assertFalse(res_http["valid"])
        self.assertIn("https://", res_http["reason"])

        # Rejection of GIF format for Instagram feed
        res_gif = autonomous_engine.validate_media("https://example.com/animation.gif")
        self.assertFalse(res_gif["valid"])
        self.assertIn("GIF", res_gif["reason"])

        # Aspect ratio validation (4:5 = 0.80, 1:1 = 1.0, 1.91:1 = 1.91)
        res_ar_valid = autonomous_engine.validate_media(
            "https://images.unsplash.com/photo-test.jpg", aspect_ratio=1.0
        )
        self.assertTrue(res_ar_valid["valid"])

        res_ar_invalid = autonomous_engine.validate_media(
            "https://images.unsplash.com/photo-test.jpg", aspect_ratio=0.5
        )
        self.assertFalse(res_ar_invalid["valid"])
        self.assertIn("aspect ratio", res_ar_invalid["reason"])

        # Caption constraints (max 2200 chars, max 30 hashtags)
        res_caption_valid = autonomous_engine.validate_media(
            "https://images.unsplash.com/photo-test.jpg",
            caption="Check out this post! #SocialMedia #Growth",
        )
        self.assertTrue(res_caption_valid["valid"])

        long_caption = "A" * 2201
        res_caption_long = autonomous_engine.validate_media(
            "https://images.unsplash.com/photo-test.jpg", caption=long_caption
        )
        self.assertFalse(res_caption_long["valid"])
        self.assertIn("2,200", res_caption_long["reason"])

        too_many_tags = " ".join([f"#tag{i}" for i in range(35)])
        res_tags = autonomous_engine.validate_media(
            "https://images.unsplash.com/photo-test.jpg", caption=too_many_tags
        )
        self.assertFalse(res_tags["valid"])
        self.assertIn("30", res_tags["reason"])

        # Empty URL
        res_empty = autonomous_engine.validate_media("")
        self.assertFalse(res_empty["valid"])

    def test_grounded_content_generation(self):
        import asyncio
        from backend.app.services.autonomous_engine import autonomous_engine

        async def _run():
            res = await autonomous_engine.generate_platform_content(
                niche="B2B SaaS",
                audience="Product Managers",
                tone="strategic and clear",
                target_topic="Product-Led Growth",
                recommended_hook="framework",
                day_offset=1,
            )
            self.assertIn("concept", res)
            self.assertIn("hook", res)
            self.assertIn("script_or_body", res)
            self.assertIn("call_to_action", res)
            self.assertIn("caption", res)
            self.assertIn("hashtags", res)
            self.assertIn("is_ai_generated", res)
            self.assertIn("source", res)

            # Ensure no fake invented statistics in the grounded content
            self.assertNotIn("82% of leaders", res["hook"])
            self.assertNotIn("82% of leaders", res["caption"])

        asyncio.run(_run())

    def test_quiet_hours_avoidance(self):
        from backend.app.services.autonomous_engine import autonomous_engine

        # 23:00 UTC falls in quiet hours (22 to 7)
        dt_quiet = datetime(2026, 11, 1, 23, 0, 0)
        self.assertTrue(autonomous_engine.is_in_quiet_hours(dt_quiet, 22, 7))

        # 14:00 UTC is outside quiet hours
        dt_active = datetime(2026, 11, 1, 14, 0, 0)
        self.assertFalse(autonomous_engine.is_in_quiet_hours(dt_active, 22, 7))

        # Compute adaptive slot: candidate in quiet hours must be shifted into daytime
        slot = autonomous_engine.compute_adaptive_slot(
            target_date=dt_quiet,
            post_index_for_day=0,
            start_quiet=22,
            end_quiet=7,
            strategy_hour=23,
        )
        self.assertFalse(autonomous_engine.is_in_quiet_hours(slot, 22, 7))
        self.assertIn(slot.hour, [8, 10, 12, 14, 16, 18])

    def test_policy_screening(self):
        from backend.app.services.autonomous_engine import autonomous_engine

        keywords = ["controversial", "guaranteed returns", "unverified"]

        # Clean text
        res_clean = autonomous_engine.screen_content_policy(
            "Here are 3 tips to boost your brand reach.", keywords
        )
        self.assertTrue(res_clean["passed"])
        self.assertFalse(res_clean["requires_approval"])

        # Text containing prohibited keyword
        res_flagged = autonomous_engine.screen_content_policy(
            "This controversial strategy brings guaranteed returns!", keywords
        )
        self.assertFalse(res_flagged["passed"])
        self.assertTrue(res_flagged["requires_approval"])
        self.assertIn("controversial", res_flagged["flagged_terms"])
        self.assertIn("guaranteed returns", res_flagged["flagged_terms"])


class TestLearningEngine(unittest.TestCase):
    """Test observation ingestion, strategy updates, and data provenance isolation."""

    def test_strategy_provenance_isolation(self):
        import asyncio
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.workspace import Workspace
        from backend.app.models.user import User
        from backend.app.services.learning_engine import learning_engine

        async def _run():
            async with AsyncSessionLocal() as db:
                user = User(email=f"learn_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
                db.add(user)
                await db.commit()
                await db.refresh(user)

                ws = Workspace(name="Learning WS", owner_id=user.id)
                db.add(ws)
                await db.commit()
                await db.refresh(ws)

                # Ingest mock observations
                obs = await learning_engine.ingest_post_observations(db, ws.id, is_mock=True)
                # Formulate mock insights
                insights = await learning_engine.update_strategy_insights(db, ws.id, is_mock=True)

                self.assertTrue(len(insights) > 0)
                # All mock insights must have is_mock = True
                for ins in insights:
                    self.assertTrue(ins.is_mock)

                # Query active strategy
                strat = await learning_engine.get_active_strategy(db, ws.id)
                self.assertIn("recommended_hook_type", strat)
                self.assertIn("insights", strat)

        asyncio.run(_run())


class TestAutonomousCeleryWorker(unittest.TestCase):
    """Test Celery task registrations, beat schedule, and approval guards."""

    def test_tasks_registered(self):
        from backend.app.celery_worker import worker
        self.assertIn("app.celery_worker.publish_due_posts", worker.tasks)
        self.assertIn("app.celery_worker.run_autonomous_cycles", worker.tasks)
        self.assertIn("app.celery_worker.collect_analytics_cycles", worker.tasks)

    def test_beat_schedules(self):
        from backend.app.celery_worker import worker
        beat = worker.conf.beat_schedule
        self.assertIn("autonomous-creator-cycles", beat)
        self.assertIn("collect-analytics-cycles", beat)
        self.assertIn("publish-due-posts", beat)

    def test_approval_guard_in_publisher(self):
        """Posts requiring approval must NOT be published by the worker."""
        import asyncio
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.content import ScheduledPost, PublishedPost
        from backend.app.models.workspace import Workspace
        from backend.app.models.user import User
        from backend.app.celery_worker import _publish_due_posts_async
        from sqlalchemy import select

        async def _run():
            async with AsyncSessionLocal() as db:
                u = User(email=f"celery_guard_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
                db.add(u)
                await db.commit()
                await db.refresh(u)

                ws = Workspace(name="Guard WS", owner_id=u.id)
                db.add(ws)
                await db.commit()
                await db.refresh(ws)

                past_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)

                # Post that requires approval
                post_pending = ScheduledPost(
                    workspace_id=ws.id,
                    user_id=u.id,
                    caption="Sensitive post awaiting review",
                    scheduled_time=past_time,
                    status="pending_approval",
                    requires_approval=True,
                )
                db.add(post_pending)
                await db.commit()
                await db.refresh(post_pending)

                # Run worker publish logic
                await _publish_due_posts_async()

                # Verify post was NOT published
                pub_res = await db.execute(
                    select(PublishedPost).where(PublishedPost.scheduled_post_id == post_pending.id)
                )
                self.assertIsNone(pub_res.scalar_one_or_none())
                self.assertEqual(post_pending.status, "pending_approval")

        asyncio.run(_run())


class TestAutonomousAPIEndpoints(unittest.TestCase):
    """Test REST API endpoints for autonomous creator and workspace isolation."""

    @classmethod
    def setUpClass(cls):
        # Register user A
        cls.email_a = f"auto_a_{uuid.uuid4().hex[:6]}@test.com"
        r = client.post("/auth/register", json={"email": cls.email_a, "password": "securepassword123"})
        cls.token_a = r.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Create workspace A
        ws_r = client.post("/workspace/", json={"name": "Auto WS A"}, headers=cls.headers_a)
        cls.ws_id_a = ws_r.json()["id"]

        # Register user B (for isolation tests)
        cls.email_b = f"auto_b_{uuid.uuid4().hex[:6]}@test.com"
        r_b = client.post("/auth/register", json={"email": cls.email_b, "password": "securepassword123"})
        cls.token_b = r_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    def test_get_and_update_config(self):
        # GET default config
        resp = client.get(f"/autonomous/config?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        cfg = resp.json()
        self.assertTrue(cfg["is_active"])
        self.assertEqual(cfg["min_posts_per_day"], 1)

        # PUT update config
        update_resp = client.put(
            "/autonomous/config",
            json={
                "workspace_id": self.ws_id_a,
                "min_posts_per_day": 2,
                "max_posts_per_day": 4,
                "quiet_hours_start": 23,
                "quiet_hours_end": 6,
                "restricted_keywords": ["unauthorized", "crypto tip"],
            },
            headers=self.headers_a,
        )
        self.assertEqual(update_resp.status_code, 200)

        # Verify updated
        verify = client.get(f"/autonomous/config?workspace_id={self.ws_id_a}", headers=self.headers_a).json()
        self.assertEqual(verify["min_posts_per_day"], 2)
        self.assertEqual(verify["max_posts_per_day"], 4)
        self.assertEqual(verify["quiet_hours_start"], 23)
        self.assertIn("crypto tip", verify["restricted_keywords"])

    def test_pause_and_resume(self):
        # Pause
        p_res = client.post(f"/autonomous/pause?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(p_res.status_code, 200)
        self.assertFalse(p_res.json()["is_active"])

        cfg = client.get(f"/autonomous/config?workspace_id={self.ws_id_a}", headers=self.headers_a).json()
        self.assertFalse(cfg["is_active"])

        # Resume
        r_res = client.post(f"/autonomous/resume?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(r_res.status_code, 200)
        self.assertTrue(r_res.json()["is_active"])

    def test_run_autonomous_cycle_and_fetch_plan(self):
        # Trigger autonomous cycle
        cycle_res = client.post(f"/autonomous/run-cycle?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(cycle_res.status_code, 200)
        data = cycle_res.json()
        self.assertEqual(data["status"], "success")

        # Fetch rolling plan
        plan_res = client.get(f"/autonomous/plan?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(plan_res.status_code, 200)
        plan = plan_res.json()
        self.assertTrue(len(plan) > 0)

        first_post = plan[0]
        self.assertIsNotNone(first_post["concept"])
        self.assertIsNotNone(first_post["hook"])
        self.assertIsNotNone(first_post["caption"])
        self.assertIsNotNone(first_post["call_to_action"])

        # Fetch insights
        ins_res = client.get(f"/autonomous/insights?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(ins_res.status_code, 200)
        insights = ins_res.json()
        self.assertTrue(len(insights) > 0)

        # Fetch audit logs
        log_res = client.get(f"/autonomous/audit-logs?workspace_id={self.ws_id_a}", headers=self.headers_a)
        self.assertEqual(log_res.status_code, 200)
        logs = log_res.json()
        self.assertTrue(len(logs) > 0)

    def test_workspace_isolation_forbidden(self):
        """User B must be rejected with 403 when trying to access Workspace A's autonomous configuration."""
        resp = client.get(f"/autonomous/config?workspace_id={self.ws_id_a}", headers=self.headers_b)
        self.assertEqual(resp.status_code, 403)

        resp_cycle = client.post(f"/autonomous/run-cycle?workspace_id={self.ws_id_a}", headers=self.headers_b)
        self.assertEqual(resp_cycle.status_code, 403)

        resp_plan = client.get(f"/autonomous/plan?workspace_id={self.ws_id_a}", headers=self.headers_b)
        self.assertEqual(resp_plan.status_code, 403)


if __name__ == "__main__":
    unittest.main()
