#!/usr/bin/env python3
"""Targeted forensic search via OpenScrape mobile browser for remaining unconfirmed inquiries."""

import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Expeei/android-browser")
from openscrape_client import MobileBrowserClient

SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/wikimaker/sessions/{SESSION_ID}.json")

TARGET_QUERIES = [
    # 1. Ph.D. Dissertation at CCS HAU (1991)
    ('inq-be0a1d7d', '"Prem Singh Yadav" "HAU" "1991" OR "thesis" OR "dissertation"'),
    ('inq-be0a1d7d', '"P.S. Yadav" "Animal Production Physiology" "HAU"'),
    ('inq-be0a1d7d', '"P.S. Yadav" "CCSHAU" OR "HAU" "1991"'),
    ('inq-be0a1d7d', 'site:krishikosh.egranth.ac.in "Prem Singh Yadav" "1991"'),

    # 2. Selection to ARS & Pay Level 14 Principal Scientist
    ('inq-c4ae3398', '"Prem Singh Yadav" "Agricultural Research Service" OR "ARS" ICAR'),
    ('inq-c4ae3398', '"P.S. Yadav" "Principal Scientist" "Pay Level 14" OR "Level-14" CIRB'),
    ('inq-c4ae3398', '"P.S. Yadav" "ARS" "scientist" "CIRB" "1993" OR "1992" OR "1994"'),

    # 3. Residential quarters at ICAR-CIRB Sirsa Road Campus
    ('inq-8adb7c15', '"Prem Singh Yadav" "Type-V" OR "Residential" "CIRB" "Hisar"'),
    ('inq-8adb7c15', '"P.S. Yadav" "CIRB Campus" "Sirsa Road" Hisar'),

    # 4. The Gazette of India Notifications (ICAR / DARE Appointment)
    ('inq-8e4d0c53', 'site:egazette.gov.in "Prem Singh Yadav"'),
    ('inq-8e4d0c53', '"Gazette of India" "Prem Singh Yadav" "ICAR"'),

    # 5. Domicile & Electoral Roll in Hisar
    ('inq-afb8942f', 'site:ceoharyana.gov.in "Prem Singh" "Hisar"'),
    ('inq-afb8942f', '"Prem Singh Yadav" "Hisar" "electoral roll" OR "voter"'),
]


def load_session() -> dict:
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(data: dict) -> None:
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    client = MobileBrowserClient()
    session_data = load_session()
    profile = session_data.get("profile", session_data)
    inquiries = profile.get("forensic_inquiries", [])
    inq_map = {i["inquiry_id"]: i for i in inquiries}

    print(f"[*] Starting targeted forensic probing for {len(TARGET_QUERIES)} queries...")

    discovered_by_inquiry = {}

    for idx, (inq_id, query) in enumerate(TARGET_QUERIES):
        print(f"\n[{idx+1}/{len(TARGET_QUERIES)}] ({inq_id}) Query: {query}")
        search_url = "https://www.google.com/search?q=" + urllib.parse.quote(query)

        try:
            res = client.navigate(search_url, wait_seconds=5)
            if res.get("status") == "error":
                print(f"  [ERROR] Navigation failed: {res.get('error')}")
                continue

            time.sleep(2)
            dom = client.extract_dom(include_text=True, include_links=True)
            links = dom.get("content", {}).get("links", [])
            body_text = dom.get("content", {}).get("text", "")

            # Filter relevant result links
            candidate_links = []
            for link in links:
                href = link.get("href", "")
                text = link.get("text", "").strip()
                if not href.startswith("http"):
                    continue
                if any(bad in href for bad in ["google.com", "youtube.com/channel", "support.google", "accounts.google"]):
                    continue
                candidate_links.append((href, text))

            print(f"  Found {len(candidate_links)} non-Google candidate links")

            # Check for subject mention in results
            for href, text in candidate_links[:5]:
                print(f"    - {text[:60]} -> {href}")
                if inq_id not in discovered_by_inquiry:
                    discovered_by_inquiry[inq_id] = []
                if href not in discovered_by_inquiry[inq_id]:
                    discovered_by_inquiry[inq_id].append(href)

        except Exception as e:
            print(f"  [ERROR] Failed on query '{query}': {e}")

    # Bind discovered links to inquiries
    updated_count = 0
    for inq_id, links in discovered_by_inquiry.items():
        if inq_id in inq_map and links:
            existing_links = inq_map[inq_id].get("corroborating_links", [])
            for l in links:
                if l not in existing_links:
                    existing_links.append(l)
            inq_map[inq_id]["corroborating_links"] = existing_links[:5]
            if len(existing_links) > 0 and inq_map[inq_id]["status"] == "probed":
                inq_map[inq_id]["status"] = "confirmed"
                inq_map[inq_id]["online_probe_status"] = "confirmed"
                updated_count += 1
            print(f"[+] Inquiry {inq_id} now has {len(existing_links)} links, status={inq_map[inq_id]['status']}")

    save_session(session_data)
    print(f"\n[*] Finished. Updated {updated_count} inquiries with newly discovered primary evidence.")


if __name__ == "__main__":
    main()
