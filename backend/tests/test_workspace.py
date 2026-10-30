"""Tests for workspace endpoints."""
import unittest
from backend.tests.conftest import client, get_auth_headers


class TestWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("ws_user@test.com")
        cls.other_headers = get_auth_headers("ws_other@test.com")

    def test_create_workspace(self):
        resp = client.post("/workspace/", json={"name": "My WS"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "My WS")

    def test_list_workspaces(self):
        client.post("/workspace/", json={"name": "Listed WS"}, headers=self.headers)
        resp = client.get("/workspace/", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)
        names = [w["name"] for w in resp.json()]
        self.assertIn("Listed WS", names)

    def test_unauthenticated_create_workspace(self):
        resp = client.post("/workspace/", json={"name": "No auth"})
        self.assertEqual(resp.status_code, 401)

    def test_workspace_isolation(self):
        """A user should not see another user's workspaces."""
        client.post("/workspace/", json={"name": "Private WS"}, headers=self.headers)
        resp = client.get("/workspace/", headers=self.other_headers)
        self.assertEqual(resp.status_code, 200)
        names = [w["name"] for w in resp.json()]
        self.assertNotIn("Private WS", names)


if __name__ == "__main__":
    unittest.main()
