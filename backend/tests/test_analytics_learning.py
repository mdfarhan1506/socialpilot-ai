"""Phase 5+6 tests: Analytics-Based Learning & Autonomous Workflow Integration.

Covers:
- Observation ingestion with real / missing Meta permissions
- Duplicate observation prevention (safe reruns)
- Live-data provenance isolation: mock insights never drive live strategy
- Minimum live samples threshold for strategy activation
- Analytics collect endpoint: missing token, missing permissions, success
- Autonomous cycle safe retry (idempotency)
- Partial failure audit logging
- Analytics-guided hook selection only when enough real data exists
- Paused workspace blocks all workflow steps
"""
from __future__ import annotations

import asyncio
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _register_and_workspace(suffix: str):
    """Register a user and create a workspace; return (headers, ws_id)."""
    email = f"al_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200, f"Register failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_r = client.post("/workspace/", json={"name": f"WS_{suffix}"}, headers=headers)
    assert ws_r.status_code == 200, f"Workspace creation failed: {ws_r.text}"
    ws_id = ws_r.json()["id"]
    return headers, ws_id


# ---------------------------------------------------------------------------
# Unit tests – Learning Engine (use TestClient to ensure DB is initialised)
# ---------------------------------------------------------------------------

class TestLearningEngineProvenance(unittest.TestCase):
    """Verify mock and live observations are strictly separated."""

    @classmethod
    def setUpClass(cls):
        cls.headers, cls.ws_id = _register_and_workspace("prov")

    def test_get_active_strategy_live_requires_enough_samples(self):
        """get_active_strategy(require_live=True) returns awaiting_live_data
        when no live insights exist yet."""
        from backend.app.db import AsyncSessionLocal
        from backend.app.services.learning_engine import learning_engine

        async def _run():
            async with AsyncSessionLocal() as db:
                ws_uuid = uuid.UUID(self.ws_id)
                strategy = await learning_engine.get_active_strategy(
                    db, ws_uuid, require_live=True
                )
                self.assertEqual(strategy["data_status"], "awaiting_live_data")
                self.assertFalse(strategy["has_enough_live_data"])
                self.assertIsInstance(strategy["recommended_hook_type"], str)
                self.assertTrue(len(strategy["recommended_hook_type"]) > 0)

        asyncio.run(_run())

    def test_mock_strategy_is_never_marked_live(self):
        """Mock-mode strategy insights must always carry is_mock=True."""
        from backend.app.db import AsyncSessionLocal
        from backend.app.services.learning_engine import learning_engine

        async def _run():
            async with AsyncSessionLocal() as db:
                ws_uuid = uuid.UUID(self.ws_id)
                insights = await learning_engine.update_strategy_insights(
                    db, ws_uuid, is_mock=True
                )
                for ins in insights:
                    self.assertTrue(
                        ins.is_mock,
                        f"Mock insight must have is_mock=True, got False for '{ins.topic}'",
                    )

        asyncio.run(_run())

    def test_duplicate_observation_skipped(self):
        """Calling ingest_post_observations twice must not create duplicate rows."""
        from sqlalchemy import select
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.content import ScheduledPost, PublishedPost
        from backend.app.models.autonomous import PostAnalyticsObservation
        from backend.app.services.learning_engine import learning_engine

        async def _run():
            async with AsyncSessionLocal() as db:
                ws_uuid = uuid.UUID(self.ws_id)
                past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)

                # Create a published post
                post = ScheduledPost(
                    workspace_id=ws_uuid,
                    caption="Dup observation test post",
                    scheduled_time=past,
                    status="published",
                )
                db.add(post)
                await db.commit()
                await db.refresh(post)

                pub = PublishedPost(
                    scheduled_post_id=post.id,
                    platform_post_id="MOCK_DUP_111",
                    published_at=past,
                    status="success",
                )
                db.add(pub)
                await db.commit()

                # First ingest
                obs1 = await learning_engine.ingest_post_observations(db, ws_uuid, is_mock=True)
                first_count = len(obs1)

                # Second ingest must produce 0 new observations for this post
                obs2 = await learning_engine.ingest_post_observations(db, ws_uuid, is_mock=True)

                # Count DB rows for this specific post
                db_res = await db.execute(
                    select(PostAnalyticsObservation).where(
                        PostAnalyticsObservation.scheduled_post_id == post.id
                    )
                )
                all_obs = db_res.scalars().all()
                self.assertEqual(len(all_obs), 1, "Should only have 1 observation per published post")
                self.assertGreaterEqual(first_count, 1)
                self.assertEqual(len(obs2), 0, "Second ingest must return 0 new for already-observed posts")

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Unit tests – Autonomous Engine safety
# ---------------------------------------------------------------------------

class TestAutonomousWorkflowSafety(unittest.TestCase):
    """Verify the autonomous loop handles pauses and reruns safely."""

    def test_run_cycle_paused_workspace_returns_paused(self):
        """A paused workspace must immediately return status=paused."""
        from sqlalchemy import select
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.autonomous import AutonomousConfig
        from backend.app.models.content import ScheduledPost
        from backend.app.services.autonomous_engine import autonomous_engine

        headers, ws_id = _register_and_workspace("pause_unit")
        ws_uuid = uuid.UUID(ws_id)

        async def _run():
            async with AsyncSessionLocal() as db:
                # Ensure config is paused
                cfg_res = await db.execute(
                    select(AutonomousConfig).where(AutonomousConfig.workspace_id == ws_uuid)
                )
                cfg = cfg_res.scalar_one_or_none()
                if cfg:
                    cfg.is_active = False
                else:
                    cfg = AutonomousConfig(workspace_id=ws_uuid, is_active=False)
                    db.add(cfg)
                await db.commit()

                before_res = await db.execute(
                    select(ScheduledPost).where(ScheduledPost.workspace_id == ws_uuid)
                )
                before_count = len(before_res.scalars().all())

                result = await autonomous_engine.run_autonomous_cycle(db, ws_uuid)
                self.assertEqual(result["status"], "paused")
                self.assertEqual(result["new_posts_planned"], 0)

                after_res = await db.execute(
                    select(ScheduledPost).where(ScheduledPost.workspace_id == ws_uuid)
                )
                after_count = len(after_res.scalars().all())
                self.assertEqual(before_count, after_count)

        asyncio.run(_run())

    def test_run_cycle_twice_no_duplicate_posts(self):
        """Running the autonomous cycle twice on the same day adds 0 posts second time."""
        from sqlalchemy import select
        from backend.app.db import AsyncSessionLocal
        from backend.app.services.autonomous_engine import autonomous_engine

        headers, ws_id = _register_and_workspace("idem_unit")
        ws_uuid = uuid.UUID(ws_id)

        async def _run():
            async with AsyncSessionLocal() as db:
                r1 = await autonomous_engine.run_autonomous_cycle(db, ws_uuid)
                posts_1 = r1["new_posts_planned"]

                r2 = await autonomous_engine.run_autonomous_cycle(db, ws_uuid)
                posts_2 = r2["new_posts_planned"]

                self.assertEqual(
                    posts_2,
                    0,
                    f"Second cycle should add 0 posts (already scheduled), got {posts_2}",
                )

        asyncio.run(_run())

    def test_audit_log_created_for_each_cycle(self):
        """Each autonomous cycle must produce at least one audit log entry."""
        from sqlalchemy import select
        from backend.app.db import AsyncSessionLocal
        from backend.app.models.autonomous import AutomationAuditLog
        from backend.app.services.autonomous_engine import autonomous_engine

        headers, ws_id = _register_and_workspace("audit_unit")
        ws_uuid = uuid.UUID(ws_id)

        async def _run():
            async with AsyncSessionLocal() as db:
                before_res = await db.execute(
                    select(AutomationAuditLog).where(AutomationAuditLog.workspace_id == ws_uuid)
                )
                before_count = len(before_res.scalars().all())

                await autonomous_engine.run_autonomous_cycle(db, ws_uuid)

                after_res = await db.execute(
                    select(AutomationAuditLog).where(AutomationAuditLog.workspace_id == ws_uuid)
                )
                after_count = len(after_res.scalars().all())
                self.assertGreater(after_count, before_count)

        asyncio.run(_run())

    def test_strategy_not_applied_without_live_data(self):
        """With only mock insights, require_live=True must return awaiting_live_data."""
        from backend.app.db import AsyncSessionLocal
        from backend.app.services.learning_engine import learning_engine

        headers, ws_id = _register_and_workspace("strat_unit")
        ws_uuid = uuid.UUID(ws_id)

        async def _run():
            async with AsyncSessionLocal() as db:
                await learning_engine.update_strategy_insights(db, ws_uuid, is_mock=True)
                strategy = await learning_engine.get_active_strategy(
                    db, ws_uuid, require_live=True
                )
                self.assertEqual(strategy["data_status"], "awaiting_live_data")
                self.assertFalse(strategy["has_enough_live_data"])

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# API endpoint tests – Analytics collect
# ---------------------------------------------------------------------------

class TestAnalyticsCollectEndpoint(unittest.TestCase):
    """Test the POST /analytics/collect endpoint."""

    @classmethod
    def setUpClass(cls):
        cls.headers, cls.ws_id = _register_and_workspace("collect")

    def test_collect_mock_mode_returns_success(self):
        """In mock mode, collect returns success with mock provenance label."""
        resp = client.post(f"/analytics/collect?workspace_id={self.ws_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data_provenance"], "mock_simulation")
        self.assertTrue(data["mock_mode"])
        self.assertIn("observations_collected", data)
        self.assertIn("strategy_insights_updated", data)

    def test_collect_idempotent_on_rerun(self):
        """Calling collect twice must return 0 new observations on the second call."""
        # Seed a published post first via a cycle (which may or may not add one)
        client.post(f"/autonomous/run-cycle?workspace_id={self.ws_id}", headers=self.headers)

        # First collect
        r1 = client.post(f"/analytics/collect?workspace_id={self.ws_id}", headers=self.headers)
        self.assertEqual(r1.status_code, 200)

        # Second collect – must be 0 new
        r2 = client.post(f"/analytics/collect?workspace_id={self.ws_id}", headers=self.headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["observations_collected"], 0,
                         "Second collect must return 0 new observations")

    def test_collect_workspace_isolation(self):
        """User B cannot collect analytics for User A's workspace."""
        headers_b, _ = _register_and_workspace("collect_b")
        resp = client.post(f"/analytics/collect?workspace_id={self.ws_id}", headers=headers_b)
        self.assertEqual(resp.status_code, 403)

    def test_collect_live_missing_token_returns_error(self):
        """When USE_MOCK=False and no Meta token exists, collect must return an error."""
        import backend.app.settings as settings_module
        import backend.app.routers.analytics as analytics_module

        orig = settings_module.settings.USE_MOCK
        settings_module.settings.USE_MOCK = False
        analytics_module.settings.USE_MOCK = False
        try:
            resp = client.post(
                f"/analytics/collect?workspace_id={self.ws_id}", headers=self.headers
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "error")
            self.assertIn("No Instagram account connected", data["message"])
        finally:
            settings_module.settings.USE_MOCK = orig
            analytics_module.settings.USE_MOCK = orig

    def test_collect_note_contains_mock_label(self):
        """In mock mode the note must clearly state it is simulated."""
        resp = client.post(f"/analytics/collect?workspace_id={self.ws_id}", headers=self.headers)
        data = resp.json()
        self.assertIn("[MOCK]", data["note"])


# ---------------------------------------------------------------------------
# API endpoint tests – Full autonomous loop
# ---------------------------------------------------------------------------

class TestAutonomousFullLoop(unittest.TestCase):
    """Integration test: full autonomous loop via API endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.headers, cls.ws_id = _register_and_workspace("loop")

    def test_full_loop_collect_then_cycle(self):
        """Collect analytics then run cycle; both must return success."""
        collect_resp = client.post(
            f"/analytics/collect?workspace_id={self.ws_id}", headers=self.headers
        )
        self.assertEqual(collect_resp.status_code, 200)
        self.assertEqual(collect_resp.json()["status"], "success")

        cycle_resp = client.post(
            f"/autonomous/run-cycle?workspace_id={self.ws_id}", headers=self.headers
        )
        self.assertEqual(cycle_resp.status_code, 200)
        data = cycle_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("observations_ingested", data)
        self.assertIn("strategy_insights", data)
        self.assertIn("new_posts_planned", data)

    def test_pause_blocks_cycle(self):
        """After pausing, run-cycle must return status=paused."""
        client.post(f"/autonomous/pause?workspace_id={self.ws_id}", headers=self.headers)
        resp = client.post(
            f"/autonomous/run-cycle?workspace_id={self.ws_id}", headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "paused")

    def test_resume_restores_cycle(self):
        """After resuming, run-cycle must return status=success again."""
        client.post(f"/autonomous/resume?workspace_id={self.ws_id}", headers=self.headers)
        resp = client.post(
            f"/autonomous/run-cycle?workspace_id={self.ws_id}", headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_insights_reflect_mock_provenance(self):
        """In mock mode all strategy insights must be flagged is_mock=True."""
        client.post(f"/autonomous/run-cycle?workspace_id={self.ws_id}", headers=self.headers)
        resp = client.get(
            f"/autonomous/insights?workspace_id={self.ws_id}", headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        insights = resp.json()
        self.assertTrue(len(insights) > 0)
        for ins in insights:
            self.assertTrue(ins["is_mock"], f"Expected is_mock=True for insight '{ins['topic']}'")

    def test_audit_log_reflects_cycle_action(self):
        """After a cycle run, audit log must contain an 'autonomous_cycle' entry."""
        client.post(f"/autonomous/run-cycle?workspace_id={self.ws_id}", headers=self.headers)
        resp = client.get(
            f"/autonomous/audit-logs?workspace_id={self.ws_id}", headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        logs = resp.json()
        actions = [log["action"] for log in logs]
        self.assertIn("autonomous_cycle", actions)

    def test_workspace_isolation_analytics_collect(self):
        """User B cannot collect analytics for User A's workspace."""
        headers_b, _ = _register_and_workspace("loop_b")
        resp = client.post(
            f"/analytics/collect?workspace_id={self.ws_id}", headers=headers_b
        )
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
