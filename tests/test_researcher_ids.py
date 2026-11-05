import pytest
from fastapi import HTTPException

from backend import main as backend_main
from backend import store
from engine import researcher_ids
from engine.models import PersonProfile, Source, SourceReliability


def _profile() -> PersonProfile:
    return PersonProfile(
        name="Prem Singh Yadav",
        affiliation="ICAR-Central Institute for Research on Buffaloes",
    )


def test_find_ids_removes_an_orcid_that_fails_identity_validation(monkeypatch):
    profile = _profile()
    profile.researcher_ids["orcid"] = "0000-0003-0982-9408"
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(store, "_save_session", lambda _name: None)
    monkeypatch.setattr(researcher_ids, "search_researcher_ids", lambda *_args: {})
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_args: False)

    result = backend_main.find_researcher_ids_endpoint(
        backend_main.FindIdsRequest(profile_name=profile.name)
    )

    assert "orcid" not in result["researcher_ids"]
    assert result["confirmed_ids"]["orcid"] is False


def test_refresh_rejects_an_unvalidated_orcid(monkeypatch):
    profile = _profile()
    monkeypatch.setattr(store, "_sessions", {profile.name: profile})
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_args: False)

    with pytest.raises(HTTPException) as exc:
        backend_main.refresh_papers_endpoint(
            backend_main.RefreshPapersRequest(
                profile_name=profile.name,
                id_type="orcid",
                id_value="0000-0003-0982-9408",
                confirm=True,
            )
        )

    assert exc.value.status_code == 400
    assert profile.researcher_ids == {}


def test_validated_new_ids_drops_wrong_person_orcid(monkeypatch):
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: False)

    out = researcher_ids.validated_new_ids(
        {"orcid": "0000-0003-0982-9408", "google_scholar": "namesake123"},
        "Prem Singh Yadav",
    )

    assert "orcid" not in out
    assert out["google_scholar"] == "namesake123"


def test_validated_new_ids_keeps_verified_orcid(monkeypatch):
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: True)

    out = researcher_ids.validated_new_ids(
        {"orcid": "0000-0002-1825-0097"}, "Prem Singh Yadav"
    )

    assert out == {"orcid": "0000-0002-1825-0097"}


def test_research_start_drops_orcid_from_source_url_when_validation_fails(
    monkeypatch, tmp_path
):
    orcid_source = Source(
        url="https://orcid.org/0000-0003-0982-9408",
        title="ORCID profile of someone else",
        publisher="ORCID",
        reliability=SourceReliability.primary,
        fetched_by="google_search",
    )
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(
        "backend.routes_research.fetch_auto_sources",
        lambda *a, **k: ([orcid_source], None),
    )
    monkeypatch.setattr(
        "engine.researcher_ids.search_researcher_ids",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "engine.openalex.search_author",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "backend.routes_research._enrich_and_flag_sources",
        lambda sources, *a: sources,
    )

    class _Clear:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr(
        "backend.routes_research.check_existing_page", lambda _t: _Clear()
    )
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: False)

    result = backend_main.research_start(
        backend_main.ResearchRequest(name="Fresh Person")
    )

    assert result["resumed"] is False
    assert "orcid" not in result["profile"]["researcher_ids"]


def test_research_start_keeps_orcid_when_validation_passes(monkeypatch, tmp_path):
    orcid_source = Source(
        url="https://orcid.org/0000-0002-1825-0097",
        title="ORCID profile",
        publisher="ORCID",
        reliability=SourceReliability.primary,
        fetched_by="google_search",
    )
    monkeypatch.setattr(store, "_sessions", {})
    monkeypatch.setattr(store, "_wiki_statuses", {})
    monkeypatch.setattr(store, "SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(
        "backend.routes_research.fetch_auto_sources",
        lambda *a, **k: ([orcid_source], None),
    )
    monkeypatch.setattr(
        "engine.researcher_ids.search_researcher_ids",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "engine.openalex.search_author",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "backend.routes_research._enrich_and_flag_sources",
        lambda sources, *a: sources,
    )

    class _Clear:
        def model_dump(self):
            return {"status": "clear", "url": None, "note": None}

    monkeypatch.setattr(
        "backend.routes_research.check_existing_page", lambda _t: _Clear()
    )
    monkeypatch.setattr(researcher_ids, "validate_orcid", lambda *_a, **_k: True)

    result = backend_main.research_start(
        backend_main.ResearchRequest(name="Fresh Person 2")
    )

    assert result["profile"]["researcher_ids"]["orcid"] == "0000-0002-1825-0097"


def test_validate_s2_author_accepts_matching_profile(monkeypatch):
    class _Resp:
        status_code = 200

        def json(self):
            return {"name": "Vishwa Mohan Katoch"}

    monkeypatch.setattr(researcher_ids.requests, "get", lambda *a, **k: _Resp())

    assert researcher_ids.validate_s2_author("2147684", "Vishwa Mohan Katoch") is True


def test_validate_s2_author_rejects_namesake_and_missing(monkeypatch):
    class _Namesake:
        status_code = 200

        def json(self):
            return {"name": "Ramesh Katoch"}

    class _Missing:
        status_code = 404

        def json(self):
            return {}

    monkeypatch.setattr(researcher_ids.requests, "get", lambda *a, **k: _Namesake())
    assert researcher_ids.validate_s2_author("1", "Vishwa Mohan Katoch") is False
    monkeypatch.setattr(researcher_ids.requests, "get", lambda *a, **k: _Missing())
    assert researcher_ids.validate_s2_author("1", "Vishwa Mohan Katoch") is False


def test_validated_new_ids_drops_wrong_semantic_scholar_id(monkeypatch):
    monkeypatch.setattr(researcher_ids, "validate_s2_author", lambda *_a, **_k: False)

    out = researcher_ids.validated_new_ids(
        {"semantic_scholar": "2147684"}, "Vishwa Mohan Katoch"
    )

    assert out == {}


def test_validated_new_ids_researchgate_slug_positive_matching():
    # Prem-Yadav-7 for "Prem Singh Yadav" → ACCEPTED
    res1 = researcher_ids.validated_new_ids(
        {"researchgate": "Prem-Yadav-7"}, "Prem Singh Yadav"
    )
    assert res1 == {"researchgate": "Prem-Yadav-7"}

    # Shivani-Bhardwaj-17 for "Prem Singh Yadav" → REJECTED (surname mismatch)
    res2 = researcher_ids.validated_new_ids(
        {"researchgate": "Shivani-Bhardwaj-17"}, "Prem Singh Yadav"
    )
    assert res2 == {}

    # Kiran-Yadav-2 for "Prem Singh Yadav" → REJECTED (surname match, conflicting given name)
    res3 = researcher_ids.validated_new_ids(
        {"researchgate": "Kiran-Yadav-2"}, "Prem Singh Yadav"
    )
    assert res3 == {}

    # Kiran-Katoch-2 for "Dr. Vishwa Mohan Katoch" → REJECTED
    res4 = researcher_ids.validated_new_ids(
        {"researchgate": "Kiran-Katoch-2"}, "Dr. Vishwa Mohan Katoch"
    )
    assert res4 == {}

    # Vishwa-Katoch for "Dr. Vishwa Mohan Katoch" → ACCEPTED
    res5 = researcher_ids.validated_new_ids(
        {"researchgate": "Vishwa-Katoch"}, "Dr. Vishwa Mohan Katoch"
    )
    assert res5 == {"researchgate": "Vishwa-Katoch"}


def test_validated_new_ids_preserves_opaque_scholar_and_scopus():
    # a real-format Scholar user= id (e.g. AbC12dEAAAAJ) → NOT rejected by the slug string rule
    res_scholar = researcher_ids.validated_new_ids(
        {"google_scholar": "AbC12dEAAAAJ"}, "Prem Singh Yadav"
    )
    assert res_scholar == {"google_scholar": "AbC12dEAAAAJ"}

    # Scopus 57225411188 → ACCEPTED (not rejected by string rule)
    res_scopus = researcher_ids.validated_new_ids(
        {"scopus": "57225411188"}, "Prem Singh Yadav"
    )
    assert res_scopus == {"scopus": "57225411188"}


def test_search_researcher_ids_name_matching_filters_wrong_people(monkeypatch):
    def mock_search_web(query):
        if "site:researchgate.net" in query:
            return [
                Source(
                    url="https://www.researchgate.net/profile/Shivani-Bhardwaj-17",
                    title="Shivani Bhardwaj | CIRB",
                    publisher="researchgate.net",
                    reliability=SourceReliability.primary,
                ),
                Source(
                    url="https://www.researchgate.net/profile/Prem-Yadav-7",
                    title="Prem Singh Yadav | CIRB",
                    publisher="researchgate.net",
                    reliability=SourceReliability.primary,
                ),
            ]
        if "site:scholar.google.com" in query:
            return [
                Source(
                    url="https://scholar.google.com/citations?user=WrongPerson123",
                    title="Shivani Bhardwaj - Google Scholar",
                    publisher="scholar.google.com",
                    reliability=SourceReliability.primary,
                ),
                Source(
                    url="https://scholar.google.com/citations?user=AbC12dEAAAAJ",
                    title="Prem Singh Yadav - Google Scholar",
                    publisher="scholar.google.com",
                    reliability=SourceReliability.primary,
                ),
            ]
        if "site:orcid.org" in query:
            return [
                Source(
                    url="https://orcid.org/0000-0003-3930-2201",
                    title="Pradeep Kumar (0000-0003-3930-2201) - ORCID",
                    publisher="orcid.org",
                    reliability=SourceReliability.primary,
                ),
                Source(
                    url="https://orcid.org/0000-0002-1825-0097",
                    title="Prem Singh Yadav (0000-0002-1825-0097) - ORCID",
                    publisher="orcid.org",
                    reliability=SourceReliability.primary,
                ),
            ]
        return []

    monkeypatch.setattr("engine.researcher._search_web", mock_search_web)

    found = researcher_ids.search_researcher_ids(
        name="Prem Singh Yadav", affiliation="CIRB", quick_mode=False
    )
    assert found.get("researchgate") == "Prem-Yadav-7"
    assert found.get("google_scholar") == "AbC12dEAAAAJ"
    assert found.get("orcid") == "0000-0002-1825-0097"

