#!/usr/bin/env python3
"""Backfill L4 verbatim quotes for approved-but-unquoted claims.

For each distinct cited source: fetch the page/PDF text (direct HTTP first, phone
bridge fallback), locate the best supporting sentence per claim, then POST the
guarded batch to /api/research/claims/set-quote. Dry-run by default.

Usage: python3 scripts/backfill_quotes.py [--apply] [--priority] [--max-sources N]
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.quote_backfill import best_quote, collect_claims_needing_quotes  # noqa: E402
from engine.models import PersonProfile, Claim  # noqa: E402

API = "http://localhost:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"
PRIORITY_FIELDS = {"birth_date", "birth_place", "education", "careers", "career",
                   "position", "affiliation", "award", "known_for"}


def page_text(url: str) -> str:
    try:
        import fitz
    except Exception:
        fitz = None
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121"},
                         timeout=25, stream=True)
        if r.status_code != 200:
            return ""
        ctype = r.headers.get("content-type", "")
        if "pdf" in ctype or url.lower().endswith(".pdf"):
            if fitz is None:
                return ""
            data = r.content[:12_000_000]
            doc = fitz.open(stream=data, filetype="pdf")
            return " ".join(p.get_text() for p in doc)[:600_000]
        import re as _re
        html = r.text[:1_500_000]
        html = _re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=_re.S | _re.I)
        html = _re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=_re.S | _re.I)
        return _re.sub(r"<[^>]+>", " ", html)[:600_000]
    except Exception:
        pass
    # fallback: phone bridge for bot-walled hosts (carrier IP)
    try:
        sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
        from engine.mobile_bridge import fetch_via_mobile_bridge
        res = fetch_via_mobile_bridge(url, wait_seconds=6)
        if res and res.get("text"):
            return res["text"][:600_000]
    except Exception:
        return ""
    return ""


def main() -> None:
    apply_changes = "--apply" in sys.argv
    priority_only = "--priority" in sys.argv
    max_sources = 60
    if "--max-sources" in sys.argv:
        max_sources = int(sys.argv[sys.argv.index("--max-sources") + 1])

    data = requests.get(f"{API}/session/{SESSION_ID}", timeout=15).json()["profile"]
    profile = PersonProfile.model_validate(data)
    indices = collect_claims_needing_quotes(profile.claims, approved_only=True)
    if priority_only:
        indices = [i for i in indices if profile.claims[i].field in PRIORITY_FIELDS]
    print(f"approved claims missing quotes: {len(indices)} (priority filter: {priority_only})")

    by_source: dict[str, list[int]] = {}
    for i in indices:
        by_source.setdefault(profile.claims[i].source_url, []).append(i)

    items, fetched = [], 0
    for url, idxs in list(by_source.items())[:max_sources]:
        text = page_text(url)
        fetched += 1
        if not text:
            print(f"  ! no text: {url[:80]}")
            continue
        for i in idxs:
            claim_text = profile.claims[i].text
            require = ["yadav", "prem"] if any(k in claim_text.lower() for k in ("yadav", "prem")) else None
            quote, score = best_quote(claim_text, text, must_include_any=require)
            if quote:
                items.append({"claim_index": i, "source_url": url, "quote": quote, "score": score})
                print(f"  + [{score:.2f}] {profile.claims[i].field:<12} | {quote[:80]}")
        if fetched % 10 == 0:
            print(f"  ... {fetched} sources fetched, {len(items)} quotes found", flush=True)

    print(f"\nquotes found: {len(items)} across {fetched} sources")
    if not apply_changes:
        Path("/tmp/opencode/quote_backfill_plan.json").write_text(json.dumps(items, indent=1))
        print("dry-run — plan saved to /tmp/opencode/quote_backfill_plan.json (use --apply)")
        return
    r = requests.post(f"{API}/research/claims/set-quote",
                      json={"profile_name": SESSION_ID, "actor": "agent", "items": items}, timeout=60)
    print("apply:", r.status_code, r.json().get("updated"), "updated |", len(r.json().get("skipped", [])), "skipped")


if __name__ == "__main__":
    main()
