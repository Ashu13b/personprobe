#!/usr/bin/env python3
"""Harvest awards, institutional repositories, and cloning milestones for Dr. Prem Singh Yadav."""

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

QUERIES = [
    'site:icar.org.in "Nanaji Deshmukh" "CIRB"',
    'site:icar.org.in "Nanaji Deshmukh" "cloning"',
    '"Nanaji Deshmukh" "Prem Singh Yadav"',
    'site:sapi.in "P.S. Yadav" OR "Prem Singh Yadav"',
    'site:krishikosh.egranth.ac.in "Prem Singh Yadav"',
    'site:epubs.icar.org.in "P.S. Yadav" buffalo',
    'site:epubs.icar.org.in "Prem Singh Yadav"',
    '"Hisar Gaurav" "Prem Singh Yadav"',
    '"Assam Gaurav" "CIRB" buffalo',
    '"Manikarnika" "CIRB" buffalo clone',
    '"Sach-Gaurav" "cloned buffalo"',
    'site:dbtindia.gov.in "Prem Singh Yadav"',
    'site:dbtindia.gov.in "CIRB" buffalo',
    '"Prem Singh Yadav" "ICAR-CIRB" award OR fellowship'
]

def load_existing_urls() -> set[str]:
    if not SESSION_FILE.exists():
        return set()
    try:
        data = json.loads(SESSION_FILE.read_text())
        return {canonical_url(s.get("url")) for s in data.get("profile", {}).get("sources", []) if s.get("url")}
    except Exception:
        return set()

def main():
    client = MobileBrowserClient()
    existing_urls = load_existing_urls()
    print(f"[*] Initial existing canonical URLs in session: {len(existing_urls)}")

    all_harvested = {}

    for idx, q in enumerate(QUERIES):
        print(f"\n[{idx+1}/{len(QUERIES)}] Query: {q}")
        search_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
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
                if "uddg=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    target = parsed.get("uddg", [""])[0]
                    if not target or any(d in target for d in ["duckduckgo.com", "bing.com", "yahoo.com"]):
                        continue
                    
                    can = canonical_url(target)
                    if can and can not in existing_urls and can not in all_harvested:
                        all_harvested[can] = {
                            "url": target,
                            "canonical": can,
                            "title": text,
                            "query": q
                        }

            print(f"  Total unique candidates so far: {len(all_harvested)}")
            time.sleep(3)

        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            time.sleep(3)

    print(f"\n[DONE] Finished harvesting queries. Total unique candidates: {len(all_harvested)}")
    with open("/tmp/awards_and_repos_candidates.json", "w") as f:
        json.dump(list(all_harvested.values()), f, indent=2)

if __name__ == "__main__":
    main()
