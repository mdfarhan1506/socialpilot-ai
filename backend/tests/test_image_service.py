"""Unit and integration tests for topic-specific image generation and validation."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.app.services import image_service
from backend.app.services.autonomous_engine import autonomous_engine
from backend.app.settings import settings
from backend.tests.conftest import client, get_auth_headers


def test_stock_image_selection_niche_matching():
    """Verify that niche keywords map to corresponding curated topic images."""
    tech_res = image_service.get_stock_image_for_topic("tech", "artificial intelligence")
    assert tech_res["category"] == "tech"
    assert "metadata" in tech_res
    assert tech_res["metadata"]["is_ai_generated"] is False
    assert tech_res["metadata"]["aspect_ratio"] == 1.0

    fitness_res = image_service.get_stock_image_for_topic("fitness", "strength training")
    assert fitness_res["category"] == "fitness"

    food_res = image_service.get_stock_image_for_topic("food & cooking", "healthy dinner")
    assert food_res["category"] == "food"


def test_stock_image_satisfies_instagram_publishing():
    """Verify that all images in the stock library pass Instagram media validation."""
    for category, urls in image_service.NICHE_STOCK_LIBRARY.items():
        for url in urls:
            val = autonomous_engine.validate_media(url, caption="Valid post caption #test")
            assert val["valid"] is True, f"Failed for {category} URL {url}: {val.get('reason')}"
            assert url.startswith("https://")


def test_generate_topic_image_fallback_when_mock_or_no_key(monkeypatch):
    """When USE_MOCK is True or OPENAI_API_KEY is empty, gracefully return stock library."""
    monkeypatch.setattr(settings, "USE_MOCK", True)
    res = asyncio.run(image_service.generate_topic_image(
        prompt="A photo of modern cloud architecture",
        niche="tech",
        topic="cloud computing",
    ))
    assert res["source"] == "stock_library"
    assert res["metadata"]["is_ai_generated"] is False
    assert res["url"].startswith("https://images.unsplash.com")


def test_generate_topic_image_openai_success(monkeypatch):
    """When OpenAI is enabled and credentials exist, mock DALL-E client and return real format."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-fake-key-for-test")

    mock_response = MagicMock()
    mock_data = MagicMock()
    mock_data.url = "https://images.openai.com/dalle3/test_generated_image.png"
    mock_data.revised_prompt = "A high-end modern computer chip"
    mock_response.data = [mock_data]

    mock_client = MagicMock()
    mock_client.images.generate = AsyncMock(return_value=mock_response)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        res = asyncio.run(image_service.generate_topic_image(
            prompt="High performance computing chip",
            niche="tech",
            topic="hardware",
            prefer_ai=True,
        ))

    assert res["source"] == "openai_dalle3"
    assert res["metadata"]["is_ai_generated"] is True
    assert res["url"] == "https://images.openai.com/dalle3/test_generated_image.png"
    assert res["metadata"]["format"] == "image/png"


def test_generate_topic_image_openai_failure_falls_back(monkeypatch):
    """When OpenAI DALL-E fails with an API error, fallback to stock image with clear reason."""
    monkeypatch.setattr(settings, "USE_MOCK", False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-fake-key-for-test")

    mock_client = MagicMock()
    mock_client.images.generate = AsyncMock(side_effect=RuntimeError("Billing limit reached"))

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        res = asyncio.run(image_service.generate_topic_image(
            prompt="High performance computing chip",
            niche="tech",
            topic="hardware",
            prefer_ai=True,
        ))

    assert res["source"] == "stock_library"
    assert res["metadata"]["is_ai_generated"] is False
    assert "Billing limit reached" in res.get("fallback_reason", "")


def test_content_generate_image_endpoint():
    """Test the POST /content/generate-image router endpoint."""
    headers = get_auth_headers("img_test_user@test.com")
    resp = client.post(
        "/content/generate-image",
        json={
            "prompt": "Morning espresso on rustic table",
            "niche": "food",
            "topic": "coffee culture",
            "prefer_ai": False,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "url" in data
    assert data["url"].startswith("https://")
    assert data["category"] == "food"
    assert data["source"] in ("openai_dalle3", "stock_library")
    assert "metadata" in data


def test_content_generate_image_endpoint_validation():
    """Test validation errors on empty image generation request."""
    headers = get_auth_headers("img_test_user2@test.com")
    resp = client.post(
        "/content/generate-image",
        json={"prompt": "", "niche": None, "topic": None},
        headers=headers,
    )
    assert resp.status_code == 400
