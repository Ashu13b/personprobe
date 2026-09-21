"""Research operations endpoints: fetch telemetry and pacing visibility."""
from __future__ import annotations

from fastapi import APIRouter

from engine import fetch_telemetry as ft

ops_router = APIRouter(prefix="/ops", tags=["ops"])


@ops_router.get("/fetch-telemetry")
def get_fetch_telemetry(limit: int = 200) -> dict:
    """Recent fetch speed/throttle telemetry plus hosts currently in cooldown."""
    import json as _json
    rows: list[dict] = []
    if ft.LOG_PATH.exists():
        try:
            lines = ft.LOG_PATH.read_text().splitlines()[-max(1, min(limit, 2000)):]
            for line in lines:
                try:
                    rows.append(_json.loads(line))
                except Exception:
                    continue
        except Exception:
            rows = []

    latencies = [r.get("latency_ms") for r in rows if isinstance(r.get("latency_ms"), int)]
    throttled = [r for r in rows if r.get("throttled")]
    by_transport: dict[str, dict] = {}
    for r in rows:
        tr = r.get("transport") or "unknown"
        bucket = by_transport.setdefault(tr, {"count": 0, "latency_ms": 0, "throttles": 0})
        bucket["count"] += 1
        if isinstance(r.get("latency_ms"), int):
            bucket["latency_ms"] += r["latency_ms"]
        if r.get("throttled"):
            bucket["throttles"] += 1
    for bucket in by_transport.values():
        if bucket["count"]:
            bucket["avg_latency_ms"] = round(bucket["latency_ms"] / bucket["count"])

    return {
        "rows": len(rows),
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "throttle_events": len(throttled),
        "by_transport": by_transport,
        "pending_rechecks": ft.pending_rechecks(),
        "recent": rows[-25:],
    }
