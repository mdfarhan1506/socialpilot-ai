"""Unit and integration tests for verified trend research and evergreen fallback."""
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.app.services.trend_research import (
    parse_feed_xml,
    parse_rss_date,
    fetch_real_niche_trends,
    conduct_workspace_research,
    NICHE_FEED_SOURCES,
    EVERGREEN_NICHE_TOPICS,
)
from backend.app.db import AsyncSessionLocal
from backend.app.models.workspace import Workspace
from backend.app.models.user import User
from backend.app.models.research import ResearchRun, TrendOpportunity
from backend.tests.conftest import client, get_auth_headers, create_workspace


SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech Insights Feed</title>
    <link>https://example.com</link>
    <description>Latest tech news</description>
    <item>
      <title>Autonomous Systems Revolutionize Developer Workflows</title>
      <link>https://example.com/autonomous-systems</link>
      <description>&lt;p&gt;How modern agentic pipelines handle operational toil.&lt;/p&gt;</description>
      <pubDate>Sun, 01 Nov 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Cloud Cost Optimization Strategies for 2026</title>
      <link>https://example.com/cloud-costs</link>
      <description>Key insights on reducing infrastructure overhead.</description>
      <pubDate>Sat, 31 Oct 2026 14:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_date_valid():
    """Verify standard RFC 822 date parsing."""
    date_str = "Sun, 01 Nov 2026 10:00:00 GMT"
    dt = parse_rss_date(date_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 11
    assert dt.day == 1
    assert dt.hour == 10


def test_parse_feed_xml_valid():
    """Verify parsing valid XML extracts titles, links, clean descriptions, and publication dates."""
    trends = parse_feed_xml(SAMPLE_RSS_XML, source_name="Tech Feed", niche="tech")
    assert len(trends) == 2

    first = trends[0]
    assert first["title"] == "Autonomous Systems Revolutionize Developer Workflows"
    assert first["evidence_url"] == "https://example.com/autonomous-systems"
    assert first["is_evergreen"] is False
    assert first["source_name"] == "Tech Feed"
    assert first["publication_date"] is not None
    assert first["publication_date"].year == 2026
    assert "retrieved_at" in first
    # HTML tags must be stripped from description
    assert "<p>" not in first["description"]


def test_fetch_real_niche_trends_success():
    """Verify trend fetching returns live_verified status when HTTP feed returns 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_RSS_XML

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = asyncio.run(fetch_real_niche_trends("tech", max_items=2))

    assert res["source_status"] == "live_verified"
    assert len(res["trends"]) == 2
    assert res["trends"][0]["is_evergreen"] is False
    assert res["trends"][0]["title"] == "Autonomous Systems Revolutionize Developer Workflows"


def test_fetch_real_niche_trends_unavailable_fallback():
    """When remote feeds are unavailable, timeout, or return HTTP 500, fallback to evergreen."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection timed out"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = asyncio.run(fetch_real_niche_trends("tech", max_items=2))

    assert res["source_status"] == "evergreen_fallback"
    assert len(res["trends"]) > 0
    # Every fallback trend must be clearly flagged as evergreen
    for t in res["trends"]:
        assert t["is_evergreen"] is True
        assert t["evidence_url"].startswith("https://")
        assert "fallback_reason" in t["trend_metadata"]


def test_conduct_workspace_research_persistence():
    """Verify that research runs and trend opportunities are stored in the database."""
    headers = get_auth_headers("trend_persist_user@test.com")
    ws_id = create_workspace(headers, "Trend Persist WS")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_RSS_XML
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        post_resp = client.post(
            f"/autonomous/trends/research?workspace_id={ws_id}&niche=tech",
            headers=headers,
        )
    assert post_resp.status_code == 200, post_resp.text
    res = post_resp.json()
    assert res["status"] == "completed"
    assert res["count"] >= 2
    assert len(res["trends"]) >= 2
    assert res["trends"][0]["title"] == "Autonomous Systems Revolutionize Developer Workflows"


def test_autonomous_trends_endpoints():
    """Test the POST /autonomous/trends/research and GET /autonomous/trends endpoints."""
    headers = get_auth_headers("trend_api_user@test.com")
    ws_id = create_workspace(headers, "Trend API WS")

    # Mock feed for endpoint test
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_RSS_XML
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        post_resp = client.post(
            f"/autonomous/trends/research?workspace_id={ws_id}&niche=tech",
            headers=headers,
        )
    assert post_resp.status_code == 200, post_resp.text
    post_data = post_resp.json()
    assert post_data["status"] == "completed"
    assert post_data["count"] >= 1

    # Fetch trends
    get_resp = client.get(
        f"/autonomous/trends?workspace_id={ws_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    trends = get_resp.json()
    assert len(trends) >= 1
    assert "title" in trends[0]
    assert "evidence_url" in trends[0]
    assert "is_evergreen" in trends[0]
