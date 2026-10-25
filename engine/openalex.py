"""OpenAlex Academic Intelligence Graph Adapter.

Provides open, non-rate-limited scholarly entity resolution for researchers,
institutional affiliations, co-author networks, and grant attribution.
"""

from __future__ import annotations

import re
from typing import Any, Optional
import requests

from .models import Source, SourceReliability

OPENALEX_API_BASE = "https://api.openalex.org"
OPENALEX_HEADERS = {"User-Agent": "PersonProbe/0.2 (mailto:ay.yadav53@gmail.com)"}


def search_author(
    name: str, institution_hint: Optional[str] = None
) -> list[dict[str, Any]]:
    """Search OpenAlex for author entities matching the subject name and optional institution."""
    clean_name = (name or "").strip()
    if not clean_name:
        return []

    url = f"{OPENALEX_API_BASE}/authors"
    params: dict[str, str] = {"search": clean_name}

    try:
        r = requests.get(url, params=params, headers=OPENALEX_HEADERS, timeout=12)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    authors: list[dict[str, Any]] = []
    for item in data.get("results", []):
        inst_list = item.get("last_known_institutions") or []
        affil_names = [
            inst.get("display_name", "")
            for inst in inst_list
            if inst.get("display_name")
        ]
        h_idx = (item.get("summary_stats") or {}).get("h_index", 0)
        author_id = item.get("id", "").split("/")[-1]

        entry = {
            "id": author_id,
            "openalex_id": item.get("id", ""),
            "display_name": item.get("display_name", ""),
            "affiliations": affil_names,
            "works_count": item.get("works_count", 0),
            "cited_by_count": item.get("cited_by_count", 0),
            "h_index": h_idx,
            "orcid": item.get("orcid"),
        }

        # Calculate a relevance match score if institution hint is provided
        relevance_score = 1.0
        if institution_hint and affil_names:
            hint_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", institution_hint.lower()))
            aff_tokens = set(
                re.findall(r"\b[a-zA-Z]{3,}\b", " ".join(affil_names).lower())
            )
            if hint_tokens & aff_tokens:
                relevance_score += 2.0

        entry["relevance_score"] = relevance_score
        authors.append(entry)

    # Sort best matches first
    authors.sort(key=lambda a: (-a["relevance_score"], -a["works_count"]))
    return authors


def get_author_works(openalex_author_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve indexed works for a resolved OpenAlex author ID."""
    clean_id = openalex_author_id.strip().split("/")[-1]
    if not clean_id:
        return []

    url = f"{OPENALEX_API_BASE}/works"
    params = {
        "filter": f"author.id:{clean_id}",
        "per_page": str(min(limit, 100)),
        "sort": "publication_year:desc",
    }

    try:
        r = requests.get(url, params=params, headers=OPENALEX_HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    works: list[dict[str, Any]] = []
    for w in data.get("results", []):
        doi = w.get("doi")
        title = (w.get("title") or "").strip()
        year = w.get("publication_year")
        venue = (w.get("primary_location") or {}).get("source", {}) or {}
        publisher = venue.get("display_name") or "Academic Journal"
        host_url = (w.get("primary_location") or {}).get("landing_page_url") or doi

        authorships = w.get("authorships") or []
        coauthors: list[str] = []
        for auth in authorships:
            name = (auth.get("author") or {}).get("display_name")
            if name:
                coauthors.append(name)

        grants_info: list[dict[str, str]] = []
        for g in w.get("grants") or []:
            funder = g.get("funder_display_name") or ""
            award_id = g.get("award_id") or ""
            if funder or award_id:
                grants_info.append({"funder": funder, "award_id": award_id})

        works.append(
            {
                "id": w.get("id"),
                "doi": doi,
                "title": title,
                "year": year,
                "publisher": publisher,
                "url": host_url
                or (f"https://openalex.org/{w.get('id')}" if w.get("id") else ""),
                "cited_by_count": w.get("cited_by_count", 0),
                "coauthors": coauthors,
                "grants": grants_info,
                "is_oa": (w.get("open_access") or {}).get("is_oa", False),
            }
        )

    return works


def convert_works_to_sources(
    works: list[dict[str, Any]], author_name: str
) -> list[Source]:
    """Convert OpenAlex work records into structured Source objects."""
    sources: list[Source] = []
    for w in works:
        target_url = w.get("url") or w.get("doi")
        if not target_url:
            continue

        title = w.get("title") or f"Research publication by {author_name}"
        year = w.get("year")
        publisher = w.get("publisher") or "Academic Publisher"

        src = Source(
            url=target_url,
            title=title,
            publisher=publisher,
            date=str(year) if year else None,
            reliability=SourceReliability.reliable_secondary,
            workflow_stage="retrieved",
            editorial_origin=publisher,
            coverage_depth="passing_mention",
            provenance_category="authored_publication",
            is_independent=False,
            identity_status="confirmed",
            identity_by="agent",
            author_match_status="confirmed",
            liveness="alive",
            liveness_by="agent",
            fetched_by="agent",
        )
        sources.append(src)
    return sources
