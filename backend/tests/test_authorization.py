"""Cross-endpoint workspace authorization tests.

Verifies that a user who is NOT a member of a workspace cannot:
- Create/list brands in that workspace
- Create/list scheduled posts in that workspace
- Create/list comments in that workspace
- View analytics for that workspace
"""
import unittest
from datetime import datetime, timedelta, timezone
from backend.tests.conftest import client, get_auth_headers, create_workspace


class TestWorkspaceAuthorization(unittest.TestCase):
    """Non-member should get 403 or 404 for every workspace-scoped endpoint."""

    @classmethod
    def setUpClass(cls):
        cls.owner_headers = get_auth_headers("authz_owner@test.com")
        cls.intruder_headers = get_auth_headers("authz_intruder@test.com")
        cls.workspace_id = create_workspace(cls.owner_headers, "Authz WS")

    def test_brand_create_blocked(self):
        resp = client.post(
            "/brand/",
            json={
                "workspace_id": self.workspace_id,
                "niche": "Hack",
                "target_audience": "Nobody",
                "tone": "Evil",
            },
            headers=self.intruder_headers,
        )
        self.assertIn(resp.status_code, [403, 404])

    def test_brand_list_blocked(self):
        resp = client.get(
            f"/brand/?workspace_id={self.workspace_id}",
            headers=self.intruder_headers,
        )
        self.assertIn(resp.status_code, [403, 404])

    def test_schedule_create_blocked(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
        resp = client.post(
            "/schedule/",
            json={"caption": "Hack post", "workspace_id": self.workspace_id, "scheduled_time": future},
            headers=self.intruder_headers,
        )
        self.assertIn(resp.status_code, [403, 404])

    def test_schedule_list_blocked(self):
        resp = client.get(
            f"/schedule/?workspace_id={self.workspace_id}",
            headers=self.intruder_headers,
        )
        self.assertIn(resp.status_code, [403, 404])

    def test_comment_create_blocked(self):
        resp = client.post(
            "/comments/",
            json={"workspace_id": self.workspace_id, "text": "Sneaky comment"},
            headers=self.intruder_headers,
        )
        self.assertIn(resp.status_code, [403, 404])

    def test_comment_list_blocked(self):
        resp = client.get(
            f"/comments/?workspace_id={self.workspace_id}",
            headers=self.intruder_headers,
        )
        self.assertIn(resp.status_code, [403, 404])

    def test_analytics_blocked(self):
        resp = client.get(
            f"/analytics/?workspace_id={self.workspace_id}",
            headers=self.intruder_headers,
        )
        # Analytics now enforces workspace membership
        self.assertIn(resp.status_code, [403, 404])


if __name__ == "__main__":
    unittest.main()
