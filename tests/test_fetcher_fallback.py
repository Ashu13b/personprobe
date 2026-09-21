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


def test_fetch_telemetry_records_and_advises(tmp_path, monkeypatch):
    from engine import fetch_telemetry as ft

    log = tmp_path / "telemetry.jsonl"
    monkeypatch.setattr(ft, "LOG_PATH", log)

    ft.record("phone", "https://example.test/page", status="ok", latency_ms=812)
    ft.record("http", "https://example.test/page", status=429, latency_ms=250, throttled=True)

    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    import json as _json
    first = _json.loads(lines[0])
    assert first["transport"] == "phone"
    assert first["latency_ms"] == 812
    assert first["host"] == "example.test"

    assert ft.recent_throttles(host="example.test") == 1
    assert ft.suggest_delay("https://example.test/page") >= ft.THROTTLE_DELAY_S
    assert ft.suggest_delay("https://clean.test/page") == ft.DEFAULT_DELAY_S

    with ft.timed("http", "https://example.test/slow"):
        pass
    assert len(log.read_text().strip().splitlines()) == 3


def test_fetch_telemetry_cooldown_and_recheck(tmp_path, monkeypatch):
    from engine import fetch_telemetry as ft
    monkeypatch.setattr(ft, "LOG_PATH", tmp_path / "t.jsonl")

    ft.record("phone", "https://walled.test/x", status="ok", latency_ms=100, throttled=True)
    assert ft.wait_time("https://walled.test/y") > 0
    # cooldown delay takes priority over the soft throttle delay
    assert abs(ft.suggest_delay("https://walled.test/y") - ft.wait_time("https://walled.test/y")) < 2
    pend = ft.pending_rechecks()
    assert len(pend) == 1 and pend[0]["host"] == "walled.test" and pend[0]["wait_s"] > 0

    # an old throttle is out of cooldown
    assert ft.wait_time("https://walled.test/y", cooldown_s=0) == 0.0
    assert ft.pending_rechecks(cooldown_s=0) == []
