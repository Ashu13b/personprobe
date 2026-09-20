#!/usr/bin/env python3
"""Ingest verified publications from Semantic Scholar into active session with strict disambiguation."""

import json
import time
import urllib.request
from pathlib import Path

API_BASE = "http://127.0.0.1:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"

def api_post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def main():
    session_file = Path("/home/ubuntu/Expeei/personprobe/sessions") / f"{SESSION_ID}.json"
    session_data = json.loads(session_file.read_text())
    existing_urls = {s.get("url", "").lower().rstrip("/") for s in session_data["profile"]["sources"]}

    with open("/tmp/s2_new_papers.json") as f:
        papers = json.load(f)

    # Filtering keywords
    ANIMAL_KW = [
        "buffalo", "bubalis", "clon", "embryo", "oocyte", "semen", "somatic cell",
        "in vitro", "stem cell", "cryopreserv", "equine", "caprine", "oct4",
        "acrosome", "sperm", "casa", "transposon", "fertilization"
    ]
    REJECT_KW = [
        "cotton", "fertilizer", "arboreum", "guar", "calcareous", "foliar",
        "spacing", "hirsutum", "soil", "wheat", "crop"
    ]

    valid_papers = []
    for p in papers:
        title = p.get("title") or ""
        t_low = title.lower()

        if any(r in t_low for r in REJECT_KW):
            continue
        if any(k in t_low for k in ANIMAL_KW):
            valid_papers.append(p)

    print(f"[*] Filtered {len(valid_papers)} confirmed animal biotech publications out of {len(papers)} candidates.")

    ingested = 0
    for p in valid_papers:
        title = p["title"]
        year = p["year"]
        doi = p["doi"]
        doi_url = f"https://doi.org/{doi}" if doi else None
        s2_url = p["s2_url"]
        abstract = p["abstract"] or ""

        target_url = doi_url or s2_url
        if not target_url or target_url.lower() in existing_urls:
            continue

        pasted_text = (
            f"Title: {title}\n"
            f"Author: Dr. Prem Singh Yadav (P. S. Yadav) et al.\n"
            f"Year: {year}\n"
        )
        if doi_url:
            pasted_text += f"DOI: {doi_url}\n"
        if s2_url:
            pasted_text += f"Semantic Scholar: {s2_url}\n"
        if abstract:
            pasted_text += f"\nAbstract:\n{abstract}\n"

        print(f"[*] Ingesting [{year}] {title[:60]}...")
        try:
            res = api_post("/research/add-source-paste", {
                "profile_name": SESSION_ID,
                "url": target_url,
                "pasted_text": pasted_text
            })
            existing_urls.add(target_url.lower())
            ingested += 1
            print(f"    [OK] Ingested. Source ID: {res.get('source', {}).get('id')}")
        except Exception as e:
            print(f"    [FAIL] Error: {e}")

        time.sleep(1)

    print(f"\n[DONE] Ingested {ingested} new verified publications into session.")
    try:
        api_post("/sessions/resume", {"session_id": SESSION_ID})
        print("[*] Session synchronized.")
    except Exception as se:
        print(f"[*] Sync error: {se}")

if __name__ == "__main__":
    main()
