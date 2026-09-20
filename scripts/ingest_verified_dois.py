#!/usr/bin/env python3
"""Ingest verified research publications by DOI via Crossref metadata into Wikimaker session."""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "http://127.0.0.1:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"

CONFIRMED_DOIS = [
    "10.1016/j.theriogenology.2020.04.003",
    "10.1071/rd18356",
    "10.1007/s11626-015-9920-0",
    "10.1007/s10616-015-9904-7",
    "10.1071/rdv28n2ab24",
    "10.1111/j.1439-0531.2010.01733.x",
    "10.1111/rda.12882",
    "10.1007/978-981-19-3072-0_12",
    "10.1007/978-981-16-7531-7_21",
    "10.1201/9781003220831-16",
    "10.18520/cs/v117/i8/1270-1271",
    "10.48165/aru.2021.1204",
    "10.48165/ijar.2022.43.1.4",
]

def api_post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def fetch_doi_metadata(doi: str) -> dict | None:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(url, headers={"User-Agent": "wikimaker/1.0 (mailto:agent@wikimaker.local)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            msg = data.get("message", {})
            title = (msg.get("title") or [""])[0]
            authors = []
            for a in msg.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                authors.append(f"{given} {family}".strip())
            container = (msg.get("container-title") or [""])[0]
            created = msg.get("created", {}).get("date-parts", [[None]])[0][0]
            abstract = msg.get("abstract", "")
            return {
                "doi": doi,
                "doi_url": f"https://doi.org/{doi}",
                "title": title,
                "authors": ", ".join(authors),
                "journal": container,
                "year": str(created or ""),
                "abstract": abstract,
            }
    except Exception as e:
        print(f"  [WARN] Crossref lookup failed for {doi}: {e}")
        return None

def main():
    session_file = Path("/home/ubuntu/Expeei/wikimaker/sessions") / f"{SESSION_ID}.json"
    existing_urls = set()
    if session_file.exists():
        sdata = json.loads(session_file.read_text())
        existing_urls = {s.get("url", "").lower().rstrip("/") for s in sdata.get("profile", {}).get("sources", [])}

    print(f"[*] Checking {len(CONFIRMED_DOIS)} DOIs against {len(existing_urls)} existing session URLs...")
    ingested = 0

    for doi in CONFIRMED_DOIS:
        doi_url = f"https://doi.org/{doi}"
        if doi.lower() in existing_urls or doi_url.lower() in existing_urls:
            print(f"[*] Skipping existing: {doi_url}")
            continue

        meta = fetch_doi_metadata(doi)
        if not meta:
            continue

        pasted_text = (
            f"Title: {meta['title']}\n"
            f"Authors: {meta['authors']}\n"
            f"Publication / Journal: {meta['journal']} ({meta['year']})\n"
            f"DOI: {meta['doi_url']}\n"
        )
        if meta["abstract"]:
            pasted_text += f"\nAbstract:\n{meta['abstract']}\n"

        print(f"[*] Ingesting: {meta['title'][:60]} ({doi})...")
        try:
            res = api_post("/research/add-source-paste", {
                "profile_name": SESSION_ID,
                "url": meta["doi_url"],
                "pasted_text": pasted_text
            })
            existing_urls.add(doi_url.lower())
            ingested += 1
            print(f"    [OK] Ingested. Source ID: {res.get('source', {}).get('id')}")
        except Exception as e:
            print(f"    [FAIL] Error: {e}")

        time.sleep(1)

    print(f"\n[DONE] Ingested {ingested} DOI publications into session.")
    try:
        api_post("/sessions/resume", {"session_id": SESSION_ID})
        print("[*] Session synchronized.")
    except Exception as se:
        print(f"[*] Sync error: {se}")

if __name__ == "__main__":
    main()
