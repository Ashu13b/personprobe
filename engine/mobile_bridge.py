"""Integration with the OpenScrape Mobile Browser Bridge (100.72.202.86:38765).

Enables PersonProbe to route web scraping through a physical mobile carrier IP via Tailscale,
bypassing Cloudflare, ResearchGate, Elsevier, and anti-bot mitigation that blocks
cloud datacenter IPs. Zero SSH tunnels or port forwarding needed.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Add android-browser directory to sys.path if not present
ANDROID_BROWSER_DIR = Path("/home/ubuntu/Expeei/android-browser")
if ANDROID_BROWSER_DIR.exists() and str(ANDROID_BROWSER_DIR) not in sys.path:
    sys.path.insert(0, str(ANDROID_BROWSER_DIR))

logger = logging.getLogger(__name__)

_client: Optional[Any] = None
_bridge_checked: bool = False


def get_mobile_client() -> Optional[Any]:
    """Return a singleton MobileBrowserClient instance if available, else None."""
    global _client, _bridge_checked
    if _bridge_checked:
        return _client

    import socket

    # Fast socket pre-check to avoid multi-second urllib connect timeouts when bridge is down
    try:
        s = socket.create_connection(("100.72.202.86", 38765), timeout=0.3)
        s.close()
    except Exception:
        _bridge_checked = True
        _client = None
        return None

    try:
        from openscrape_client import MobileBrowserClient  # type: ignore

        client = MobileBrowserClient()
        status = client.get_status()
        if isinstance(status, dict) and status.get("status") == "ok":
            _client = client
    except Exception as e:
        logger.debug("MobileBrowserClient unavailable: %s", e)
        _client = None

    _bridge_checked = True
    return _client


def is_mobile_bridge_available() -> bool:
    """Check if the physical mobile browser bridge on Tailnet (port 38765) is reachable."""
    try:
        client = get_mobile_client()
        return client is not None
    except Exception:
        return False


def fetch_via_mobile_bridge(
    url: str, wait_seconds: int = 5
) -> Optional[dict[str, Any]]:
    """Navigate and extract DOM text via the mobile scrap browser.

    Returns dict with {"title": str, "text": str, "url": str, "raw_html": str} or None.
    """
    client = get_mobile_client()
    if not client:
        return None

    # Guard physical phone against reserved dummy RFC 2606/6761 test domains (.test, .example, .invalid, .localhost)
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if any(
        hostname == tld.lstrip(".") or hostname.endswith(tld)
        for tld in (".test", ".example", ".invalid", ".localhost")
    ):
        return None

    from .fetch_telemetry import timed, looks_throttled

    with timed("phone", url) as t:
        try:
            res = client.navigate(url, wait_seconds=wait_seconds)
            if res.get("status") == "error":
                logger.debug(
                    "Mobile bridge navigation error for %s: %s", url, res.get("error")
                )
                t.status = "error"
                t.note = str(res.get("error"))[:120]
                return None

            dom = client.extract_dom(include_text=True, include_links=True)
            content = dom.get("content", {})
            text = content.get("text", "").strip()
            captcha = bool(dom.get("has_captcha", False))
            t.status = "ok" if text else "empty"
            walled = looks_throttled(text)
            t.throttled = captcha or walled
            t.note = (
                "captcha"
                if captcha
                else (
                    "throttle text" if walled else ("empty render" if not text else "")
                )
            )
            return {
                "title": dom.get("title", ""),
                "text": text,
                "url": dom.get("url", url),
                "links": content.get("links", []),
                "raw_html": content.get("html", "") or dom.get("html", ""),
                "has_captcha": captcha,
            }
        except Exception as e:
            logger.warning("Failed to fetch %s via mobile bridge: %s", url, e)
            t.status = "exception"
            t.note = str(e)[:120]
            return None


def search_via_mobile_bridge(query: str, max_results: int = 10) -> list[dict[str, str]]:
    """Execute a web search query via the mobile browser bridge (e.g. DDG HTML) to bypass bot-walls.

    Returns list of dicts with {"url": str, "title": str, "snippet": str}.
    """
    if not is_mobile_bridge_available():
        return []

    from urllib.parse import quote_plus, parse_qs, urlsplit

    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    res = fetch_via_mobile_bridge(search_url, wait_seconds=2)
    if not res:
        return []

    links = res.get("links", [])
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for lk in links:
        href = lk.get("href", "")
        text = lk.get("text", "").strip()
        if not href or href.startswith("https://html.duckduckgo.com"):
            continue

        actual_url = href
        if "uddg=" in href:
            qs = parse_qs(urlsplit(href).query)
            if "uddg" in qs and qs["uddg"]:
                actual_url = qs["uddg"][0]

        if not actual_url.startswith(("http://", "https://")):
            continue
        if "duckduckgo.com" in actual_url:
            continue

        if actual_url not in seen_urls and text:
            seen_urls.add(actual_url)
            results.append({"url": actual_url, "title": text, "snippet": text})
            if len(results) >= max_results:
                break

    return results
