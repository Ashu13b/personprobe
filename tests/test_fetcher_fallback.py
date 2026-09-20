"""Tests for URL fetcher strategy hierarchy and mobile browser fallback."""
from unittest.mock import patch, MagicMock
from engine.fetcher import fetch_url, check_liveness, FetchResult


def test_fetch_url_direct_success():
    with patch("engine.fetcher._direct_fetch") as mock_direct:
        mock_direct.return_value = ("Extracted full text of the article.", "<html>...</html>", "https://example.com")
        res = fetch_url("https://example.com/article")
        assert res.method == "direct"
        assert res.blocked is False
        assert "Extracted full text" in res.text


def test_fetch_url_mobile_bridge_fallback():
    # Direct fetch returns None (e.g. 403 / Cloudflare blocked)
    with patch("engine.fetcher._direct_fetch", return_value=None), \
         patch("engine.fetcher.is_mobile_bridge_available", return_value=True), \
         patch("engine.fetcher.fetch_via_mobile_bridge") as mock_bridge:

        mock_bridge.return_value = {
            "title": "Mobile Scraped Page",
            "text": "Detailed contents extracted through the mobile phone browser bridge bypassing Cloudflare. " * 3,
            "url": "https://example.com/blocked",
            "has_captcha": False,
        }

        res = fetch_url("https://example.com/blocked")
        assert res.method == "mobile_browser"
        assert res.blocked is False
        assert "Detailed contents" in res.text


def test_fetch_url_browser_server_fallback_when_mobile_unavailable():
    with patch("engine.fetcher._direct_fetch", return_value=None), \
         patch("engine.fetcher.is_mobile_bridge_available", return_value=False), \
         patch("engine.fetcher._try_browser_server") as mock_browser:

        mock_browser.return_value = FetchResult("https://example.com", "Browser server text content.", method="browser")
        res = fetch_url("https://example.com")
        assert res.method == "browser"
        assert res.blocked is False


def test_check_liveness_recovers_blocked_via_mobile_bridge():
    with patch("engine.fetcher.requests.get") as mock_get, \
         patch("engine.fetcher.is_mobile_bridge_available", return_value=True), \
         patch("engine.fetcher.fetch_via_mobile_bridge") as mock_bridge:

        resp = MagicMock()
        resp.status_code = 403
        resp.url = "https://example.com/cloudflare-protected"
        mock_get.return_value = resp

        mock_bridge.return_value = {
            "title": "Loaded",
            "text": "Content loaded on mobile device successfully " * 5,
            "has_captcha": False,
        }

        status, archive = check_liveness("https://example.com/cloudflare-protected")
        assert status == "alive"
        assert archive is None
