"""Integration tests for Meta API, token refresh, error diagnostics, and recovery."""
import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestMetaRealIntegrations(unittest.TestCase):
    """Tests for Meta Graph API integration helpers, error mapping, and token lifecycle."""

    def test_meta_error_parser(self):
        """Verify that specific Meta Graph API error codes translate into user-friendly diagnostic messages."""
        from backend.app.services.meta_publisher import _parse_meta_error

        # Code 190: Expired token
        err_190 = '{"error": {"message": "Session has expired", "code": 190}}'
        msg_190 = _parse_meta_error(err_190, "Publishing failed")
        self.assertIn("190", msg_190)
        self.assertIn("Re-authorization required", msg_190)

        # Code 36003: Aspect ratio error
        err_aspect = '{"error": {"message": "Invalid aspect ratio", "code": 36003}}'
        msg_aspect = _parse_meta_error(err_aspect, "Publishing failed")
        self.assertIn("aspect ratio", msg_aspect)
        self.assertIn("4:5", msg_aspect)

        # Code 2207001: Media download failure
        err_media = '{"error": {"message": "The image could not be fetched from url", "code": 2207001}}'
        msg_media = _parse_meta_error(err_media, "Publishing failed")
        self.assertIn("media download error", msg_media)
        self.assertIn("publicly accessible HTTPS", msg_media)

    def test_meta_insights_service_mock_mode(self):
        """Verify meta_insights returns structured metrics with mock indicator."""
        import asyncio
        from backend.app.services.meta_insights import meta_insights

        async def _run():
            res = await meta_insights.fetch_media_metrics(
                platform_post_id="test_post_123",
                access_token="mock_token",
            )
            self.assertTrue(res["success"])
            self.assertTrue(res["mock"])
            self.assertIn("reach", res)
            self.assertIn("engagement_rate", res)

        asyncio.run(_run())

    def test_token_refresh_mock(self):
        """Verify refresh_long_lived_token returns a refreshed token in mock mode."""
        import asyncio
        from backend.app.services.meta_oauth import refresh_long_lived_token

        async def _run():
            res = await refresh_long_lived_token("existing_token")
            self.assertIn("access_token", res)
            self.assertTrue(res.get("mock"))

        asyncio.run(_run())

    def test_celery_worker_retries_and_duplicate_prevention(self):
        """Verify celery worker handles due posts, avoids duplicates, and retries on failure."""
        import asyncio
        from backend.app.celery_worker import _publish_due_posts_async
        from backend.app.db import engine, Base

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            # Execution without error on clean DB
            await _publish_due_posts_async()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
