"""Tests for the scheduling router."""
import unittest
from datetime import datetime, timedelta, timezone
from backend.tests.conftest import client, get_auth_headers, create_workspace


def future_time(minutes=60) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class TestScheduling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("sched_user@test.com")
        cls.other_headers = get_auth_headers("sched_other@test.com")
        cls.workspace_id = create_workspace(cls.headers, "Sched WS")

    def _create_post(self, caption="Test caption", minutes=120):
        return client.post(
            "/schedule/",
            json={
                "caption": caption,
                "workspace_id": self.workspace_id,
                "scheduled_time": future_time(minutes),
            },
            headers=self.headers,
        )

    def test_create_scheduled_post(self):
        resp = self._create_post("My post")
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertEqual(data["status"], "scheduled")
        self.assertEqual(data["caption"], "My post")

    def test_list_scheduled_posts(self):
        self._create_post("Listed post", minutes=180)
        resp = client.get(f"/schedule/?workspace_id={self.workspace_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        captions = [p["caption"] for p in resp.json()]
        self.assertIn("Listed post", captions)

    def test_past_scheduled_time_rejected(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        resp = client.post(
            "/schedule/",
            json={"caption": "Past", "workspace_id": self.workspace_id, "scheduled_time": past},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_duplicate_schedule_rejected(self):
        t = future_time(240)
        client.post(
            "/schedule/",
            json={"caption": "Dup post", "workspace_id": self.workspace_id, "scheduled_time": t},
            headers=self.headers,
        )
        resp = client.post(
            "/schedule/",
            json={"caption": "Dup post", "workspace_id": self.workspace_id, "scheduled_time": t},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 409)

    def test_cancel_schedule(self):
        resp = self._create_post("To cancel", minutes=300)
        self.assertEqual(resp.status_code, 201)
        post_id = resp.json()["id"]
        del_resp = client.delete(f"/schedule/{post_id}", headers=self.headers)
        self.assertEqual(del_resp.status_code, 204)

    def test_cancel_other_users_post_forbidden(self):
        resp = self._create_post("Forbidden cancel", minutes=360)
        self.assertEqual(resp.status_code, 201)
        post_id = resp.json()["id"]
        del_resp = client.delete(f"/schedule/{post_id}", headers=self.other_headers)
        self.assertEqual(del_resp.status_code, 403)

    def test_schedule_requires_auth(self):
        resp = client.post(
            "/schedule/",
            json={"caption": "No auth", "workspace_id": self.workspace_id, "scheduled_time": future_time()},
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
