"""Comprehensive research lifecycle audit engine for Wikimaker.

Audits a subject profile across all 4 development lifecycle stages:
Stage 1: Discovery & Acquisition Health (liveness, name matching, discarded registry, mobile bridge)
Stage 2: Source Provenance & Notability (independence, editorial origins, depth, WP:GNG / WP:PROF)
Stage 3: Claim Quality & Saturation (trust score distribution, corroboration, diminishing returns)
Stage 4: Draft Readiness & AfC Compliance (identity lead evidence, citation hygiene, draft readiness)
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from .mobile_bridge import is_mobile_bridge_available
from .models import PersonProfile
from wiki.draft import audit_profile


@dataclass
class StageAuditItem:
    stage_id: str
    label: str
    status: str  # "completed" | "in_progress" | "blocked" | "attention_needed"
    score: float  # 0.0 to 1.0
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class FullLifecycleAudit:
    current_stage: str
    overall_health: str  # "healthy" | "needs_attention" | "blocked"
    completion_rate: float  # 0.0 to 1.0
    stages: list[StageAuditItem]
    next_action: str
    mobile_bridge_online: bool


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def audit_discovery_stage(profile: PersonProfile) -> StageAuditItem:
    """Audit Stage 1: Candidate link discovery, liveness, and discarded registry."""
    total_sources = len(profile.sources)
    discarded_list = getattr(profile, "discarded_sources", []) or []
    total_discarded = len(discarded_list)

    # Liveness breakdown
    liveness_counts = Counter(getattr(s, "liveness", "unknown") for s in profile.sources)
    alive_count = liveness_counts.get("alive", 0)
    dead_archived = sum(1 for s in profile.sources if getattr(s, "liveness", "") == "dead" and getattr(s, "archive_url", None))
    dead_unarchived = sum(1 for s in profile.sources if getattr(s, "liveness", "") == "dead" and not getattr(s, "archive_url", None))
    blocked_count = liveness_counts.get("blocked", 0)

    # Discarded reasons breakdown
    discarded_reasons = Counter(getattr(d, "reason", "no_name_match") for d in discarded_list)

    recommendations: list[str] = []
    if dead_unarchived > 0:
        recommendations.append(f"{dead_unarchived} source(s) are dead with no Wayback archive. Archive or replace them.")
    if blocked_count > 0:
        recommendations.append(f"{blocked_count} source(s) blocked by bot mitigation. Use the mobile scrap browser to unblock.")
    if discarded_reasons.get("homonym_risk", 0) > 0:
        recommendations.append(f"{discarded_reasons['homonym_risk']} link(s) flagged as homonym risk. Inspect in Discarded tab.")
    if discarded_reasons.get("no_name_match", 0) > 0:
        recommendations.append(f"{discarded_reasons['no_name_match']} link(s) discarded due to name match. Audit for script/name variants.")

    # Status & Score
    if total_sources == 0:
        status = "blocked"
        score = 0.0
        summary = "No sources discovered yet."
    elif dead_unarchived > 0:
        status = "attention_needed"
        score = max(0.4, min(0.9, alive_count / max(1, total_sources)))
        summary = f"{total_sources} active sources; {dead_unarchived} dead without archive."
    else:
        status = "completed" if total_sources >= 5 else "in_progress"
        score = min(1.0, total_sources / 10.0)
        summary = f"{total_sources} active sources ({alive_count} verified alive), {total_discarded} discarded in registry."

    return StageAuditItem(
        stage_id="discovery",
        label="Discovery & Acquisition",
        status=status,
        score=round(score, 2),
        summary=summary,
        metrics={
            "total_active_sources": total_sources,
            "total_discarded": total_discarded,
            "alive_count": alive_count,
            "dead_archived": dead_archived,
            "dead_unarchived": dead_unarchived,
            "blocked_count": blocked_count,
            "discarded_reasons": dict(discarded_reasons),
        },
        recommendations=recommendations,
    )


def audit_provenance_stage(profile: PersonProfile) -> StageAuditItem:
    """Audit Stage 2: Source provenance, independence, editorial origins, and WP:GNG."""
    verified_sources = [s for s in profile.sources if s.human_verified]
    total_sources = len(profile.sources)
    verified_count = len(verified_sources)

    # Independence and categories
    independent_sources = [s for s in verified_sources if getattr(s, "is_independent", True) and s.reliability.value == "reliable_secondary"]
    independent_hosts = {_host(s.url) for s in independent_sources}
    significant_origins = {
        (s.editorial_origin or _host(s.url)).strip().lower()
        for s in independent_sources
        if s.coverage_depth == "significant"
    }
    significant_origins.discard("")

    categories = Counter(getattr(s, "provenance_category", "general_web") for s in profile.sources)
    missing_slots = profile.missing_slots or []

    recommendations: list[str] = []
    if verified_count == 0 and total_sources > 0:
        recommendations.append("Verify active sources to confirm they describe the subject.")
    if len(independent_hosts) < 2:
        recommendations.append(f"AfC requires at least 2 independent secondary origins (currently {len(independent_hosts)}).")
    if len(significant_origins) < 2:
        recommendations.append(f"Only {len(significant_origins)} origin(s) assessed as significant coverage. Review source depth.")
    if missing_slots:
        recommendations.append(f"Missing key biographical slots: {', '.join(missing_slots[:4])}.")

    if verified_count == 0:
        status = "blocked" if total_sources > 0 else "in_progress"
        score = 0.0
        summary = "No sources human-verified yet."
    elif len(independent_hosts) < 2:
        status = "attention_needed"
        score = 0.5
        summary = f"{verified_count} sources verified, but only {len(independent_hosts)} independent origin(s)."
    else:
        status = "completed"
        score = 1.0 if len(significant_origins) >= 2 else 0.8
        summary = f"{verified_count} verified sources across {len(independent_hosts)} independent host(s)."

    return StageAuditItem(
        stage_id="provenance",
        label="Provenance & Notability",
        status=status,
        score=round(score, 2),
        summary=summary,
        metrics={
            "verified_count": verified_count,
            "unverified_count": total_sources - verified_count,
            "independent_origins_count": len(independent_hosts),
            "significant_origins_count": len(significant_origins),
            "categories": dict(categories),
            "missing_slots_count": len(missing_slots),
        },
        recommendations=recommendations,
    )


def audit_claims_stage(profile: PersonProfile) -> StageAuditItem:
    """Audit Stage 3: Claim extraction, verification, corroboration, and saturation."""
    total_claims = len(profile.claims)
    unverified_claims = [c for c in profile.claims if c.verification.value == "unverified"]
    draft_approved_claims = [c for c in profile.claims if c.draft_approved]
    research_only_claims = [
        c for c in profile.claims
        if not c.draft_approved and c.verification.value in ("confirmed", "edited")
    ]

    saturation = profile.saturation
    sat_score = saturation.score if saturation else 0.0
    sat_level = saturation.level if saturation else "exploring"

    recommendations: list[str] = []
    if len(unverified_claims) > 0:
        recommendations.append(f"{len(unverified_claims)} claims pending verification. Review or dismiss them.")
    if total_claims > 0 and len(draft_approved_claims) == 0:
        recommendations.append("No claims selected for draft yet. Approve key verified claims.")
    if sat_level == "saturated":
        recommendations.append("Research is saturated; fact repetition is high. Proceed to drafting.")

    if total_claims == 0:
        status = "in_progress"
        score = 0.0
        summary = "No claims extracted yet."
    elif len(unverified_claims) > 0 and len(draft_approved_claims) == 0:
        status = "in_progress"
        score = 0.4
        summary = f"{total_claims} claims extracted; {len(unverified_claims)} awaiting review."
    elif len(draft_approved_claims) > 0:
        status = "completed"
        score = 1.0
        summary = f"{len(draft_approved_claims)} claims approved for draft, {len(research_only_claims)} in research dossier."
    else:
        status = "in_progress"
        score = 0.6
        summary = f"{len(research_only_claims)} confirmed claims in dossier; none approved for draft."

    return StageAuditItem(
        stage_id="claims",
        label="Claims & Saturation",
        status=status,
        score=round(score, 2),
        summary=summary,
        metrics={
            "total_claims": total_claims,
            "unverified_claims": len(unverified_claims),
            "draft_approved_claims": len(draft_approved_claims),
            "research_only_claims": len(research_only_claims),
            "saturation_level": sat_level,
            "saturation_score": sat_score,
        },
        recommendations=recommendations,
    )


def audit_draft_stage(profile: PersonProfile) -> StageAuditItem:
    """Audit Stage 4: AfC compliance, wikitext generation, and blocker analysis."""
    draft_audit = audit_profile(profile)
    ready = draft_audit.ready
    blockers = [b.model_dump() for b in draft_audit.blockers]
    warnings = [w.model_dump() for w in draft_audit.warnings]

    has_en_draft = bool(profile.wikitext_en and len(profile.wikitext_en) > 100)
    has_hi_draft = bool(profile.wikitext_hi and len(profile.wikitext_hi) > 100)

    recommendations: list[str] = []
    for b in draft_audit.blockers:
        recommendations.append(b.message)
    if ready and not has_en_draft:
        recommendations.append("Draft evidence is ready! Click 'Generate AfC Draft'.")

    if not ready:
        status = "blocked" if blockers else "attention_needed"
        score = 0.2 if blockers else 0.6
        summary = f"Draft blocked: {blockers[0]['message'] if blockers else 'evidence incomplete'}"
    else:
        status = "completed"
        score = 1.0
        summary = f"Ready for AfC submission ({draft_audit.eligible_source_count} eligible sources, {draft_audit.independent_source_count} independent sources)."

    return StageAuditItem(
        stage_id="draft",
        label="Draft & AfC Compliance",
        status=status,
        score=round(score, 2),
        summary=summary,
        metrics={
            "ready": ready,
            "blockers_count": len(blockers),
            "warnings_count": len(warnings),
            "eligible_source_count": draft_audit.eligible_source_count,
            "independent_source_count": draft_audit.independent_source_count,
            "has_en_draft": has_en_draft,
            "has_hi_draft": has_hi_draft,
            "blockers": blockers,
            "warnings": warnings,
        },
        recommendations=recommendations,
    )


def audit_full_lifecycle(profile: PersonProfile) -> FullLifecycleAudit:
    """Run full lifecycle audit across all four stages."""
    s1 = audit_discovery_stage(profile)
    s2 = audit_provenance_stage(profile)
    s3 = audit_claims_stage(profile)
    s4 = audit_draft_stage(profile)

    stages = [s1, s2, s3, s4]
    avg_score = sum(s.score for s in stages) / len(stages)

    # Determine current lifecycle stage
    if s1.status != "completed" and s1.score < 0.6:
        current_stage = "discovery"
    elif s2.status != "completed":
        current_stage = "provenance"
    elif s3.status != "completed":
        current_stage = "claims"
    else:
        current_stage = "draft"

    # Overall health
    has_blockers = any(s.status == "blocked" for s in stages)
    has_attention = any(s.status == "attention_needed" for s in stages)
    if has_blockers:
        overall_health = "blocked"
    elif has_attention:
        overall_health = "needs_attention"
    else:
        overall_health = "healthy"

    # Determine next best action
    if s1.metrics.get("dead_unarchived", 0) > 0:
        next_action = f"Archive or replace {s1.metrics['dead_unarchived']} dead source(s)."
    elif s2.metrics.get("unverified_count", 0) > 0 and s2.metrics.get("verified_count", 0) == 0:
        next_action = f"Verify {s2.metrics['unverified_count']} active source(s) to unlock claims."
    elif s2.metrics.get("independent_origins_count", 0) < 2:
        next_action = "Discover and verify independent secondary news coverage to satisfy WP:GNG."
    elif s3.metrics.get("unverified_claims", 0) > 0:
        next_action = f"Review {s3.metrics['unverified_claims']} pending claim(s)."
    elif s3.metrics.get("draft_approved_claims", 0) == 0:
        next_action = "Select key claims for the Wikipedia draft."
    elif s4.metrics.get("ready", False) and not s4.metrics.get("has_en_draft", False):
        next_action = "Generate deterministic AfC draft wikitext."
    elif s4.metrics.get("has_en_draft", False):
        next_action = "Draft generated. Review wikitext and submit to Wikipedia AfC."
    else:
        next_action = "Continue research."

    mobile_online = is_mobile_bridge_available()

    return FullLifecycleAudit(
        current_stage=current_stage,
        overall_health=overall_health,
        completion_rate=round(avg_score, 2),
        stages=stages,
        next_action=next_action,
        mobile_bridge_online=mobile_online,
    )
