"""Tests for authentication endpoints."""
import unittest
from backend.tests.conftest import client


class TestAuthRegister(unittest.TestCase):
    def test_register_new_user(self):
        resp = client.post("/auth/register", json={"email": "auth_new@test.com", "password": "secure123"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("access_token", resp.json())

    def test_register_duplicate_user(self):
        client.post("/auth/register", json={"email": "auth_dup@test.com", "password": "secure123"})
        resp = client.post("/auth/register", json={"email": "auth_dup@test.com", "password": "secure123"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already registered", resp.json()["detail"].lower())

    def test_register_short_password_is_accepted(self):
        # We do not enforce min-length server-side currently; just verify it doesn't 500
        resp = client.post("/auth/register", json={"email": "auth_short@test.com", "password": "a"})
        self.assertIn(resp.status_code, [200, 400, 422])


class TestAuthLogin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client.post("/auth/register", json={"email": "auth_login@test.com", "password": "loginpass"})

    def test_valid_login(self):
        resp = client.post(
            "/auth/login",
            data={"username": "auth_login@test.com", "password": "loginpass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("access_token", resp.json())

    def test_wrong_password(self):
        resp = client.post(
            "/auth/login",
            data={"username": "auth_login@test.com", "password": "wrongpass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_unknown_user(self):
        resp = client.post(
            "/auth/login",
            data={"username": "nobody@test.com", "password": "whatever"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_protected_route_without_token(self):
        resp = client.get("/workspace/")
        self.assertEqual(resp.status_code, 401)

    def test_protected_route_with_invalid_token(self):
        resp = client.get("/workspace/", headers={"Authorization": "Bearer INVALID_TOKEN"})
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
