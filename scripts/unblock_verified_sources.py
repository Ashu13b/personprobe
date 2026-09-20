#!/usr/bin/env python3
"""Update liveness status of sources verified via the OpenScrape scrap browser."""

import json
from pathlib import Path
from scripts.deduplicate_session import canonical_url, deduplicate

SESSION_ID = "py-prem-singh-yadav-569e5aea"
SESSION_FILE = Path(f"/home/ubuntu/Expeei/wikimaker/sessions/{SESSION_ID}.json")

def main():
    if not SESSION_FILE.exists():
        print("Session file missing.")
        return

    data = json.loads(SESSION_FILE.read_text())
    profile = data.get("profile", {})
    sources = profile.get("sources", [])

    # URLs confirmed alive via scrap browser
    unblocked_alive = {
        canonical_url("https://www.ndtv.com/india-news/indias-first-cloned-assamese-buffalo-born-1824454"),
        canonical_url("https://www.india.com/education/cirb-became-the-second-institute-to-produce-cloned-buffalo-named-hisar-gaurav-1572570/"),
        canonical_url("https://www.researchgate.net/publication/374928871_Electroporation-based_CRISPR_gene_editing_in_adult_buffalo_fibroblast_cells"),
        canonical_url("https://www.researchgate.net/publication/369975794_Production_of_MSTN_Gene-Edited_Embryos_of_Buffalo_Using_the_CRISPRCas9_System_and_SCNT"),
        canonical_url("https://www.researchgate.net/publication/365392992_Buffalo_Cloning")
    }

    # Truncated typo to remove
    typo_url = canonical_url("https://www.ndtv.com/india-news/indias-first-cloned-assamese-buffalo-born-182445")

    cleaned_sources = []
    unblocked_count = 0

    for s in sources:
        can = canonical_url(s.get("url", ""))
        if can == typo_url:
            print(f"[*] Pruning truncated scraper typo: {s.get('url')}")
            continue

        if can in unblocked_alive:
            old_liveness = s.get("liveness")
            s["liveness"] = "alive"
            s["human_verified"] = True
            if "researchgate" in s.get("url", "").lower() and s.get("title") == "researchgate.net":
                if "374928871" in s.get("url", ""):
                    s["title"] = "Electroporation-based CRISPR gene editing in adult buffalo fibroblast cells - ResearchGate"
                elif "369975794" in s.get("url", ""):
                    s["title"] = "Production of MSTN Gene-Edited Embryos of Buffalo Using CRISPR/Cas9 System and SCNT - ResearchGate"
                elif "365392992" in s.get("url", ""):
                    s["title"] = "Buffalo Cloning - ResearchGate"
            s["research_notes"] = (s.get("research_notes", "") + " [Verified alive via OpenScrape mobile browser]").strip()
            print(f"[*] Unblocked/Verified ALIVE ({old_liveness} -> alive): {s.get('url')}")
            unblocked_count += 1

        cleaned_sources.append(s)

    profile["sources"] = cleaned_sources
    data["profile"] = profile

    SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"[*] Successfully updated {unblocked_count} sources to ALIVE.")
    print(f"[*] New source count: {len(cleaned_sources)}")

    deduplicate()

if __name__ == "__main__":
    main()
