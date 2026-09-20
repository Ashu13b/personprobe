"""Integration with the OpenScrape Mobile Browser Bridge (100.72.202.86:38765).

Enables Wikimaker to route web scraping through a physical mobile carrier IP via Tailscale,
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


def fetch_via_mobile_bridge(url: str, wait_seconds: int = 5) -> Optional[dict[str, Any]]:
    """Navigate and extract DOM text via the mobile scrap browser.

    Returns dict with {"title": str, "text": str, "url": str, "raw_html": str} or None.
    """
    client = get_mobile_client()
    if not client:
        return None
    try:
        res = client.navigate(url, wait_seconds=wait_seconds)
        if res.get("status") == "error":
            logger.debug("Mobile bridge navigation error for %s: %s", url, res.get("error"))
            return None

        dom = client.extract_dom(include_text=True, include_links=True)
        content = dom.get("content", {})
        return {
            "title": dom.get("title", ""),
            "text": content.get("text", "").strip(),
            "url": dom.get("url", url),
            "links": content.get("links", []),
            "has_captcha": dom.get("has_captcha", False)
        }
    except Exception as e:
        logger.warning("Failed to fetch %s via mobile bridge: %s", url, e)
        return None
