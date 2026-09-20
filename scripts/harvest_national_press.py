#!/usr/bin/env python3
"""Harvest national English press coverage for Dr. Prem Singh Yadav & CIRB buffalo cloning."""

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

NATIONAL_PRESS_QUERIES = [
    'site:thehindu.com "CIRB" buffalo clone OR cloning',
    'site:indianexpress.com "CIRB" Hisar buffalo clone OR cloning',
    'site:hindustantimes.com "CIRB" buffalo clone OR "Hisar Gaurav"',
    'site:timesofindia.indiatimes.com "Prem Singh Yadav"',
    'site:theprint.in "CIRB" "buffalo"',
    'site:moneycontrol.com "CIRB" buffalo',
    'site:downtoearth.org.in "CIRB" buffalo clone OR cloning',
    'site:thewire.in "CIRB" buffalo',
    'site:scroll.in "CIRB" buffalo',
    'site:ndtv.com "CIRB" "buffalo" clone'
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

    for idx, q in enumerate(NATIONAL_PRESS_QUERIES):
        print(f"\n[{idx+1}/{len(NATIONAL_PRESS_QUERIES)}] Query: {q}")
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote(q)
        try:
            res = client.navigate(search_url, wait_seconds=5)
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
                if any(x in href for x in ["google.com", "gstatic.com", "google.co.in"]):
                    continue

                can = canonical_url(href)
                if can and can not in existing_urls and can not in all_harvested:
                    # Filter for relevant domains
                    if any(dom_kw in can for dom_kw in [
                        "thehindu.com", "indianexpress.com", "hindustantimes.com",
                        "timesofindia", "theprint.in", "moneycontrol.com",
                        "downtoearth.org.in", "thewire.in", "scroll.in", "ndtv.com"
                    ]):
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

    print(f"\n[DONE] Finished National Press harvesting. Total unique candidates: {len(all_harvested)}")
    with open("/tmp/national_press_candidates.json", "w") as f:
        json.dump(list(all_harvested.values()), f, indent=2)

if __name__ == "__main__":
    main()
