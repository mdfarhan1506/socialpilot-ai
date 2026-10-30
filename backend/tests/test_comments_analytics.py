"""Tests for comments and analytics endpoints."""
import unittest
from backend.tests.conftest import client, get_auth_headers, create_workspace


class TestComments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("comments_user@test.com")
        cls.workspace_id = create_workspace(cls.headers, "Comments WS")

    def test_create_comment(self):
        resp = client.post(
            "/comments/",
            json={"workspace_id": self.workspace_id, "text": "Great post!", "post_id": "post_001"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertEqual(data["text"], "Great post!")
        self.assertEqual(data["post_id"], "post_001")

    def test_list_comments_for_workspace(self):
        client.post(
            "/comments/",
            json={"workspace_id": self.workspace_id, "text": "Listed comment", "post_id": "post_002"},
            headers=self.headers,
        )
        resp = client.get(f"/comments/?workspace_id={self.workspace_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        texts = [c["text"] for c in resp.json()]
        self.assertIn("Listed comment", texts)

    def test_filter_comments_by_post(self):
        client.post(
            "/comments/",
            json={"workspace_id": self.workspace_id, "text": "Post-specific", "post_id": "post_xyz"},
            headers=self.headers,
        )
        resp = client.get(
            f"/comments/?workspace_id={self.workspace_id}&post_id=post_xyz",
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        texts = [c["text"] for c in resp.json()]
        self.assertIn("Post-specific", texts)
        # Should not contain comments from other post IDs
        for c in resp.json():
            self.assertEqual(c["post_id"], "post_xyz")

    def test_comment_requires_auth(self):
        resp = client.post(
            "/comments/",
            json={"workspace_id": self.workspace_id, "text": "No auth"},
        )
        self.assertEqual(resp.status_code, 401)


class TestAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("analytics_user@test.com")
        cls.workspace_id = create_workspace(cls.headers, "Analytics WS")

    def test_analytics_returns_workspace_data(self):
        resp = client.get(f"/analytics/?workspace_id={self.workspace_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("scheduled_posts", data)
        self.assertIn("total_comments", data)
        self.assertIn("mock_mode", data)

    def test_analytics_mock_mode_labeled(self):
        resp = client.get(f"/analytics/?workspace_id={self.workspace_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # In test env mock_mode should be True
        self.assertTrue(data["mock_mode"])
        self.assertIn("[MOCK]", data.get("estimated_reach", ""))

    def test_analytics_counts_own_data(self):
        """Scheduled posts and comments for this workspace should count correctly."""
        from datetime import datetime, timedelta, timezone
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        # Add a scheduled post
        client.post(
            "/schedule/",
            json={"caption": "Analytics test post", "workspace_id": self.workspace_id, "scheduled_time": future},
            headers=self.headers,
        )
        # Add a comment
        client.post(
            "/comments/",
            json={"workspace_id": self.workspace_id, "text": "Analytics comment"},
            headers=self.headers,
        )
        resp = client.get(f"/analytics/?workspace_id={self.workspace_id}", headers=self.headers)
        data = resp.json()
        self.assertGreaterEqual(data["scheduled_posts"], 1)
        self.assertGreaterEqual(data["total_comments"], 1)

    def test_analytics_requires_auth(self):
        resp = client.get(f"/analytics/?workspace_id={self.workspace_id}")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
