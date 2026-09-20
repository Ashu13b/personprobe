"""Tests for the Discarded Sources Registry and Canonical Deduplication."""
from engine.models import PersonProfile, Source
from engine.discarded_registry import (
    record_discarded,
    is_discarded,
    is_known_or_discarded,
    get_known_and_discarded_canonical_urls,
    recover_discarded,
    get_discarded_by_reason,
)


def test_record_discarded_canonical_dedup():
    profile = PersonProfile(name="Test Subject")
    url1 = "https://www.example.com/article?utm_source=twitter"
    url2 = "http://example.com/article/"

    d1 = record_discarded(profile, url1, reason="no_name_match", title="Article 1")
    assert len(profile.discarded_sources) == 1
    assert d1.canonical_url == "https://example.com/article"

    # Exact duplicate under canonical normalization should not duplicate entry
    d2 = record_discarded(profile, url2, reason="no_name_match", title="Article 2")
    assert len(profile.discarded_sources) == 1
    assert d2.canonical_url == "https://example.com/article"


def test_is_known_or_discarded():
    profile = PersonProfile(
        name="Test Subject",
        sources=[Source(url="https://example.com/live-source", title="Live", publisher="Test")],
    )
    record_discarded(profile, "https://example.com/discarded-link?utm_source=google", reason="homonym_risk")

    assert is_known_or_discarded(profile, "https://example.com/live-source") is True
    assert is_known_or_discarded(profile, "https://www.example.com/live-source/") is True
    assert is_known_or_discarded(profile, "http://example.com/discarded-link") is True
    assert is_known_or_discarded(profile, "https://example.com/unknown-fresh-link") is False


def test_get_known_and_discarded_canonical_urls():
    profile = PersonProfile(
        name="Test Subject",
        sources=[Source(url="https://example.com/source1", title="S1", publisher="P1")],
        skipped_sources=["https://example.com/skipped1"],
        rejected_sources=["https://example.com/rejected1"],
    )
    record_discarded(profile, "https://example.com/discarded1", reason="no_name_match")

    urls = get_known_and_discarded_canonical_urls(profile)
    assert "https://example.com/source1" in urls
    assert "https://example.com/skipped1" in urls
    assert "https://example.com/rejected1" in urls
    assert "https://example.com/discarded1" in urls


def test_recover_discarded():
    profile = PersonProfile(name="Test Subject")
    url = "https://example.com/potential-match"
    record_discarded(profile, url, reason="no_name_match", title="Potential Match")

    assert is_discarded(profile, url) is True
    assert len(profile.discarded_sources) == 1

    recovered = recover_discarded(profile, url)
    assert recovered is not None
    assert recovered.canonical_url == "https://example.com/potential-match"
    assert len(profile.discarded_sources) == 0
    assert is_discarded(profile, url) is False


def test_get_discarded_by_reason():
    profile = PersonProfile(name="Test Subject")
    record_discarded(profile, "https://example.com/1", reason="no_name_match")
    record_discarded(profile, "https://example.com/2", reason="homonym_risk")
    record_discarded(profile, "https://example.com/3", reason="no_name_match")

    no_name = get_discarded_by_reason(profile, "no_name_match")
    assert len(no_name) == 2
    homonyms = get_discarded_by_reason(profile, "homonym_risk")
    assert len(homonyms) == 1
