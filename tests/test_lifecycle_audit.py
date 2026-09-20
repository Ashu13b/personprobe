"""Tests for the Research Lifecycle Audit engine."""
from engine.models import PersonProfile, Source, Claim, VerificationState, SourceReliability, DiscardedSource
from engine.lifecycle_audit import (
    audit_discovery_stage,
    audit_provenance_stage,
    audit_claims_stage,
    audit_draft_stage,
    audit_full_lifecycle,
)


def test_audit_discovery_stage():
    profile = PersonProfile(
        name="Test Subject",
        sources=[
            Source(url="https://example.com/live1", title="S1", publisher="P1", liveness="alive"),
            Source(url="https://example.com/dead1", title="Dead", publisher="P2", liveness="dead", archive_url="https://archive.org/dead1"),
            Source(url="https://example.com/dead2", title="Dead No Arch", publisher="P3", liveness="dead", archive_url=None),
        ],
        discarded_sources=[
            DiscardedSource(url="https://example.com/disc1", canonical_url="https://example.com/disc1", reason="no_name_match"),
            DiscardedSource(url="https://example.com/disc2", canonical_url="https://example.com/disc2", reason="homonym_risk"),
        ],
    )

    stage = audit_discovery_stage(profile)
    assert stage.stage_id == "discovery"
    assert stage.status == "attention_needed"  # dead without archive triggers attention
    assert stage.metrics["total_active_sources"] == 3
    assert stage.metrics["total_discarded"] == 2
    assert stage.metrics["alive_count"] == 1
    assert stage.metrics["dead_archived"] == 1
    assert stage.metrics["dead_unarchived"] == 1
    assert stage.metrics["discarded_reasons"]["homonym_risk"] == 1
    assert any("dead with no Wayback archive" in r for r in stage.recommendations)


def test_audit_provenance_stage():
    profile = PersonProfile(
        name="Test Subject",
        sources=[
            Source(
                url="https://news1.com/story",
                title="Major discovery",
                publisher="News 1",
                reliability=SourceReliability.reliable_secondary,
                human_verified=True,
                coverage_depth="significant",
                is_independent=True,
            ),
            Source(
                url="https://news2.org/profile",
                title="Scientist overview",
                publisher="News 2",
                reliability=SourceReliability.reliable_secondary,
                human_verified=True,
                coverage_depth="significant",
                is_independent=True,
            ),
        ],
        missing_slots=["birth_date", "birth_place"],
    )

    stage = audit_provenance_stage(profile)
    assert stage.stage_id == "provenance"
    assert stage.status == "completed"
    assert stage.metrics["verified_count"] == 2
    assert stage.metrics["independent_origins_count"] == 2
    assert stage.metrics["significant_origins_count"] == 2
    assert stage.metrics["missing_slots_count"] == 2


def test_audit_claims_stage():
    profile = PersonProfile(
        name="Test Subject",
        claims=[
            Claim(field="field", text="Animal biotechnology", verification=VerificationState.confirmed, draft_approved=True),
            Claim(field="position", text="Principal Scientist", verification=VerificationState.confirmed, draft_approved=False),
            Claim(field="award", text="National Award", verification=VerificationState.unverified, draft_approved=False),
        ],
    )

    stage = audit_claims_stage(profile)
    assert stage.stage_id == "claims"
    assert stage.metrics["total_claims"] == 3
    assert stage.metrics["unverified_claims"] == 1
    assert stage.metrics["draft_approved_claims"] == 1
    assert stage.metrics["research_only_claims"] == 1
    assert any("pending verification" in r for r in stage.recommendations)


def test_audit_draft_stage_blocked_when_no_evidence():
    profile = PersonProfile(name="Empty Person")
    stage = audit_draft_stage(profile)
    assert stage.stage_id == "draft"
    assert stage.metrics["ready"] is False
    assert stage.metrics["blockers_count"] > 0


def test_audit_full_lifecycle():
    profile = PersonProfile(
        name="Test Subject",
        sources=[
            Source(
                url="https://thehindu.com/article",
                title="Pioneering buffalo research",
                publisher="The Hindu",
                reliability=SourceReliability.reliable_secondary,
                human_verified=True,
                coverage_depth="significant",
                is_independent=True,
                liveness="alive",
            ),
            Source(
                url="https://timesofindia.com/article",
                title="Cloning breakthrough",
                publisher="Times of India",
                reliability=SourceReliability.reliable_secondary,
                human_verified=True,
                coverage_depth="significant",
                is_independent=True,
                liveness="alive",
            ),
        ],
        claims=[
            Claim(field="field", text="Animal biotechnology", source_url="https://thehindu.com/article",
                  verification=VerificationState.confirmed, draft_approved=True),
            Claim(field="position", text="Principal Scientist at CIRB", source_url="https://timesofindia.com/article",
                  verification=VerificationState.confirmed, draft_approved=True),
        ],
    )

    full = audit_full_lifecycle(profile)
    assert full.overall_health in ("healthy", "needs_attention")
    assert len(full.stages) == 4
    assert full.stages[0].stage_id == "discovery"
    assert full.stages[1].stage_id == "provenance"
    assert full.stages[2].stage_id == "claims"
    assert full.stages[3].stage_id == "draft"
    assert full.completion_rate > 0.0
    assert full.next_action != ""
