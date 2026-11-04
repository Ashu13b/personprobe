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


def get_mobile_client() -> Optional[Any]:
    """Return a singleton MobileBrowserClient instance if available, else None."""
    global _client
    if _client is not None:
        return _client
    try:
        from openscrape_client import MobileBrowserClient  # type: ignore

        client = MobileBrowserClient()
        status = client.get_status()
        if isinstance(status, dict) and status.get("status") == "ok":
            _client = client
            return _client
    except Exception as e:
        logger.debug("MobileBrowserClient unavailable: %s", e)
    return None


def is_mobile_bridge_available() -> bool:
    """Check if the physical mobile browser bridge on Tailnet (port 38765) is reachable."""
    client = get_mobile_client()
    if client is None:
        return False
    try:
        status = client.get_status()
        return isinstance(status, dict) and status.get("status") == "ok"
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


def search_via_mobile_bridge(
    query: str, max_results: int = 10
) -> list[dict[str, str]]:
    """Execute a web search query via the mobile browser bridge (e.g. DDG HTML) to bypass bot-walls.

    Returns list of dicts with {"url": str, "title": str, "snippet": str}.
    """
    if not is_mobile_bridge_available():
        return []

    from urllib.parse import quote_plus, parse_qs, urlsplit
    from bs4 import BeautifulSoup

    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    res = fetch_via_mobile_bridge(search_url, wait_seconds=3)
    if not res:
        return []

    html = res.get("raw_html") or res.get("text", "")
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str]] = []
    for item in soup.select(".result"):
        a_title = item.select_one("a.result__a, h2 a")
        snippet_elem = item.select_one(".result__snippet")
        if a_title:
            href_val = a_title.get("href")
            href = str(href_val) if href_val else ""
            if "uddg=" in href:
                qs = parse_qs(urlsplit(href).query)
                if "uddg" in qs and qs["uddg"]:
                    href = qs["uddg"][0]
            title = a_title.get_text(" ", strip=True)
            snippet = snippet_elem.get_text(" ", strip=True) if snippet_elem else ""
            if href and title:
                results.append({"url": href, "title": title, "snippet": snippet})
                if len(results) >= max_results:
                    break
    return results
