#!/usr/bin/env python3
"""Print fetch-telemetry status: parked hosts, recheck times, latency summary."""
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import fetch_telemetry as ft  # noqa: E402

rows = []
if ft.LOG_PATH.exists():
    rows = [json.loads(l) for l in ft.LOG_PATH.read_text().splitlines() if l.strip()]

print(f"telemetry rows : {len(rows)}")
lat = [r["latency_ms"] for r in rows if r.get("latency_ms")]
if lat:
    print(f"latency ms     : mean {mean(lat):.0f} | median {sorted(lat)[len(lat)//2]} | max {max(lat)}")
throttles = [r for r in rows if r.get("throttled")]
print(f"throttle events: {len(throttles)}")
for r in throttles[-8:]:
    print(f"   {r['ts'][:19]} {r['host']:<24} {r.get('note','')}")

pending = ft.pending_rechecks()
if pending:
    print("\nhosts in cooldown (recheck after):")
    for p in pending:
        print(f"   {p['host']:<24} in {p['wait_s']}s (at {p['recheck_at'][:19]})")
else:
    print("\nno hosts in cooldown")
