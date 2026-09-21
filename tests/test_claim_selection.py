"""Claim clustering + best-source ranking for draft selection."""
from engine.claim_selection import build_claim_clusters, rank_sources_for_fact, source_citation_rank
from engine.models import Claim, PersonProfile, Source, SourceReliability


def _src(url, cat="independent_secondary", depth="unassessed", verified=False, alive=True, trust="high"):
    return Source(
        url=url, title=f"t {url}", publisher="pub",
        reliability=SourceReliability.reliable_secondary if cat == "independent_secondary" else SourceReliability.primary,
        provenance_category=cat, coverage_depth=depth, human_verified=verified,
        liveness="alive" if alive else "dead", domain_trust=trust,
    )


def test_citation_rank_prefers_independent_significant_verified():
    press = _src("https://p.test/a", "independent_secondary", "significant", verified=True)
    inst = _src("https://cirb.test/ar", "institutional_bio")
    authored = _src("https://doi.test/x", "authored_publication")
    cv = _src("file:///cv.pdf", "cv_blueprint")
    assert source_citation_rank(press) > source_citation_rank(inst) > source_citation_rank(authored) > source_citation_rank(cv)


def test_rank_sources_for_fact_orders_and_flags_context():
    by_url = {
        "https://p.test/a": _src("https://p.test/a", "independent_secondary", "significant"),
        "https://cirb.test/ar": _src("https://cirb.test/ar", "institutional_bio"),
    }
    ranked = rank_sources_for_fact(["https://cirb.test/ar", "https://gone.test/x", "https://p.test/a"], by_url)
    assert ranked[0]["url"] == "https://p.test/a"
    assert ranked[-1]["url"] == "https://gone.test/x"
    assert ranked[-1]["rank"] == -99.0


def test_build_claim_clusters_groups_same_fact_across_links():
    profile = PersonProfile(name="Prem Singh Yadav", sources=[
        _src("https://p.test/a", "independent_secondary", "significant", verified=True),
        _src("https://mirror.test/b", "independent_secondary"),
        _src("https://cirb.test/ar", "institutional_bio"),
    ], claims=[
        Claim(text="Hisar Gaurav, the first cloned calf born at ICAR-CIRB in Hisar, turned seven in December 2022.",
              field="research", source_url="https://p.test/a"),
        Claim(text="Hisar Gaurav, the first cloned calf born at ICAR-CIRB Hisar, turned seven on Sunday.",
              field="research", source_url="https://mirror.test/b"),
        Claim(text="Yadav retired from ICAR-CIRB as a principal scientist in 2025.",
              field="careers", source_url="https://cirb.test/ar"),
    ])
    clusters = build_claim_clusters(profile)
    multi = [c for c in clusters if c["link_count"] > 1]
    assert len(multi) == 1
    c = multi[0]
    assert set(c["claim_indices"]) == {0, 1}
    assert c["best_source_url"] == "https://p.test/a"
    assert c["canonical_index"] in (0, 1)
    singles = [c for c in clusters if c["link_count"] <= 1]
    assert len(singles) == 1 and singles[0]["field"] == "careers"


def test_suggest_draft_upgrades_collapses_dupes_and_classifies():
    from engine.claim_selection import suggest_draft_upgrades
    from engine.models import VerificationState

    press = _src("https://press.test/a", "independent_secondary", "significant", verified=True)
    suspect = _src("https://mirror.test/b", "independent_secondary")
    suspect.identity_status = "suspect"
    cv = _src("file:///cv.pdf", "cv_blueprint")

    profile = PersonProfile(name="Prem Singh Yadav", sources=[press, suspect, cv], claims=[
        Claim(text="Hisar Gaurav, the first cloned calf born at ICAR-CIRB Hisar, turned seven.",
              field="research", source_url="https://press.test/a", verification=VerificationState.confirmed),
        Claim(text="Hisar Gaurav, the first cloned calf born at ICAR-CIRB Hisar, turned seven on Sunday.",
              field="research", source_url="https://mirror.test/b"),
        Claim(text="Born on April 10, 1963 in village Nimoth, Rewari.",
              field="birth_date", source_url="file:///cv.pdf"),
    ])
    res = suggest_draft_upgrades(profile)
    # the two Hisar Gaurav claims are one fact -> exactly one suggestion for it
    facts = [s for s in res["suggestions"] if "Hisar Gaurav" in s["text"]]
    assert len(facts) == 1
    assert facts[0]["status"] in ("ready", "needs_confirmation")
    assert facts[0]["link_count"] == 2
    # the CV-sourced fact is blocked
    birth = [s for s in res["suggestions"] if s["field"] == "birth_date"][0]
    assert birth["status"] == "blocked"
    assert any("CV" in b for b in birth["blockers"])
