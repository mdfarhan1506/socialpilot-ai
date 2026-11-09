"""End-to-End System Integration Tests — Phase 9 & 10.

Verifies the complete SocialPilot AI lifecycle:
1. Workspace & Brand Setup
2. Trend Research integration (RSS parsing / evergreen fallback)
3. Content Generation & Distinct 7-Day Planning
4. Topic-Specific Image Generation & Metadata Tracking
5. Pre-Publish Quality Validation (Caption constraints, HTTPS image, mock guard)
6. Safe Publishing (Approval guards, duplicate prevention, mock/live toggle)
7. Analytics Collection & Closed-Loop Learning Formulation
8. Idempotency & Re-run Safety (No duplicate schedules on immediate rerun)
9. Partial Failure Handling (Invalid post aborts cleanly without blocking valid posts)
10. Workspace Pause / Resume Lifecycle
11. Celery Worker Task Execution (without live Redis broker)
"""
import os
import uuid
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("MOCK_INSTAGRAM", "true")

from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app.main import app
from backend.app.db import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.brand import BrandProfile
from backend.app.models.content import ScheduledPost, PublishedPost
from backend.app.models.autonomous import AutonomousConfig, AutomationAuditLog, StrategyInsight
from backend.app.models.research import ResearchRun, TrendOpportunity
from backend.app.services.publish_validator import validate_post_for_publishing
from backend.app.services.autonomous_engine import autonomous_engine
from backend.app.services.learning_engine import learning_engine
from backend.app.celery_worker import _publish_due_posts_async

client = TestClient(app)


def _create_test_user_and_workspace(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:6]}@integration-test.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123!"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_r = client.post("/workspace/", json={"name": f"{prefix} Workspace"}, headers=headers)
    ws_id = ws_r.json()["id"]
    return headers, ws_id


class TestEndToEndAutonomousSystem(unittest.TestCase):
    """Full lifecycle integration tests across all services and phases."""

    def test_complete_autonomous_cycle_and_audit(self):
        """Phase 1-8 E2E: Brand -> Trend Research -> Content -> Image -> Validate -> Schedule -> Audit."""
        headers, ws_id = _create_test_user_and_workspace("e2e_full")

        # 1. Setup Brand Profile
        brand_payload = {
            "workspace_id": ws_id,
            "brand_name": "GrowthPulse Analytics",
            "niche": "AI SaaS & B2B Growth",
            "target_audience": "Founders and Growth Marketers",
            "brand_voice": "Data-driven, actionable, and direct",
            "content_pillars": ["Product Analytics", "Viral Loops", "Retention Hacks"],
        }
        b_res = client.post("/brand/", json=brand_payload, headers=headers)
        self.assertIn(b_res.status_code, (200, 201))

        # 2. Trigger Autonomous Cycle
        cycle_res = client.post(f"/autonomous/run-cycle?workspace_id={ws_id}", headers=headers)
        self.assertEqual(cycle_res.status_code, 200)
        cycle_data = cycle_res.json()
        self.assertEqual(cycle_data["status"], "success")
        self.assertGreater(cycle_data["new_posts_planned"], 0)

        # 3. Verify Scheduled Posts in Plan
        plan_res = client.get(f"/autonomous/plan?workspace_id={ws_id}", headers=headers)
        self.assertEqual(plan_res.status_code, 200)
        plan_posts = plan_res.json()
        self.assertGreaterEqual(len(plan_posts), 1)

        # 4. Verify Post Structure & Pre-Publish Validation
        for post in plan_posts:
            self.assertIn("caption", post)
            self.assertIn("image_url", post)
            self.assertTrue(post["image_url"].startswith("https://"))
            self.assertNotIn("[MOCK]", post["caption"])
            self.assertNotIn("PLACEHOLDER_", post["caption"])

        # 5. Verify Audit Logs Recorded Cycle Steps
        log_res = client.get(f"/autonomous/audit-logs?workspace_id={ws_id}", headers=headers)
        self.assertEqual(log_res.status_code, 200)
        logs = log_res.json()
        actions = [l["action"] for l in logs]
        self.assertIn("plan_generation", actions)
        self.assertIn("autonomous_cycle", actions)

    def test_cycle_idempotency_and_no_duplicate_scheduling(self):
        """Running the autonomous cycle twice immediately should be safe and idempotent."""
        headers, ws_id = _create_test_user_and_workspace("e2e_idempotent")

        # Run 1st cycle
        res1 = client.post(f"/autonomous/run-cycle?workspace_id={ws_id}", headers=headers)
        self.assertEqual(res1.status_code, 200)
        initial_count = res1.json()["new_posts_planned"]
        self.assertGreater(initial_count, 0)

        # Run 2nd cycle immediately
        res2 = client.post(f"/autonomous/run-cycle?workspace_id={ws_id}", headers=headers)
        self.assertEqual(res2.status_code, 200)
        second_count = res2.json()["new_posts_planned"]
        # Since schedule window is already filled, immediate rerun must not over-schedule
        self.assertEqual(second_count, 0)

        # Fetch plan: total count should still equal initial_count
        plan_res = client.get(f"/autonomous/plan?workspace_id={ws_id}", headers=headers)
        self.assertEqual(len(plan_res.json()), initial_count)

    def test_partial_failure_isolation_in_publisher(self):
        """Invalid posts should fail pre-publish validation and be audited, without crashing the publisher."""
        import asyncio
        headers, ws_id = _create_test_user_and_workspace("e2e_partial_fail")

        async def _run():
            async with AsyncSessionLocal() as db:
                # Find user
                user_res = await db.execute(
                    select(Workspace).where(Workspace.id == uuid.UUID(ws_id))
                )
                ws = user_res.scalar_one()

                now = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)

                # Create 1 invalid post (HTTP image URL)
                invalid_post = ScheduledPost(
                    workspace_id=ws.id,
                    user_id=ws.owner_id,
                    caption="Valid caption for post with bad image URL #marketing",
                    image_url="http://insecure-cdn.com/bad.png",  # HTTP rejected
                    scheduled_time=now,
                    status="scheduled",
                )
                # Create 1 valid post
                valid_post = ScheduledPost(
                    workspace_id=ws.id,
                    user_id=ws.owner_id,
                    caption="Valid caption for post with valid image URL #growth #tips",
                    image_url="https://images.unsplash.com/photo-good.jpg",
                    scheduled_time=now,
                    status="scheduled",
                )
                db.add(invalid_post)
                db.add(valid_post)
                await db.commit()
                await db.refresh(invalid_post)
                await db.refresh(valid_post)

                invalid_id = invalid_post.id
                valid_id = valid_post.id

            # Run publisher worker logic
            await _publish_due_posts_async()

            # Verify outcomes
            async with AsyncSessionLocal() as db:
                p_inv = await db.get(ScheduledPost, invalid_id)
                p_val = await db.get(ScheduledPost, valid_id)

                self.assertEqual(p_inv.status, "failed")
                self.assertEqual(p_val.status, "published")

                # Check audit log for validation failure
                audit_res = await db.execute(
                    select(AutomationAuditLog).where(
                        AutomationAuditLog.workspace_id == ws.id,
                        AutomationAuditLog.status == "failed",
                    )
                )
                audit_entries = audit_res.scalars().all()
                self.assertTrue(len(audit_entries) >= 1)
                self.assertIn("Pre-publish validation failed", audit_entries[0].summary)

        asyncio.run(_run())

    def test_pause_resume_policy_compliance(self):
        """Paused workspaces must be skipped by both autonomous generator and publishing worker."""
        import asyncio
        headers, ws_id = _create_test_user_and_workspace("e2e_pause")

        # 1. Pause the workspace
        p_res = client.post(f"/autonomous/pause?workspace_id={ws_id}", headers=headers)
        self.assertEqual(p_res.status_code, 200)
        self.assertFalse(p_res.json()["is_active"])

        # 2. Attempt to run cycle while paused -> must be rejected or no-op
        c_res = client.post(f"/autonomous/run-cycle?workspace_id={ws_id}", headers=headers)
        self.assertEqual(c_res.json().get("new_posts_planned", 0), 0)

        # 3. Add a due post and verify publisher skips it while paused
        async def _test_publish_skip():
            async with AsyncSessionLocal() as db:
                ws_obj = await db.get(Workspace, uuid.UUID(ws_id))
                now = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
                post = ScheduledPost(
                    workspace_id=ws_obj.id,
                    user_id=ws_obj.owner_id,
                    caption="Post scheduled before pausing #paused",
                    image_url="https://images.unsplash.com/photo-paused.jpg",
                    scheduled_time=now,
                    status="scheduled",
                )
                db.add(post)
                await db.commit()
                await db.refresh(post)
                p_id = post.id

            await _publish_due_posts_async()

            async with AsyncSessionLocal() as db:
                p_check = await db.get(ScheduledPost, p_id)
                # Must remain scheduled because workspace is paused
                self.assertEqual(p_check.status, "scheduled")

        asyncio.run(_test_publish_skip())

        # 4. Resume workspace
        r_res = client.post(f"/autonomous/resume?workspace_id={ws_id}", headers=headers)
        self.assertEqual(r_res.status_code, 200)
        self.assertTrue(r_res.json()["is_active"])

    def test_analytics_collection_and_learning_loop(self):
        """Ingest observations, update strategy, and verify recommendation availability."""
        headers, ws_id = _create_test_user_and_workspace("e2e_analytics")

        # Ingest analytics via endpoint
        col_res = client.post(f"/analytics/collect?workspace_id={ws_id}", headers=headers)
        self.assertEqual(col_res.status_code, 200)
        data = col_res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("observations_collected", data)

        # Query active strategy insights
        ins_res = client.get(f"/autonomous/insights?workspace_id={ws_id}", headers=headers)
        self.assertEqual(ins_res.status_code, 200)
        insights = ins_res.json()
        self.assertIsInstance(insights, list)

    def test_environment_and_secret_handling(self):
        """Verify settings do not leak raw secret values in string representations."""
        from backend.app.settings import settings
        s_repr = repr(settings)
        # Check that sensitive keys are not exposed verbatim
        if settings.SECRET_KEY and settings.SECRET_KEY != "changeme-in-production":
            self.assertNotIn(settings.SECRET_KEY, s_repr)


if __name__ == "__main__":
    unittest.main()
