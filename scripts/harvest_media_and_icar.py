#!/usr/bin/env python3
"""Harvest news media, ICAR, and institutional links for Dr. Prem Singh Yadav & CIRB cloning."""

import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient

SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/wikimaker/sessions/{SESSION_ID}.json")

QUERIES = [
    "site:tribuneindia.com CIRB Hisar buffalo",
    "site:bhaskar.com CIRB हिसार गौरव",
    "site:amarujala.com CIRB हिसार गौरव",
    "site:jagran.com CIRB हिसार गौरव",
    "site:icar.org.in \"Prem Singh Yadav\"",
    "site:icar.org.in \"Hisar Gaurav\"",
    "site:icar.org.in \"Veer Gaurav\"",
    "site:icar.org.in \"Sach Gaurav\"",
    "site:icar.org.in \"cloned buffalo\" Hisar",
    "site:ndri.res.in \"Prem Singh Yadav\"",
    "site:naas.org.in \"Prem Singh Yadav\"",
    "site:sapi.in \"Prem Singh Yadav\""
]

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
    print(f"[*] Initial existing URLs in session: {len(existing_urls)}")

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
                    clean_target = target.split("?")[0].rstrip("/")
                    norm = clean_target.lower()
                    if norm not in existing_urls and norm not in all_harvested:
                        all_harvested[norm] = {
                            "url": clean_target,
                            "title": text,
                            "query": q
                        }

            print(f"  Total unique candidates so far: {len(all_harvested)}")
            time.sleep(4)

        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            time.sleep(4)

    print(f"\n[DONE] Finished harvesting queries. Total unique candidates: {len(all_harvested)}")
    with open("/tmp/media_and_icar_candidates.json", "w") as f:
        json.dump(list(all_harvested.values()), f, indent=2)

if __name__ == "__main__":
    main()
