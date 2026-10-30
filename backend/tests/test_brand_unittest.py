import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

class TestBrandCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a user
        resp = client.post("/auth/register", json={"email": "brand@test.com", "password": "test1234"})
        assert resp.status_code == 200
        cls.token = resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        # Create a workspace
        resp = client.post("/workspace/", json={"name": "Test Workspace"}, headers=cls.headers)
        assert resp.status_code == 200
        cls.workspace_id = resp.json()["id"]

    def test_create_and_get_brand(self):
        brand_data = {
            "workspace_id": self.workspace_id,
            "niche": "Fitness",
            "target_audience": "Young adults",
            "tone": "Motivational",
            "brand_voice": "Energetic",
            "content_preferences": "Video"
        }
        # Create brand
        resp = client.post("/brand/", json=brand_data, headers=self.headers)
        self.assertEqual(resp.status_code, 201)
        brand_id = resp.json()["id"]
        # Get brand
        resp = client.get(f"/brand/{brand_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["niche"], "Fitness")
        # List brands
        resp = client.get(f"/brand/?workspace_id={self.workspace_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any(b["id"] == brand_id for b in resp.json()))

if __name__ == "__main__":
    unittest.main()
