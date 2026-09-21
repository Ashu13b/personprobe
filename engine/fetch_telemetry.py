"""Fetch telemetry: per-request speed/status logging and pacing advice.

Every outbound fetch (HTTP requests or mobile-bridge page loads) can record its
latency and outcome here. `suggest_delay()` then derives a safe inter-request
gap per host from recent throttle events (429 / CAPTCHA / empty renders), so a
run that starts getting throttled automatically slows itself instead of
re-triggering the block.

Runtime output lives under sessions/ (gitignored) — telemetry is per-host state,
not repo content.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

LOG_PATH = Path("sessions/fetch_telemetry.jsonl")
DEFAULT_DELAY_S = 2.0
THROTTLE_DELAY_S = 20.0
_THROTTLE_WINDOW_S = 900  # 15 minutes


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except Exception:
        return ""


def record(transport: str, url: str, status=None, latency_ms: int | None = None,
           throttled: bool = False, note: str = "") -> None:
    """Append one telemetry row. Never raises (telemetry must not break fetches)."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "transport": transport,          # http | phone | api
            "host": _host(url),
            "url": url[:500],
            "status": status,
            "latency_ms": latency_ms,
            "throttled": bool(throttled),
            "note": note[:200],
        }
        with LOG_PATH.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass


def timed(transport: str, url: str):
    """Context manager: times a fetch and records latency + optional outcome.

    with timed("http", url) as t:
        resp = requests.get(url)
        t.status = resp.status_code
        t.throttled = resp.status_code == 429
    """
    return _Timer(transport, url)


class _Timer:
    def __init__(self, transport: str, url: str):
        self.transport = transport
        self.url = url
        self.status = None
        self.throttled = False
        self.note = ""
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        latency_ms = int((time.time() - self._t0) * 1000)
        if exc_type is not None and not self.note:
            self.note = f"exception:{exc_type.__name__}"
        record(self.transport, self.url, self.status, latency_ms, self.throttled, self.note)
        return False


def recent_throttles(minutes: int = 15, host: str | None = None) -> int:
    """Count throttle events in the recent window (optionally per host)."""
    if not LOG_PATH.exists():
        return 0
    cutoff = time.time() - minutes * 60
    count = 0
    try:
        for line in LOG_PATH.read_text().splitlines()[-2000:]:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if not row.get("throttled"):
                continue
            if host and row.get("host") != host:
                continue
            ts = row.get("ts", "")
            try:
                epoch = datetime.fromisoformat(ts).timestamp()
            except Exception:
                continue
            if epoch >= cutoff:
                count += 1
    except Exception:
        return 0
    return count


def suggest_delay(url_or_host: str, default: float = DEFAULT_DELAY_S) -> float:
    """Advisory gap before the next request to this host.

    Priority: an active cooldown from a recent throttle (wait it out), then a
    soft throttle signal (park briefly), then the default pace.
    """
    host = _host(url_or_host) if "://" in url_or_host else url_or_host
    cooldown = wait_time(url_or_host)
    if cooldown > 0:
        return cooldown
    if host and recent_throttles(host=host) > 0:
        return THROTTLE_DELAY_S
    if recent_throttles() > 2:
        return max(default, THROTTLE_DELAY_S / 2)
    return default


COOLDOWN_S = 900  # a throttled host is parked for 15 minutes before any retry


def last_throttle_ts(host: str) -> float | None:
    """Epoch of the most recent throttle event for a host, if any."""
    if not LOG_PATH.exists():
        return None
    latest = None
    try:
        for line in LOG_PATH.read_text().splitlines()[-4000:]:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("host") != host or not row.get("throttled"):
                continue
            try:
                epoch = datetime.fromisoformat(row["ts"]).timestamp()
            except Exception:
                continue
            latest = epoch if latest is None else max(latest, epoch)
    except Exception:
        return None
    return latest


def wait_time(url_or_host: str, cooldown_s: int = COOLDOWN_S) -> float:
    """Seconds to wait before this host may be queried again (0 when cleared).

    A throttle parks the host for `cooldown_s`; schedules that respect this
    simply come back later instead of re-triggering the bot wall.
    """
    host = _host(url_or_host) if "://" in url_or_host else url_or_host
    if not host:
        return 0.0
    last = last_throttle_ts(host)
    if last is None:
        return 0.0
    remaining = cooldown_s - (time.time() - last)
    return max(0.0, remaining)


def pending_rechecks(cooldown_s: int = COOLDOWN_S) -> list[dict]:
    """Hosts currently in cooldown, with when each becomes retryable again.

    A later run (or cron-ish pass) consults this to re-check throttled hosts
    after the cooldown rather than guessing.
    """
    if not LOG_PATH.exists():
        return []
    out: dict[str, dict] = {}
    try:
        for line in LOG_PATH.read_text().splitlines()[-4000:]:
            try:
                row = json.loads(line)
            except Exception:
                continue
            host = row.get("host") or ""
            if not host or not row.get("throttled"):
                continue
            try:
                epoch = datetime.fromisoformat(row["ts"]).timestamp()
            except Exception:
                continue
            remaining = cooldown_s - (time.time() - epoch)
            if remaining <= 0:
                out.pop(host, None)
                continue
            out[host] = {
                "host": host,
                "recheck_at": datetime.fromtimestamp(epoch + cooldown_s, timezone.utc).isoformat(),
                "wait_s": round(remaining),
            }
    except Exception:
        return []
    return sorted(out.values(), key=lambda r: r["wait_s"])


THROTTLE_TEXT_MARKERS = (
    "solve the challenge",
    "unusual traffic",
    "temporarily offline",
    "too many requests",
    "one last step",
    "checking your browser",
    "verify you are human",
    "enable javascript and cookies",
    "access denied",
)


def looks_throttled(text: str, status=None) -> bool:
    """Heuristic: page/body markers that mean the request was throttled or walled.

    Search engines and archives return challenge/outage pages with HTTP 200, so
    status alone is not enough; this catches them for telemetry and pacing.
    """
    if status == 429:
        return True
    low = (text or "").lower()
    return any(marker in low for marker in THROTTLE_TEXT_MARKERS)
