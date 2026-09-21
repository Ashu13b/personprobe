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


# Draft-readiness statuses
READY = "ready"                          # verified source + settled fact -> approve directly
NEEDS_CONFIRM = "needs_confirmation"     # verified source, claim itself unconfirmed -> approving confirms it
NEEDS_SOURCE = "needs_source_verification"  # claim fine, source not verified yet
BLOCKED = "blocked"                      # cv/wrong-person/no source -> never suggest


def _claim_source(profile: PersonProfile, url: str | None) -> Source | None:
    if not url:
        return None
    return next((s for s in profile.sources if s.url == url), None)


def evaluate_claim(profile: PersonProfile, index: int, cluster_link_count: int) -> dict:
    """Assess one claim's readiness for the draft, with reasons."""
    claim = profile.claims[index]
    source = _claim_source(profile, claim.source_url)
    blockers: list[str] = []
    notes: list[str] = []

    if source is None:
        blockers.append("no source attached")
    else:
        if (source.provenance_category == "cv_blueprint"):
            blockers.append("source is CV input, never citable evidence")
        if source.relevance_flag == "likely_wrong" or source.identity_status == "wrong_person":
            blockers.append("source belongs to a different person / namesake")
        if source.identity_status == "suspect":
            blockers.append("identity unconfirmed (initials-only match)")
        if not blockers and not (source.human_verified or source.identity_status == "confirmed"):
            notes.append("source identity not yet verified")
        if source.liveness in ("dead", "blocked") and not source.archive_url:
            notes.append(f"link is {source.liveness} without archive")

    if claim.verification.value == "skipped":
        blockers.append("claim was skipped in review")

    status = BLOCKED if blockers else NEEDS_SOURCE if not (source and (source.human_verified or source.identity_status == "confirmed")) else (
        READY if claim.verification.value in ("confirmed", "edited") else NEEDS_CONFIRM
    )

    rank = source_citation_rank(source) if source else -99.0
    score = rank
    if status == READY:
        score += 6
    elif status == NEEDS_CONFIRM:
        score += 3
    score += min(cluster_link_count, 6)
    if claim.settled_quote:
        score += 1.0

    return {
        "claim_index": index,
        "text": claim.text,
        "field": claim.field,
        "verification": claim.verification.value,
        "source_url": claim.source_url,
        "source_title": source.title if source else None,
        "source_rank": rank,
        "link_count": cluster_link_count,
        "status": status,
        "blockers": blockers,
        "notes": notes,
        "score": round(score, 2),
        "has_quote": bool(claim.settled_quote),
    }


def suggest_draft_upgrades(profile: PersonProfile, limit: int = 60) -> dict:
    """Rank not-yet-approved facts for draft inclusion — one suggestion per fact.

    The pipeline is: named+verified source -> claims -> same fact across many
    links -> pick the best claim/link. Duplicate members of one fact cluster are
    collapsed so the reviewer sees each fact once, on its strongest wording.
    """
    clusters = build_claim_clusters(profile)
    seen: set[int] = set()
    suggestions: list[dict] = []
    approved_facts = 0

    for cluster in clusters:
        members = [i for i in cluster["claim_indices"] if not profile.claims[i].draft_approved]
        if not members:
            approved_facts += 1
            continue
        # best member = canonical wording if still open, else the one with the best source
        candidate = cluster["canonical_index"] if cluster["canonical_index"] in members else members[0]
        best = max((evaluate_claim(profile, i, cluster["link_count"]) for i in members),
                   key=lambda e: e["score"])
        chosen = best if candidate not in members else evaluate_claim(profile, candidate, cluster["link_count"])
        # prefer the highest-scoring member unless canonical is materially better sourced
        if best["score"] > chosen["score"]:
            chosen = best
        for i in members:
            seen.add(i)
        chosen["cluster_id"] = cluster["cluster_id"]
        chosen["fact"] = cluster["canonical_text"]
        suggestions.append(chosen)

    # claims outside any cluster (shouldn't happen, but stay safe)
    for i, claim in enumerate(profile.claims):
        if i in seen or claim.draft_approved:
            continue
        suggestions.append(evaluate_claim(profile, i, 1))

    suggestions.sort(key=lambda s: (s["status"] == BLOCKED, -s["score"]))
    ready = [s for s in suggestions if s["status"] == READY]
    return {
        "suggestions": suggestions[:limit],
        "counts": {
            "ready": len(ready),
            "needs_confirmation": sum(1 for s in suggestions if s["status"] == NEEDS_CONFIRM),
            "needs_source_verification": sum(1 for s in suggestions if s["status"] == NEEDS_SOURCE),
            "blocked": sum(1 for s in suggestions if s["status"] == BLOCKED),
            "already_approved_facts": approved_facts,
        },
    }
