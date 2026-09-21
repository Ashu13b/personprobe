"""Claim clustering + best-source ranking for draft selection.

The research model is: a *named, AI/human-verified source* yields claims; the
same fact typically appears across many links (mirrors, syndication,
corroborating outlets). This module groups those claims into one fact cluster,
ranks the supporting links, and surfaces the best citation so a human (or the
agent) can pick what goes into the draft — rather than the draft inheriting
whichever link happened to be ingested first.
"""
from __future__ import annotations

from .models import PersonProfile, Source
from .saturation import cluster_claims

# Higher = better citation for the same fact. Independence first (Wikipedia
# wants secondary independent coverage), then subject-specific assessment.
_CATEGORY_RANK = {
    "independent_secondary": 5,
    "record_registry": 4,
    "institutional_bio": 3,
    "authored_publication": 2,
    "general_web": 1,
    "self_published": 0,
    "cv_blueprint": -1,
}
_DEPTH_BONUS = {"significant": 2.0, "passing_mention": 0.0, "unassessed": -0.5}
_TRUST_BONUS = {"high": 1.0, "medium": 0.0, "low": -1.0, "untrusted": -3.0}


def source_citation_rank(source: Source) -> float:
    """Score one source as a citation for a fact (higher is better)."""
    score = float(_CATEGORY_RANK.get(source.provenance_category or "general_web", 1) * 2)
    score += _DEPTH_BONUS.get(source.coverage_depth or "unassessed", -0.5)
    score += _TRUST_BONUS.get(source.domain_trust or "medium", 0.0)
    if source.human_verified:
        score += 1.5
    if source.identity_status == "confirmed":
        score += 0.5
    if source.identity_status == "suspect":
        score -= 2.0
    if source.relevance_flag == "likely_wrong":
        score -= 5.0
    if source.liveness == "alive":
        score += 0.5
    elif source.liveness in ("dead", "blocked"):
        score -= 0.5
    if source.archive_url:
        score += 0.3
    return round(score, 2)


def rank_sources_for_fact(urls: list[str], sources_by_url: dict[str, Source]) -> list[dict]:
    """Rank the links carried by one claim cluster."""
    ranked: list[dict] = []
    for url in urls:
        source = sources_by_url.get(url)
        if source is None:
            ranked.append({"url": url, "rank": -99.0, "title": None, "category": "unknown",
                           "depth": None, "note": "source not in session (mirror/removed)"})
            continue
        ranked.append({
            "url": source.url,
            "rank": source_citation_rank(source),
            "title": source.title,
            "category": source.provenance_category,
            "depth": source.coverage_depth,
            "human_verified": bool(source.human_verified),
            "liveness": source.liveness,
        })
    ranked.sort(key=lambda r: r["rank"], reverse=True)
    return ranked


def build_claim_clusters(profile: PersonProfile) -> list[dict]:
    """Fact clusters with their supporting links, ranked and marked for selection."""
    sources_by_url = {s.url: s for s in profile.sources}
    out: list[dict] = []
    for cluster in cluster_claims(profile.claims):
        canonical = profile.claims[cluster.claim_indices[0]] if cluster.claim_indices else None
        # cluster_claims picks the longest text as canonical; find its index
        canon_idx = max(cluster.claim_indices, key=lambda i: len(profile.claims[i].text)) if cluster.claim_indices else None
        canon_claim = profile.claims[canon_idx] if canon_idx is not None else None
        ranked = rank_sources_for_fact(cluster.corroborating_sources, sources_by_url)
        approved = [i for i in cluster.claim_indices if profile.claims[i].draft_approved]
        out.append({
            "cluster_id": f"cl-{canon_idx}",
            "canonical_text": cluster.canonical_text,
            "field": cluster.field,
            "claim_indices": cluster.claim_indices,
            "repetition_count": cluster.repetition_count,
            "canonical_index": canon_idx,
            "link_count": len(cluster.corroborating_sources),
            "sources": ranked,
            "best_source_url": ranked[0]["url"] if ranked else None,
            "best_source_rank": ranked[0]["rank"] if ranked else None,
            "approved_indices": approved,
            "approved": bool(approved),
        })
    # multi-link facts first, then single-link; approved sink lower
    out.sort(key=lambda c: (c["approved"], -c["link_count"], -(c["best_source_rank"] or 0)))
    return out
