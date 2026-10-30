"""Tests for the Celery worker task (without a live Redis broker)."""
import os
import unittest

# Env vars must be set before any app import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")


class TestCeleryWorkerRegistration(unittest.TestCase):
    """Verify the worker module loads and the task is registered correctly."""

    def test_worker_import(self):
        from backend.app.celery_worker import worker
        self.assertIsNotNone(worker)

    def test_task_registered(self):
        from backend.app.celery_worker import worker
        self.assertIn("app.celery_worker.publish_due_posts", worker.tasks)

    def test_publish_task_callable(self):
        """The task function itself must be importable and callable."""
        from backend.app.celery_worker import publish_due_posts
        self.assertTrue(callable(publish_due_posts))

    def test_beat_schedule_configured(self):
        from backend.app.celery_worker import worker
        beat = worker.conf.beat_schedule
        self.assertIn("publish-due-posts", beat)
        self.assertEqual(beat["publish-due-posts"]["task"], "app.celery_worker.publish_due_posts")


class TestPublishDuePostsTask(unittest.TestCase):
    """Test the async publish logic directly (mocked DB interaction)."""

    def test_async_publish_logic_runs_without_redis(self):
        """Run the async internals directly (not via Celery broker) to confirm
        they execute without errors when no posts are due."""
        import asyncio

        async def _run():
            from backend.app.celery_worker import _publish_due_posts_async
            # Should complete without error (zero due posts in test DB)
            await _publish_due_posts_async()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
