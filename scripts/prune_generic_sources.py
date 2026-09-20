#!/usr/bin/env python3
"""Prune generic institutional pages, circular links, and job postings from the research session."""

import json
from pathlib import Path
from scripts.deduplicate_session import canonical_url, deduplicate

SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/wikimaker/sessions/{SESSION_ID}.json")

URLS_TO_PRUNE = {
    canonical_url("https://en.wikipedia.org/wiki/Central_Institute_for_Research_on_Buffaloes"), # WP:CIRCULAR
    canonical_url("https://cirb.res.in/hisar-1/"),                                            # General campus page
    canonical_url("https://krishijagran.com/jobs/senior-research-fellow-srf-at-icar-cirb-hisar-haryana/"), # Job posting
    canonical_url("https://www.icar.org.in/sites/default/files/inline-files/Nanaji-Deshmukh-2021.pdf"),     # Award rules PDF
    canonical_url("https://cirb.res.in/awards/"),                                            # Empty awards index
    canonical_url("https://cirb.res.in/"),                                                  # Institute homepage
    canonical_url("https://www.issrf.org/issrf-awards/prof-s-s-guraya-memorial-oration"),    # General ISSRF list
    canonical_url("https://www.pashudhanpraharee.com/improving-buffalo-welfare-through-the-use-of-r"), # General article
    canonical_url("https://readingsbell.com/buffalo/")                                      # SEO blog
}

def main():
    if not SESSION_FILE.exists():
        print("Missing session file.")
        return

    data = json.loads(SESSION_FILE.read_text())
    profile = data.get("profile", {})
    sources = profile.get("sources", [])
    claims = profile.get("claims", [])

    print(f"[*] Initial sources: {len(sources)} | Initial claims: {len(claims)}")

    kept_sources = []
    pruned_sources = []
    for s in sources:
        can = canonical_url(s.get("url"))
        if can in URLS_TO_PRUNE:
            pruned_sources.append(s)
        else:
            kept_sources.append(s)

    kept_claims = []
    pruned_claims = []
    for c in claims:
        can = canonical_url(c.get("source_url"))
        if can in URLS_TO_PRUNE:
            pruned_claims.append(c)
        else:
            kept_claims.append(c)

    print(f"[*] Pruned {len(pruned_sources)} generic/irrelevant sources:")
    for s in pruned_sources:
        print(f"    - [{s.get('title')}]({s.get('url')})")

    print(f"[*] Pruned {len(pruned_claims)} unapproved placeholder claims bound to pruned sources:")
    for c in pruned_claims:
        print(f"    - Text: {c.get('text')[:80]}...")

    profile["sources"] = kept_sources
    profile["claims"] = kept_claims
    data["profile"] = profile

    SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"[*] Updated session: {len(kept_sources)} sources, {len(kept_claims)} claims.")

    deduplicate()

if __name__ == "__main__":
    main()
