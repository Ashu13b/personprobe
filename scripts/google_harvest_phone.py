#!/usr/bin/env python3
"""Run targeted Google searches via OpenScrape mobile browser to discover new candidate links."""

import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient
from scripts.deduplicate_session import canonical_url

SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/personprobe/sessions/{SESSION_ID}.json")

GOOGLE_QUERIES = [
    '"Dr. Prem Singh Yadav" CIRB',
    '"P.S. Yadav" CIRB "cloning"',
    '"Prem Singh Yadav" "buffalo cloning" ICAR',
    '"Prem Singh Yadav" "Hisar Gaurav"',
    '"Prem Singh Yadav" "Sach-Gaurav"',
    '"Prem Singh Yadav" "Assam Gaurav"',
    '"Prem Singh Yadav" CIRB "patent" OR "technology"',
    '"Prem Singh Yadav" "Nanaji Deshmukh"',
    '"Prem Singh Yadav" CIRB "award"',
    '"Prem Singh Yadav" "Institute of Animal Sciences" Germany'
]

def load_existing_canonical_urls() -> set[str]:
    if not SESSION_FILE.exists():
        return set()
    try:
        data = json.loads(SESSION_FILE.read_text())
        return {canonical_url(s.get("url")) for s in data.get("profile", {}).get("sources", []) if s.get("url")}
    except Exception:
        return set()

def main():
    client = MobileBrowserClient()
    existing_urls = load_existing_canonical_urls()
    print(f"[*] Initial existing canonical URLs in session: {len(existing_urls)}")

    all_harvested = {}

    for idx, q in enumerate(GOOGLE_QUERIES):
        print(f"\n[{idx+1}/{len(GOOGLE_QUERIES)}] Google Query: {q}")
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote(q)
        try:
            res = client.navigate(search_url, wait_seconds=6)
            if res.get("status") == "error":
                print(f"  [ERROR] Nav error: {res.get('error')}")
                continue

            time.sleep(2)
            dom = client.extract_dom(include_text=False, include_links=True)
            links = dom.get("content", {}).get("links", [])
            print(f"  Links returned: {len(links)}")

            for l in links:
                href = l.get("href", "")
                text = l.get("text", "").strip()
                if not href.startswith("http"):
                    continue
                
                # Exclude internal Google links
                if any(x in href for x in ["google.com", "gstatic.com", "google.co.in"]):
                    continue

                can = canonical_url(href)
                if can and can not in existing_urls and can not in all_harvested:
                    all_harvested[can] = {
                        "url": href,
                        "canonical": can,
                        "title": text,
                        "query": q
                    }

            print(f"  Total unique candidates so far: {len(all_harvested)}")
            time.sleep(3)

        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            time.sleep(3)

    print(f"\n[DONE] Finished Google harvesting. Total unique candidates: {len(all_harvested)}")
    with open("/tmp/google_harvest_candidates.json", "w") as f:
        json.dump(list(all_harvested.values()), f, indent=2)

if __name__ == "__main__":
    main()
