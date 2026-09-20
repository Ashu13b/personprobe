#!/usr/bin/env python3
"""Run real forensic web sweeps via OpenScrape Mobile Browser Bridge and parse results."""
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient

FORENSIC_QUERIES = [
    {
        "category": "thesis_dissertation",
        "name": "Shodhganga Theses under Dr. P.S. Yadav",
        "q": 'site:shodhganga.inflibnet.ac.in "P.S. Yadav" OR "Prem Singh Yadav" "buffalo"'
    },
    {
        "category": "thesis_dissertation",
        "name": "Shodhganga Cloning Theses at CIRB",
        "q": 'site:shodhganga.inflibnet.ac.in "Hisar Gaurav" OR ("CIRB" "cloning")'
    },
    {
        "category": "grant_sanction",
        "name": "Project Hisar Gaurav Grant & Sanction",
        "q": '"Hisar Gaurav" "sanction" OR "NASF" OR "ICAR" "cloning"'
    },
    {
        "category": "recruitment_notice",
        "name": "Recruited Fellows on Cloning Projects at CIRB",
        "q": 'site:cirb.icar.gov.in "walk-in-interview" "cloning" OR "Hisar Gaurav"'
    },
    {
        "category": "legal_tribunal",
        "name": "IndianKanoon CAT & Court Filings for CIRB / Prem Singh",
        "q": 'site:indiankanoon.org "Central Institute for Research on Buffaloes" "Prem Singh"'
    },
    {
        "category": "annual_report",
        "name": "CIRB Annual Reports Division of Animal Biotechnology",
        "q": 'site:cirb.icar.gov.in "Annual Report" "Animal Biotechnology" "P.S. Yadav"'
    },
    {
        "category": "electoral_housing",
        "name": "Residential & Campus Footprint in Hisar",
        "q": '"Prem Singh Yadav" "Hisar" "quarter" OR "colony" OR "Campus School"'
    }
]

def clean_google_url(raw_url: str) -> str:
    if "/url?q=" in raw_url:
        match = re.search(r'/url\?q=([^&]+)', raw_url)
        if match:
            return urllib.parse.unquote(match.group(1))
    return raw_url

def main():
    client = MobileBrowserClient()
    results = []

    print("[*] Starting Forensic Intelligence Hunt for Dr. Prem Singh Yadav...")

    for i, item in enumerate(FORENSIC_QUERIES):
        print(f"\n--- [{i+1}/{len(FORENSIC_QUERIES)}] {item['name']} ---")
        print(f"Query: {item['q']}")
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote(item['q'])
        
        try:
            nav_res = client.navigate(search_url, wait_seconds=5)
            if nav_res.get("status") == "error":
                print(f"  [!] Navigation error: {nav_res.get('error')}")
                continue
            
            time.sleep(2)
            dom = client.extract_dom(include_text=True, include_links=True)
            text = dom.get("content", {}).get("text", "")
            links = dom.get("content", {}).get("links", [])
            
            # Filter external non-google links
            found_links = []
            for l in links:
                raw_href = l.get("href", "")
                url = clean_google_url(raw_href)
                title = l.get("text", "").strip()
                if url.startswith("http") and not any(x in url for x in ["google.com", "gstatic.com", "google.co.in", "youtube.com/search"]):
                    found_links.append({"url": url, "title": title})
            
            print(f"  Found {len(found_links)} external result links.")
            
            # Print top 5 links
            top_links = []
            seen_urls = set()
            for fl in found_links:
                u = fl["url"].split("#")[0].split("?")[0]
                if u not in seen_urls and len(fl["title"]) > 3:
                    seen_urls.add(u)
                    top_links.append(fl)
                    if len(top_links) >= 5:
                        break
            
            for idx, tl in enumerate(top_links):
                print(f"   [{idx+1}] {tl['title'][:80]} -> {tl['url']}")
                
            results.append({
                "category": item["category"],
                "name": item["name"],
                "query": item["q"],
                "links": top_links,
                "snippet_preview": text[:500].replace("\n", " ")
            })

        except Exception as e:
            print(f"  [!] Exception: {e}")

    out_file = Path("/home/ubuntu/Expeei/personprobe/forensic_hunt_results.json")
    out_file.write_text(json.dumps(results, indent=2))
    print(f"\n[✓] Finished! Saved detailed forensic findings to {out_file}")

if __name__ == "__main__":
    main()
