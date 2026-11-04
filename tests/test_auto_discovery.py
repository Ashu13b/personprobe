"""Tests for comprehensive auto-discovery at research/start.

Verifies:
1. Orchestrates OpenAlex works, active researcher-ID search, crawl, and mobile-bridge fallback.
2. Canonical URL deduplication across all sources.
3. Graceful degradation when Google CSE is unconfigured or returns nothing.
4. Hard Rule 1: Adds SOURCES ONLY (never creates claims or auto-approves claims).
"""

from __future__ import annotations

from unittest.mock import MagicMock
from engine.models import PersonProfile, Source, SourceReliability
from backend.routes_research import _populate_initial_sources, ResearchRequest
import backend.routes_research as rr
import engine.researcher as res_mod
import engine.openalex as oa
import engine.researcher_ids as r_ids
import engine.crawler as cr
import engine.mobile_bridge as mb


def test_auto_discovery_chains_openalex_ids_crawl_and_dedups(monkeypatch):
    """Assert research/start chains OpenAlex works + active ID search + crawl and dedups via canonical_url."""
    # 1. Mock fetch_auto_sources with 2 sources (one of which has a duplicate variant)
    base_source_1 = Source(
        url="https://doi.org/10.1016/j.lep.2020.01",
        title="Base Paper 1",
        publisher="Elsevier",
        reliability=SourceReliability.reliable_secondary,
    )
    base_source_2 = Source(
        url="https://example.org/profile/katoch?utm_source=twitter",
        title="Profile Mention",
        publisher="Example Org",
        reliability=SourceReliability.primary,
    )
    monkeypatch.setattr(
        rr,
        "fetch_auto_sources",
        lambda name, field, affil: ([base_source_1, base_source_2], None),
    )

    # 2. Mock active ID search returning an ORCID
    monkeypatch.setattr(
        r_ids,
        "search_researcher_ids",
        lambda name, field, affil: {
            "orcid": "0000-0002-7892-2764",
            "google_scholar": "GS12345",
        },
    )
    monkeypatch.setattr(
        r_ids,
        "validated_new_ids",
        lambda new_ids, name, affil: new_ids,
    )

    # 3. Mock OpenAlex author resolution and works (including a duplicate DOI variant of base_source_1)
    monkeypatch.setattr(
        oa,
        "search_author",
        lambda name, affil: [
            {
                "id": "A5019627093",
                "display_name": "Vishwa Mohan Katoch",
                "orcid": "https://orcid.org/0000-0002-7892-2764",
            }
        ],
    )
    monkeypatch.setattr(
        oa,
        "get_author_works",
        lambda author_id, limit: [
            {
                "id": "W1",
                "doi": "http://dx.doi.org/10.1016/j.lep.2020.01/",  # duplicate of base_source_1
                "title": "Base Paper 1 duplicate URL",
                "publisher": "Elsevier",
                "year": 2020,
            },
            {
                "id": "W2",
                "doi": "https://doi.org/10.1016/j.lep.2021.99",
                "title": "Distinct OpenAlex Work",
                "publisher": "Elsevier",
                "year": 2021,
            },
        ],
    )

    # 4. Mock link extractor & crawler
    monkeypatch.setattr(
        rr,
        "fetch_institution_sources",
        lambda name, affil: [
            Source(
                url="https://institution.edu/faculty/katoch",
                title="Faculty Page",
                publisher="institution.edu",
                reliability=SourceReliability.primary,
            )
        ],
    )

    crawl_node = Source(
        url="https://institution.edu/faculty/katoch/publications",
        title="Faculty Publications",
        publisher="institution.edu",
        reliability=SourceReliability.primary,
    )
    mock_graph = MagicMock()
    mock_graph.to_sources.return_value = [crawl_node]
    mock_graph.relevance_hits = {crawl_node.url: 3}
    monkeypatch.setattr(cr, "crawl", lambda **kwargs: mock_graph)

    monkeypatch.setattr(
        rr,
        "_enrich_and_flag_sources",
        lambda sources, *a, **k: sources,
    )
    monkeypatch.setattr(
        "backend.store._check_doi_sources",
        lambda *a, **k: None,
    )

    # 5. Execute _populate_initial_sources
    profile = PersonProfile(name="Vishwa Mohan Katoch")
    req = ResearchRequest(
        name="Vishwa Mohan Katoch",
        field="Microbiology",
        affiliation="National JALMA Institute for Leprosy",
    )
    _populate_initial_sources(profile, req)

    # Verifications:
    # A. Active researcher IDs populated
    assert profile.researcher_ids.get("openalex") == "A5019627093"
    assert profile.researcher_ids.get("orcid") == "0000-0002-7892-2764"
    assert profile.researcher_ids.get("google_scholar") == "GS12345"

    # B. Discovery legs tracked
    assert profile.discovery_legs.get("web_search") in (
        "none",
        "duckduckgo",
        "google_cse",
        "mobile_bridge",
        "failed_all",
    )
    assert profile.discovery_legs.get("active_id_search") == "ok"
    assert profile.discovery_legs.get("openalex") == "imported_2"
    assert profile.discovery_legs.get("institution_crawl") == "deferred"
    assert profile.discovery_legs.get("profile_crawl") == "deferred"

    # C. Sources merged and deduplicated via canonical_url:
    # base_source_1 (doi:10.1016/j.lep.2020.01) and W1 (dx.doi.org/10.1016/j.lep.2020.01/) should dedup to 1
    urls = [s.url for s in profile.sources]
    doi_sources = [u for u in urls if "10.1016/j.lep.2020.01" in u]
    assert len(doi_sources) == 1, (
        f"Expected 1 canonical DOI source, found: {doi_sources}"
    )

    # D. OpenAlex distinct work present and crawl deferred
    assert any("Distinct OpenAlex Work" in s.title for s in profile.sources)

    # E. HARD RULE 1: Sources ONLY. Zero claims created or approved.
    assert len(profile.claims) == 0, (
        "No claims should be created by research_start discovery!"
    )
    for s in profile.sources:
        assert s.human_verified is False
        assert s.identity_status != "confirmed" or s.fetched_by != "openalex"


def test_graceful_degradation_without_cse(monkeypatch):
    """Verify that when Google CSE is not configured and web search is degraded,
    API-based sources (OpenAlex, Semantic Scholar) and mobile bridge still yield sources.
    """
    # Ensure CSE keys are unset
    monkeypatch.delenv("GOOGLE_CSE_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_CX", raising=False)

    # Mock fetch_auto_sources, researcher_ids, and institution sources to prevent slow live network calls
    monkeypatch.setattr(rr, "fetch_auto_sources", lambda name, field, affil: ([], None))
    monkeypatch.setattr(rr, "fetch_institution_sources", lambda name, affil: [])
    monkeypatch.setattr(r_ids, "search_researcher_ids", lambda name, field, affil: {})

    # Mock OpenAlex working via API
    monkeypatch.setattr(
        oa,
        "search_author",
        lambda name, affil: [{"id": "A999", "display_name": name, "orcid": None}],
    )
    monkeypatch.setattr(
        oa,
        "get_author_works",
        lambda author_id, limit: [
            {
                "id": "W999",
                "doi": "https://doi.org/10.999/paper",
                "title": "Paper 999",
                "publisher": "Nature",
            }
        ],
    )
    monkeypatch.setattr(
        rr,
        "_enrich_and_flag_sources",
        lambda sources, *a, **k: sources,
    )
    monkeypatch.setattr(
        "backend.store._check_doi_sources",
        lambda *a, **k: None,
    )

    profile = PersonProfile(name="Test Researcher")
    req = ResearchRequest(name="Test Researcher", field="Physics")
    _populate_initial_sources(profile, req)

    # API-based source should still be yielded
    assert len(profile.sources) >= 1
    assert any("Paper 999" in s.title for s in profile.sources)
    assert len(profile.claims) == 0


def test_mobile_bridge_search_fallback(monkeypatch):
    """Verify that _search_web calls mobile bridge search when CSE and DDGS fail."""
    monkeypatch.delenv("GOOGLE_CSE_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_CX", raising=False)

    # Mock DDGS failure
    import ddgs

    monkeypatch.setattr(ddgs, "DDGS", MagicMock(side_effect=Exception("DDGS blocked")))

    # Mock mobile bridge available and returning search results
    monkeypatch.setattr(mb, "is_mobile_bridge_available", lambda: True)
    monkeypatch.setattr(
        mb,
        "search_via_mobile_bridge",
        lambda q, max_results: [
            {
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345/",
                "title": "PubMed Leprosy Study",
                "snippet": "Study on M. leprae",
            }
        ],
    )

    results = res_mod._search_web("Vishwa Mohan Katoch")
    assert len(results) == 1
    assert results[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    assert results[0].fetched_by == "mobile_bridge_search"


def test_openalex_namesake_guard_rejects_decoy():
    """Verify select_best_author rejects namesake decoys and prioritizes matching author or ORCID."""
    from engine.openalex import select_best_author

    authors = [
        {
            "id": "A_DECOY",
            "display_name": "Kiran Katoch",
            "relevance_score": 100.0,
            "works_count": 500,
        },
        {
            "id": "A_REAL",
            "display_name": "Vishwa Mohan Katoch",
            "relevance_score": 10.0,
            "works_count": 150,
            "affiliations": ["National JALMA Institute for Leprosy"],
        },
    ]

    # Must select A_REAL despite lower base relevance score because A_DECOY has different given name
    best = select_best_author(
        authors, "Dr. Vishwa Mohan Katoch", affiliation_hint="National JALMA Institute"
    )
    assert best is not None
    assert best["id"] == "A_REAL"

    # With distinct ORCID hint, matches ORCID
    orcid_authors = [
        {"id": "A_OTHER", "display_name": "Vishwa Katoch", "relevance_score": 200.0},
        {
            "id": "A_ORCID",
            "display_name": "V. M. Katoch",
            "orcid": "https://orcid.org/0000-0002-7892-2764",
        },
    ]
    best_orcid = select_best_author(
        orcid_authors, "Vishwa Mohan Katoch", orcid_hint="0000-0002-7892-2764"
    )
    assert best_orcid is not None
    assert best_orcid["id"] == "A_ORCID"


def test_researcher_id_namesake_guard_rejects_decoy():
    """Verify validated_new_ids rejects namesake collision decoys like 'Kiran-Katoch-2'."""
    from engine.researcher_ids import validated_new_ids

    # Conflicting given name for same surname must be dropped
    candidate_ids = {
        "researchgate": "Kiran-Katoch-2",
        "google_scholar": "VM_Katoch_Agra",
    }
    validated = validated_new_ids(candidate_ids, "Dr. Vishwa Mohan Katoch")
    assert "researchgate" not in validated, (
        "Namesake decoy Kiran Katoch must be rejected!"
    )
    assert validated.get("google_scholar") == "VM_Katoch_Agra"


def test_research_start_defers_crawl_and_fetch(monkeypatch):
    """Verify research/start discovery defers heavy recursive crawl off synchronous path."""
    import engine.crawler as crawler_mod

    # Track if crawler or heavy fetcher are called during start
    crawl_called = False

    def fail_crawl(*args, **kwargs):
        nonlocal crawl_called
        crawl_called = True
        raise AssertionError(
            "crawl should not be called synchronously during research_start!"
        )

    monkeypatch.setattr(crawler_mod, "crawl", fail_crawl)

    # Mock auto sources & IDs to keep unit test isolated
    monkeypatch.setattr(rr, "fetch_auto_sources", lambda name, field, affil: ([], None))
    monkeypatch.setattr(r_ids, "search_researcher_ids", lambda name, field, affil: {})
    monkeypatch.setattr(oa, "search_author", lambda name, affil: [])

    profile = PersonProfile(name="Test Fast Start")
    req = ResearchRequest(name="Test Fast Start", field="Physics")
    _populate_initial_sources(profile, req)

    assert crawl_called is False, "Inline crawl must be deferred off synchronous path!"
    assert profile.discovery_legs.get("profile_crawl") == "deferred"
    assert profile.discovery_legs.get("institution_crawl") == "deferred"
