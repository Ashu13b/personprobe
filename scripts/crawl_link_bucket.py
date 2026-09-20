#!/usr/bin/env python3
"""Autonomous link bucket crawler for Dr. Prem Singh Yadav research.

Walks listing pages, publication pages, and institutional hubs via the
OpenScrape mobile browser bridge. Extracts outbound links, verifies author
identity against strict disambiguation rules, ingests new sources into
the active Wikimaker session, and extracts further links to complete the bucket.

Usage:
    python3 scripts/crawl_link_bucket.py [--max-pages 15] [--wait 8]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
sys.path.insert(0, "/home/ubuntu/Expeei/wikimaker")

from openscrape_client import MobileBrowserClient

API_BASE = "http://127.0.0.1:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path("/home/ubuntu/Expeei/wikimaker/sessions") / f"{SESSION_ID}.json"

# Seed hubs known to contain rich clusters of Dr. Yadav works
SEEDS = [
    "https://cirb.res.in/ongoing-projects/",
    "https://cirb.res.in/completed-projects/",
    "https://cirb.res.in/research-achievements/",
    "https://cirb.res.in/newsletters/",
    "https://cirb.res.in/annual-reports/",
    "https://cirb.res.in/cloning/",
    "https://cirb.res.in/cloned-bulls/",
    "https://cirb.res.in/technologies-developed/",
    "https://cirb.res.in/awards-and-recognitions/",
    "https://cirb.res.in/scientific-staff/",
    "https://cirb.res.in/physiology-reproduction/",
    "https://cirb.res.in/news/",
    "https://www.researchgate.net/scientific-contributions/Prem-Singh-Yadav-2179538614",
    "https://www.researchgate.net/scientific-contributions/P-S-Yadav-38446973",
    "https://www.researchgate.net/publication/343800882_Semen_parameters_and_fertility_potency_of_a_cloned_water_buffalo_Bubalus_bubalis_bull_produced_from_a_semen-derived_epithelial_cell",
    "https://www.researchgate.net/publication/333741892_Isolation_and_culture_of_epithelial_cells_from_stored_buffalo_semen_and_their_use_for_the_production_of_cloned_embryos",
    "https://www.researchgate.net/publication/374928871_Electroporation-based_CRISPR_gene_editing_in_adult_buffalo_fibroblast_cells",
    "https://www.researchgate.net/publication/325501303_Establishment_of_a_Somatic_Cell_Bank_for_Indian_Buffalo_Breeds_and_Assessing_the_Suitability_of_the_Cryopreserved_Cells_for_Somatic_Cell_Nuclear_Transfer",
]

# Negative author entities to reject immediately
WRONG_PERSON_ENTITIES = [
    "dr. prem singh (veterinary surgery)",
    "prof (dr) prem singh",
    "prem singh bhadouria",
    "prem prakash yadav",
    "rameshwar yadav"
]

def load_existing_urls() -> set[str]:
    """Load all normalized URLs already in the session."""
    if not SESSION_FILE.exists():
        return set()
    try:
        data = json.loads(SESSION_FILE.read_text())
        urls = set()
        for s in data.get("profile", {}).get("sources", []):
            u = s.get("url", "")
            if u:
                urls.add(normalize_url(u))
        return urls
    except Exception as e:
        print(f"[WARN] Failed to load session file: {e}")
        return set()

def normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking parameters, fragments, and trailing slashes."""
    p = urllib.parse.urlparse(url)
    clean = f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")
    return clean.lower()

def is_valid_candidate(url: str) -> bool:
    """Check if URL looks like a scientific publication, news, or institutional page."""
    u = url.lower()
    if any(ext in u for ext in [".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".ico"]):
        return False
    if any(d in u for d in ["facebook.com", "twitter.com", "instagram.com", "linkedin.com/feed", "support.google", "policies.google"]):
        return False
    # Target domains
    targets = [
        "researchgate.net/publication/",
        "cirb.res.in",
        "icar.org.in",
        "pubmed.ncbi.nlm.nih.gov",
        "pmc.ncbi.nlm.nih.gov",
        "doi.org",
        "sciencedirect.com",
        "tandfonline.com",
        "springer.com",
        "wiley.com",
        "indianjournals.com",
        "hrcak.srce.hr",
        "bhaskar.com",
        "amarujala.com",
        "jagran.com",
        "tribuneindia.com"
    ]
    return any(t in u for t in targets)

def verify_dr_yadav(text: str, title: str) -> bool:
    """Confirm text is about Dr. Prem Singh Yadav and does not belong to wrong entities."""
    t_lower = text.lower() + " " + title.lower()
    # Reject explicit wrong entities
    for we in WRONG_PERSON_ENTITIES:
        if we in t_lower:
            return False
    # Positive name signals
    has_name = any(n in t_lower for n in [
        "prem singh yadav", "prem s. yadav", "prem s yadav",
        "p. s. yadav", "p.s. yadav", "p s yadav", "yadav ps", "yadav, p. s.",
        "डॉ. प्रेम सिंह यादव", "डा. प्रेम सिंह यादव", "प्रेम सिंह यादव"
    ])
    # Context signals
    has_context = any(c in t_lower for c in [
        "cirb", "buffalo", "bubalis", "hisar", "clon", "semen", "embryo", "oocyte", "icar"
    ])
    return has_name and has_context

def api_post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def crawl(max_pages: int = 20, wait_seconds: int = 10):
    client = MobileBrowserClient()
    existing_urls = load_existing_urls()
    print(f"[*] Initial existing URLs in session: {len(existing_urls)}")

    queue = deque(SEEDS)
    visited = set()
    ingested_count = 0

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        norm = normalize_url(url)
        if norm in visited:
            continue
        visited.add(norm)

        print(f"\n[{len(visited)}/{max_pages}] Navigating: {url[:75]}...")
        try:
            res = client.navigate(url, wait_seconds=wait_seconds)
            if res.get("status") == "error":
                print(f"  [ERROR] Nav error: {res.get('error')}")
                continue

            time.sleep(3)
            dom = client.extract_dom(include_text=True, include_links=True)
            text = (dom.get("content", {}).get("text", "") or "")
            title = dom.get("title", "") or ""
            links = dom.get("content", {}).get("links", []) or []

            print(f"  Title: {title[:65]}")
            print(f"  Text len: {len(text)} | Links found: {len(links)}")

            # Check if this page should be ingested into the session
            if norm not in existing_urls:
                if verify_dr_yadav(text, title):
                    print("  --> VERIFIED DR. YADAV WORK! Ingesting into session...")
                    try:
                        r = api_post("/research/add-source-paste", {
                            "profile_name": SESSION_ID,
                            "url": url,
                            "pasted_text": text[:15000]
                        })
                        existing_urls.add(norm)
                        ingested_count += 1
                        print(f"  [SUCCESS] Ingested source #{ingested_count}: {url[:70]}")
                    except Exception as ie:
                        print(f"  [WARN] Ingestion error: {ie}")
                else:
                    print("  [SKIP] Not confirmed as Dr. Prem Singh Yadav work")

            # Extract outbound links for the queue
            for l in links:
                href = l.get("href", "")
                if not href or not href.startswith("http"):
                    continue
                clean_href = href.split("?")[0].rstrip("/")
                norm_href = clean_href.lower()
                if norm_href not in visited and norm_href not in existing_urls:
                    if is_valid_candidate(clean_href):
                        queue.append(clean_href)

            print(f"  Queue size now: {len(queue)}")
            time.sleep(4)

        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            if "Connection" in str(e) or "104" in str(e) or "111" in str(e):
                print("  [HEAL] Attempting auto-heal of mobile bridge...")
                try:
                    import subprocess
                    subprocess.run(
                        ["ssh", "-p", "8022", "-o", "BatchMode=yes", "u0_a509@100.72.202.86",
                         "am startservice org.openscrape.browser/.BrowserAgentService"],
                        capture_output=True, timeout=10
                    )
                    time.sleep(5)
                except Exception as he:
                    print(f"  [HEAL ERROR] {he}")
            time.sleep(5)

    print("\n" + "=" * 60)
    print(f"[*] Crawl finished. Visited: {len(visited)} | New sources ingested: {ingested_count}")
    # Sync session
    try:
        api_post("/sessions/resume", {"session_id": SESSION_ID})
        print("[*] Session resumed and synchronized.")
    except Exception as se:
        print(f"[*] Session sync error: {se}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=15)
    parser.add_argument("--wait", type=int, default=10)
    args = parser.parse_args()
    crawl(max_pages=args.max_pages, wait_seconds=args.wait)
