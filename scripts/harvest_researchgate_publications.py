#!/usr/bin/env python3
"""Autonomous harvester for Dr. Prem Singh Yadav ResearchGate publications."""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient

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
    client = MobileBrowserClient()
    existing_urls = load_existing_urls()
    print(f"[*] Loaded {len(existing_urls)} existing session URLs.")

    with open("/tmp/rg_new_pubs.json") as f:
        pubs = json.load(f)

    # Filter out PDFs or auxiliary links
    target_pubs = []
    for p in pubs:
        clean = p.split("?")[0].rstrip("/")
        if clean.endswith(".pdf") or "/links/" in clean or "/fulltext/" in clean:
            continue
        if clean.lower() not in existing_urls:
            target_pubs.append(clean)

    print(f"[*] Identified {len(target_pubs)} clean publication URLs to harvest.")

    ingested = 0
    for idx, pub_url in enumerate(target_pubs):
        print(f"\n[{idx+1}/{len(target_pubs)}] Navigating: {pub_url[:70]}...")
        try:
            res = client.navigate(pub_url, wait_seconds=8)
            if res.get("status") == "error":
                print(f"  [ERROR] Nav error: {res.get('error')}")
                continue

            time.sleep(3)
            dom = client.extract_dom(include_text=True, include_links=False)
            title = dom.get("title", "")
            text = (dom.get("content", {}).get("text", "") or "")

            print(f"  Title: {title[:65]}")
            print(f"  Text length: {len(text)}")

            pasted_text = (
                f"URL: {pub_url}\n"
                f"Page Title: {title}\n\n"
                f"Extracted Content:\n{text[:12000]}\n"
            )

            try:
                r = api_post("/research/add-source-paste", {
                    "profile_name": SESSION_ID,
                    "url": pub_url,
                    "pasted_text": pasted_text
                })
                existing_urls.add(pub_url.lower())
                ingested += 1
                print(f"  [SUCCESS] Ingested #{ingested}: {pub_url[:65]}")
            except Exception as ie:
                print(f"  [WARN] Ingestion error: {ie}")

            time.sleep(5)

        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            time.sleep(5)

    print(f"\n[DONE] Finished harvesting ResearchGate. Ingested {ingested} new publications.")
    try:
        api_post("/sessions/resume", {"session_id": SESSION_ID})
        print("[*] Session synchronized.")
    except Exception as se:
        print(f"[*] Session sync error: {se}")

if __name__ == "__main__":
    main()
