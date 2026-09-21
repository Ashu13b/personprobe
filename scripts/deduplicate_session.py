#!/usr/bin/env python3
"""Canonical URL deduplication for PersonProbe research session.

Ensures that no exact same duplicate links exist in the session due to:
- Trailing slashes (/ vs non-/)
- Scheme differences (http:// vs https://)
- Subdomain differences (www. vs non-www)
- Case insensitivity in paths or DOIs (10.1016/J.ANIREPROSCI... vs 10.1016/j.anireprosci...)
- Tracking parameters (?utm_*, ?_tp=*, #anchors)

Merges claims and metadata so no verified information is lost.
"""

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "http://127.0.0.1:3890/api"
SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/wikimaker/sessions/{SESSION_ID}.json")

DOMAIN_ALIAS_MAP = {
    "icar.gov.in": "icar.org.in",
    "timesofindia.com": "timesofindia.indiatimes.com",
    "m.timesofindia.com": "timesofindia.indiatimes.com",
    "m.timesofindia.indiatimes.com": "timesofindia.indiatimes.com",
    "m.jagran.com": "jagran.com",
    "m.bhaskar.com": "bhaskar.com",
    "m.punjabkesari.in": "punjabkesari.in",
    "m.haryana.punjabkesari.in": "punjabkesari.in",
    "m.amarujala.com": "amarujala.com"
}

def canonical_url(url: str) -> str:
    if not url:
        return ""
    u = url.strip()
    p = urllib.parse.urlparse(u)
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    
    # Map domain aliases and mobile mirrors
    if netloc in DOMAIN_ALIAS_MAP:
        netloc = DOMAIN_ALIAS_MAP[netloc]
    elif netloc.startswith("m.") and netloc[2:] in DOMAIN_ALIAS_MAP:
        netloc = DOMAIN_ALIAS_MAP[netloc[2:]]
    elif netloc.startswith("m."):
        netloc = netloc[2:]

    path = p.path.rstrip("/")

    # Normalize DOIs
    if "doi.org" in netloc:
        doi_match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", path)
        if doi_match:
            return f"https://doi.org/{doi_match.group(1).lower()}"

    # Strip tracking and amp parameters
    clean_params = []
    if p.query:
        params = urllib.parse.parse_qsl(p.query)
        for k, v in params:
            k_low = k.lower()
            if not any(k_low.startswith(prefix) for prefix in ["utm_", "_tp", "fbclid", "gclid", "ref", "source", "amp"]):
                clean_params.append((k, v))
    query_str = urllib.parse.urlencode(clean_params)

    # Normalize amp paths
    clean_path = path.replace("/amp/", "/").replace("/amp_articleshow/", "/articleshow/")
    if clean_path.endswith("/amp"):
        clean_path = clean_path[:-4]

    res = f"https://{netloc}{clean_path}"
    if query_str:
        res += f"?{query_str}"
    return res.lower()

def deduplicate():
    if not SESSION_FILE.exists():
        print(f"Session file {SESSION_FILE} not found.")
        return

    data = json.loads(SESSION_FILE.read_text())
    profile = data["profile"]
    sources = profile.get("sources", [])
    claims = profile.get("claims", [])

    print(f"[*] Initial sources: {len(sources)} | Initial claims: {len(claims)}")

    canonical_map = {}
    url_redirect_map = {}
    deduped_sources = []

    for s in sources:
        raw_url = s.get("url", "")
        canon = canonical_url(raw_url)
        if not canon:
            continue

        if canon in canonical_map:
            # Duplicate found! Merge metadata into existing entry
            existing = canonical_map[canon]
            # Record redirect
            url_redirect_map[raw_url] = existing.get("url")

            # Merge fields
            if s.get("human_verified"):
                existing["human_verified"] = True
            if len(s.get("snippet", "") or "") > len(existing.get("snippet", "") or ""):
                existing["snippet"] = s.get("snippet")
            if not existing.get("date") and s.get("date"):
                existing["date"] = s.get("date")
            if not existing.get("editorial_origin") and s.get("editorial_origin"):
                existing["editorial_origin"] = s.get("editorial_origin")
            if not existing.get("research_notes") and s.get("research_notes"):
                existing["research_notes"] = s.get("research_notes")
            if existing.get("liveness") != "alive" and s.get("liveness") == "alive":
                existing["liveness"] = "alive"
        else:
            canonical_map[canon] = s
            deduped_sources.append(s)

    # Re-point claims whose source_url was merged
    for c in claims:
        src_url = c.get("source_url")
        if src_url in url_redirect_map:
            c["source_url"] = url_redirect_map[src_url]

    dropped_count = len(sources) - len(deduped_sources)
    print(f"[*] Dropped {dropped_count} exact duplicate source links.")
    print(f"[*] Deduped sources count: {len(deduped_sources)}")

    profile["sources"] = deduped_sources
    profile["claims"] = claims
    data["profile"] = profile

    SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # Sync via API
    try:
        req = urllib.request.Request(
            API_BASE + "/sessions/resume",
            data=json.dumps({"session_id": SESSION_ID}).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=30)
        print("[*] Session resumed and synchronized via backend.")
    except Exception as e:
        print(f"[*] Sync error: {e}")

if __name__ == "__main__":
    deduplicate()
