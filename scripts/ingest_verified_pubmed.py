#!/usr/bin/env python3
"""Ingest verified PubMed peer-reviewed papers for Dr. Prem Singh Yadav into active session."""

import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

API_BASE = "http://127.0.0.1:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"

CONFIRMED_PMIDS = [
    "41527787", "41009405", "40229609", "39498956", "39178617",
    "39042556", "39029316", "38200865", "38035499", "37042654",
    "36958101", "36880183", "35451101", "33301776", "32822364",
    "31388074", "29851497", "25373338", "25141841"
]

def api_post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def fetch_pubmed_details(pmids: list[str]) -> list[dict]:
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(pmids)}&retmode=xml"
    req = urllib.request.Request(url, headers={"User-Agent": "personprobe/1.0"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())

    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.find(".//MedlineCitation/PMID").text
        title = (article.find(".//ArticleTitle").text or "").strip()
        
        # Abstract
        abstract_parts = []
        for ab in article.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            text = ab.text or ""
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = "\n\n".join(abstract_parts)

        # Journal & Date
        journal = article.find(".//Journal/Title")
        journal_title = journal.text if journal is not None else ""
        pub_year = article.find(".//JournalIssue/PubDate/Year")
        year_str = pub_year.text if pub_year is not None else ""

        # Authors
        authors = []
        for a in article.findall(".//AuthorList/Author"):
            last = a.find("LastName")
            fore = a.find("ForeName")
            l_str = last.text if last is not None and last.text else ""
            f_str = fore.text if fore is not None and fore.text else ""
            if l_str:
                authors.append(f"{f_str} {l_str}".strip())

        # DOI
        doi = None
        for aid in article.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = aid.text
                break

        results.append({
            "pmid": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "title": title,
            "abstract": abstract,
            "journal": journal_title,
            "year": year_str,
            "authors": ", ".join(authors),
        })
    return results

def main():
    print(f"[*] Fetching details for {len(CONFIRMED_PMIDS)} confirmed PMIDs...")
    details = fetch_pubmed_details(CONFIRMED_PMIDS)
    print(f"[*] Retrieved {len(details)} articles from NCBI.")

    session_file = Path("/home/ubuntu/Expeei/personprobe/sessions") / f"{SESSION_ID}.json"
    existing_urls = set()
    if session_file.exists():
        sdata = json.loads(session_file.read_text())
        existing_urls = {s.get("url", "").lower().rstrip("/") for s in sdata.get("profile", {}).get("sources", [])}

    ingested = 0
    for doc in details:
        url = doc["url"]
        norm_url = url.lower().rstrip("/")
        if norm_url in existing_urls:
            print(f"[*] Skipping already present: {url}")
            continue

        pasted_text = (
            f"Title: {doc['title']}\n"
            f"Authors: {doc['authors']}\n"
            f"Journal: {doc['journal']} ({doc['year']})\n"
            f"PMID: {doc['pmid']}\n"
        )
        if doc["doi_url"]:
            pasted_text += f"DOI: {doc['doi_url']}\n"
        pasted_text += f"\nAbstract:\n{doc['abstract']}\n"

        print(f"[*] Ingesting PMID {doc['pmid']}: {doc['title'][:60]}...")
        try:
            res = api_post("/research/add-source-paste", {
                "profile_name": SESSION_ID,
                "url": url,
                "pasted_text": pasted_text
            })
            existing_urls.add(norm_url)
            ingested += 1
            print(f"    [OK] Ingested. Source ID: {res.get('source', {}).get('id')}")
        except Exception as e:
            print(f"    [FAIL] Error ingesting {url}: {e}")

        # Also ingest DOI mirror if available
        if doc["doi_url"] and doc["doi_url"].lower().rstrip("/") not in existing_urls:
            try:
                api_post("/research/add-source-paste", {
                    "profile_name": SESSION_ID,
                    "url": doc["doi_url"],
                    "pasted_text": pasted_text
                })
                existing_urls.add(doc["doi_url"].lower().rstrip("/"))
            except Exception:
                pass

        time.sleep(1)

    print(f"\n[DONE] Successfully ingested {ingested} PubMed sources and DOI mirrors into session {SESSION_ID}.")
    api_post("/sessions/resume", {"session_id": SESSION_ID})
    print("[*] Session resumed and saved.")

if __name__ == "__main__":
    main()
