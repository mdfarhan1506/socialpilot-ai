"""Tests for Meta OAuth and publishing router (mock mode only).

Security checks:
- OAuth callback must never return the raw access token.
- Publishing uses stored token, not user-submitted raw token.
- Publish without linking first must fail with 400.
"""
import unittest
from backend.tests.conftest import client, get_auth_headers


class TestMetaStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("meta_user@test.com")

    def test_status_returns_mock_mode(self):
        resp = client.get("/meta/status", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("mock_mode", data)
        self.assertTrue(data["mock_mode"])

    def test_status_shows_account_linked(self):
        resp = client.get("/meta/status", headers=self.headers)
        data = resp.json()
        self.assertIn("account_linked", data)

    def test_status_requires_auth(self):
        resp = client.get("/meta/status")
        self.assertEqual(resp.status_code, 401)


class TestMetaOAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("meta_oauth@test.com")

    def test_oauth_start_returns_url_in_mock(self):
        resp = client.get("/meta/oauth/start", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("mock_mode"), "Expected mock_mode=True in test environment")
        self.assertIn("oauth_url", data)
        self.assertIn("facebook.com", data["oauth_url"])
        self.assertIn("dialog/oauth", data["oauth_url"])

    def test_oauth_callback_stores_token_securely(self):
        """Callback must store token and NEVER return it in the response."""
        resp = client.get("/meta/oauth/callback?code=fake_code", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("mock_mode"))
        self.assertTrue(data.get("token_stored"), "Token must be stored in DB")
        self.assertTrue(data.get("account_linked"))
        self.assertEqual(data.get("ig_user_id"), "MOCK_IG_USER_ID")
        # SECURITY: raw access_token must NOT appear in response
        self.assertNotIn("access_token", data, "Raw access_token must never be in response")

    def test_oauth_requires_auth(self):
        resp = client.get("/meta/oauth/start")
        self.assertEqual(resp.status_code, 401)


class TestMetaPublish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("meta_pub@test.com")
        # Link account first via OAuth callback
        client.get("/meta/oauth/callback?code=fake_code", headers=cls.headers)

        cls.unlinked_headers = get_auth_headers("meta_unlinked@test.com")

    def test_publish_uses_stored_token(self):
        """Publish endpoint no longer requires raw token in request body."""
        resp = client.post(
            "/meta/publish",
            json={
                "image_url": "https://example.com/image.jpg",
                "caption": "Test post #socialpilot",
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data.get("mock"), "Publish response must be labeled as mock")
        self.assertIn("[MOCK]", data.get("message", ""), "Mock message must contain [MOCK] label")
        self.assertEqual(data.get("status"), "published")

    def test_publish_without_linking_fails(self):
        """Publishing without completing OAuth first must return 400."""
        resp = client.post(
            "/meta/publish",
            json={"image_url": "https://example.com/img.jpg", "caption": "no link"},
            headers=self.unlinked_headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No Instagram account linked", resp.json()["detail"])

    def test_publish_requires_auth(self):
        resp = client.post(
            "/meta/publish",
            json={"image_url": "x", "caption": "x"},
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
