"""Unit tests for Multi-Level Verification (L1-L5) & Dual-Client (Agent/Human) Logging."""
from engine.models import (
    Source,
    Claim,
    log_source_verification,
    log_claim_verification,
    PersonProfile,
)
from backend import store
from backend.routes_research import (
    verify_source_level,
    verify_claim,
    get_verification_summary,
)
from backend.schemas import (
    VerifyClaimRequest,
    VerifySourceLevelRequest,
)


def test_verification_log_entry_models():
    """Verify data model serialization and defaults."""
    source = Source(
        url="https://example.com/scientist-profile",
        title="Dr. Jane Doe Profile",
        publisher="Example University",
    )
    assert source.verification_trail == []
    assert source.liveness_by is None
    assert source.identity_status == "unverified"

    # Log L1 Liveness by Agent
    entry1 = log_source_verification(
        source,
        level="liveness",
        actor="agent",
        action="check_liveness",
        verdict="passed",
        summary="Reachable 200 OK via agent crawler",
    )
    assert len(source.verification_trail) == 1
    assert source.liveness_by == "agent"
    assert entry1.actor == "agent"
    assert entry1.level == "liveness"

    # Log L2 Identity by Human
    entry2 = log_source_verification(
        source,
        level="identity",
        actor="human",
        action="confirm_person",
        verdict="passed",
        summary="Confirmed person affiliation matches subject",
    )
    assert len(source.verification_trail) == 2
    assert source.identity_status == "confirmed"
    assert source.identity_by == "human"


def test_claim_verification_logging():
    """Verify claim settlement and draft approval logging with quotes."""
    claim = Claim(
        text="Served as Director of Institute from 2015 to 2020.",
        field="position",
        source_url="https://example.com/director-report",
    )
    assert claim.verification_trail == []
    assert claim.verified_by is None
    assert claim.settled_quote is None

    # L4: Settled by agent with verbatim quote
    log_claim_verification(
        claim,
        level="claim",
        actor="agent",
        action="settle_claim",
        verdict="passed",
        summary="Matched verbatim sentence in source document",
        details={"quote": "Jane Doe was appointed Director in 2015 and concluded her term in 2020."},
    )
    assert claim.verified_by == "agent"
    assert len(claim.verification_trail) == 1

    # L5: Approved for draft by human
    log_claim_verification(
        claim,
        level="draft",
        actor="human",
        action="approve_draft",
        verdict="passed",
        summary="Approved for AfC draft inclusion by human reviewer",
    )
    assert claim.draft_approved_by == "human"
    assert len(claim.verification_trail) == 2


def test_verify_source_level_endpoints(monkeypatch):
    """Test POST /research/source/verify-level and GET /research/verification-summary."""
    profile = PersonProfile(name="Test Subject")
    src = Source(
        url="https://example.org/news/bio",
        title="Major Breakthrough by Test Subject",
        publisher="Daily Tribune",
        is_independent=True,
        provenance_category="independent_secondary",
    )
    claim = Claim(
        text="Won National Science Award in 2021.",
        field="award",
        source_url="https://example.org/news/bio",
    )
    profile.sources.append(src)
    profile.claims.append(claim)
    store._sessions[profile.name] = profile

    # 1. Level 1 Verification via endpoint by Agent
    res1 = verify_source_level(
        VerifySourceLevelRequest(
            profile_name=profile.name,
            url=src.url,
            level="liveness",
            actor="agent",
            status="alive",
            note="HTTP 200 via headless fetch",
        )
    )
    assert res1["ok"] is True
    assert profile.sources[0].liveness == "alive"
    assert profile.sources[0].liveness_by == "agent"

    # 2. Level 2 Verification via endpoint by Human
    res2 = verify_source_level(
        VerifySourceLevelRequest(
            profile_name=profile.name,
            url=src.url,
            level="identity",
            actor="human",
            status="confirmed",
            note="Person confirmed by manual review",
        )
    )
    assert res2["ok"] is True
    assert profile.sources[0].identity_status == "confirmed"
    assert profile.sources[0].identity_by == "human"

    # 3. Level 4 Claim verification with settled quote by Human
    c_res = verify_claim(
        profile.name,
        VerifyClaimRequest(
            claim_index=0,
            action="confirm",
            actor="human",
            settled_quote="Test Subject received the National Science Award at the 2021 gala.",
        ),
    )
    assert c_res["claim"]["verification"] == "confirmed"
    assert c_res["claim"]["verified_by"] == "human"
    assert c_res["claim"]["settled_quote"] is not None

    # 4. Level 5 Draft approval by Human
    d_res = verify_claim(
        profile.name,
        VerifyClaimRequest(
            claim_index=0,
            action="approve_draft",
            actor="human",
        ),
    )
    assert d_res["claim"]["draft_approved"] is True
    assert d_res["claim"]["draft_approved_by"] == "human"

    # 5. Verification Summary breakdown
    summary = get_verification_summary(profile.name)
    assert summary["levels"]["l1_liveness"]["alive"] == 1
    assert summary["levels"]["l1_liveness"]["checked_by_agent"] == 1
    assert summary["levels"]["l2_identity"]["confirmed"] == 1
    assert summary["levels"]["l2_identity"]["verified_by_human"] == 1
    assert summary["levels"]["l4_claims"]["settled"] == 1
    assert summary["levels"]["l5_draft"]["total_approved"] == 1
    assert summary["audit_events"]["agent_actions"] >= 1
    assert summary["audit_events"]["human_actions"] >= 1
