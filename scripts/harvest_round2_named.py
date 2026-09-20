#!/usr/bin/env python3
"""Harvest Round 2: Target ICAR ePubs, Hindi Press, SAPI, and NAAS for Dr. Prem Singh Yadav.

Strict rules:
1. Every candidate visited on mobile scrap browser.
2. Verified DOM text must contain 'Prem Singh Yadav', 'P.S. Yadav', 'P. S. Yadav', or 'प्रेम सिंह यादव'.
3. Verified topic relevance (animal biotechnology, CIRB, cloning, buffalo, physiology).
4. Strict canonical deduplication.
"""

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient
from scripts.deduplicate_session import canonical_url

SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/wikimaker/sessions/{SESSION_ID}.json")
OUTPUT_FILE = Path("/tmp/round2_named_candidates.json")

TARGET_QUERIES = [
    'site:epubs.icar.org.in "P.S. Yadav" buffalo',
    'site:epubs.icar.org.in "Prem Singh Yadav"',
    'site:epubs.icar.org.in/index.php/IJAnS "P.S. Yadav"',
    'site:sapi.in "Prem Singh Yadav" OR "P.S. Yadav"',
    'site:bhaskar.com "प्रेम सिंह यादव" CIRB OR भैंस',
    'site:jagran.com "प्रेम सिंह यादव" CIRB OR भैंस',
    'site:amarujala.com "प्रेम सिंह यादव" CIRB OR भैंस',
    'site:etvbharat.com "प्रेम सिंह यादव"',
    'site:naas.org.in "Prem Singh Yadav"',
    '"Prem Singh Yadav" "Dharmendra Kumar" buffalo cloning',
    '"Prem Singh Yadav" "Naresh Selokar"',
    '"Prem Singh Yadav" "Inderjeet Singh" buffalo',
    '"Prem Singh Yadav" "Birbal Singh" buffalo'
]

NAME_PATTERNS = [
    r"\bprem\s+singh\s+yadav\b",
    r"\bp\.\s*s\.\s*yadav\b",
    r"\bprem\s+s\.\s*yadav\b",
    r"\bdr\.?\s*prem\s+singh\b",
    r"\bडॉ\.?\s*प्रेम\s+सिंह\s+यादव\b",
    r"\bप्रेम\s+सिंह\s+यादव\b",
    r"\bपी\.?\s*एस\.?\s*यादव\b"
]

RELEVANCE_PATTERNS = [
    r"\bbuffalo\b", r"\bclon", r"\bcirb\b", r"\bembryo", r"\bsemen\b",
    r"\breproduct", r"\bphysiol", r"\bstem\s+cell", r"\bicar\b", r"\bmurrah\b",
    r"\bhisar\b", r"\bhau\b", r"\bgaurav\b", r"\bभैंस\b", r"\bक्लोन\b", r"\bसीआईआरबी\b"
]

def load_existing_urls() -> set[str]:
    if not SESSION_FILE.exists():
        return set()
    try:
        data = json.loads(SESSION_FILE.read_text())
        return {canonical_url(s.get("url")) for s in data.get("profile", {}).get("sources", []) if s.get("url")}
    except Exception:
        return set()

def name_matches(text: str) -> bool:
    t = text.lower()
    return any(re.search(pat, t) for pat in NAME_PATTERNS)

def relevance_matches(text: str) -> bool:
    t = text.lower()
    return any(re.search(pat, t) for pat in RELEVANCE_PATTERNS)

def main():
    client = MobileBrowserClient()
    existing_urls = load_existing_urls()
    print(f"[*] Initial existing canonical URLs in session: {len(existing_urls)}")

    harvested_urls = {}
    verified_candidates = []

    # Step 1: Collect candidates across targeted queries
    for idx, q in enumerate(TARGET_QUERIES, 1):
        print(f"\n[{idx}/{len(TARGET_QUERIES)}] Query: {q}")
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
                if can and can not in existing_urls and can not in harvested_urls:
                    harvested_urls[can] = {
                        "raw_url": href,
                        "canonical": can,
                        "search_title": text,
                        "query": q
                    }

            print(f"  Unique candidates collected so far: {len(harvested_urls)}")
            time.sleep(2)
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            time.sleep(2)

    print(f"\n[*] Total candidates collected for DOM inspection: {len(harvested_urls)}")

    # Step 2: On-page DOM verification for his name
    for idx, (can, item) in enumerate(harvested_urls.items(), 1):
        target_url = item["raw_url"]
        print(f"[{idx}/{len(harvested_urls)}] Verifying {target_url} ...")
        try:
            if any(bad in target_url.lower() for bad in [
                "login", "signin", "signup", "facebook.com", "instagram.com",
                "twitter.com", "x.com", "linkedin.com/pub/dir"
            ]):
                continue

            res = client.navigate(target_url, wait_seconds=5)
            if res.get("status") == "error":
                print("  [SKIP] Nav failed")
                continue

            dom = client.extract_dom(include_text=True, include_links=False)
            page_text = dom.get("content", {}).get("text", "")
            page_title = dom.get("title", "") or item["search_title"]

            has_name = name_matches(page_title + " " + page_text)
            has_rel = relevance_matches(page_title + " " + page_text)

            if has_name and has_rel:
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]
                name_snippets = [l for l in lines if name_matches(l)]
                snippet = " ... ".join(name_snippets[:3]) if name_snippets else page_title

                print(f"  [VERIFIED] Name found! Snippet: {snippet[:120]}...")
                verified_candidates.append({
                    "url": target_url,
                    "canonical": can,
                    "title": page_title,
                    "snippet": snippet[:400],
                    "query": item["query"]
                })
            else:
                if not has_name:
                    print("  [REJECT] Name NOT found on page.")
                elif not has_rel:
                    print("  [REJECT] Name found but topic irrelevant.")

            time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(2)

    print(f"\n[DONE] Finished verification. Total confirmed sources with his name: {len(verified_candidates)}")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(verified_candidates, f, indent=2)

if __name__ == "__main__":
    main()
