#!/usr/bin/env python3
"""Bulk ingest newly discovered candidate links into Dr. Prem Singh Yadav research session."""

import json
import time
import urllib.request
from pathlib import Path

API_BASE = "http://127.0.0.1:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path("/home/ubuntu/Expeei/wikimaker/sessions") / f"{SESSION_ID}.json"

def api_post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def load_existing_urls() -> set[str]:
    if not SESSION_FILE.exists():
        return set()
    try:
        data = json.loads(SESSION_FILE.read_text())
        return {s.get("url", "").lower().rstrip("/") for s in data.get("profile", {}).get("sources", [])}
    except Exception:
        return set()

def main():
    existing_urls = load_existing_urls()
    print(f"[*] Loaded {len(existing_urls)} existing session URLs.")

    with open("/tmp/total_combined_candidates.json") as f:
        candidates = json.load(f)

    print(f"[*] Processing {len(candidates)} candidate links...")
    ingested = 0

    for idx, c in enumerate(candidates):
        url = c.get("url", "").strip()
        norm_url = url.lower().rstrip("/")
        if not norm_url or norm_url in existing_urls:
            continue

        title = c.get("title", "") or "Untitled Candidate Publication"
        authors = c.get("authors", "") or "ICAR-CIRB Research Team"
        publisher = c.get("publisher", "") or c.get("journal", "") or "Scholarly Publication"
        year = c.get("year", "")

        pasted_text = (
            f"Title: {title}\n"
            f"Authors / Contributors: {authors}\n"
            f"Journal / Publisher: {publisher} ({year})\n"
            f"Source URL: {url}\n"
        )

        try:
            res = api_post("/research/add-source-paste", {
                "profile_name": SESSION_ID,
                "url": url,
                "pasted_text": pasted_text
            })
            existing_urls.add(norm_url)
            ingested += 1
            if ingested % 10 == 0 or idx == len(candidates) - 1:
                print(f"  [{ingested}/{len(candidates)}] Ingested: {title[:55]} ({url[:45]})")
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {url}: {e}")

        time.sleep(0.3)

    print(f"\n[DONE] Successfully ingested {ingested} candidate links into session.")
    try:
        api_post("/sessions/resume", {"session_id": SESSION_ID})
        print("[*] Session synchronized and saved.")
    except Exception as se:
        print(f"[*] Sync error: {se}")

if __name__ == "__main__":
    main()
