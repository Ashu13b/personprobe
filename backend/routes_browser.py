"""Phone-browser bridge routes (OpenScrape app webhooks).

The Android app POSTs here when the human clears a bot challenge on the
phone screen, so it can toast "VM notified" instead of "webhook unreachable".
Agents poll has_captcha via the bridge directly; this record exists so a
solve event is never lost between polls.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

browser_router = APIRouter()

_last_captcha_solved: dict = {}


@browser_router.post("/browser/captcha-solved")
def captcha_solved(body: dict) -> dict:
    """Record a human-solved challenge from the phone browser."""
    global _last_captcha_solved
    _last_captcha_solved = {
        "event": body.get("event", "captcha_solved"),
        "url": body.get("url"),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    return {"ok": True, "recorded": _last_captcha_solved}


@browser_router.get("/browser/captcha-solved")
def last_captcha_solved() -> dict:
    """Most recent solve event, if any."""
    return {"last": _last_captcha_solved or None}
