from unittest.mock import patch, MagicMock
import fitz

from engine.models import PersonProfile
from engine.openalex import search_author, get_author_works, convert_works_to_sources
from engine.osint_dorks import generate_osint_dorks
from engine.doc_metadata import parse_pdf_date, extract_pdf_metadata
from engine.fetcher import get_wayback_url


def test_openalex_search_and_ranking():
    mock_payload = {
        "results": [
            {
                "id": "https://openalex.org/A1",
                "display_name": "Prem Singh Yadav",
                "last_known_institutions": [{"display_name": "University of Delhi"}],
                "works_count": 5,
                "summary_stats": {"h_index": 3},
            },
            {
                "id": "https://openalex.org/A2",
                "display_name": "Prem Singh Yadav",
                "last_known_institutions": [
                    {"display_name": "Central Institute for Research on Buffaloes"}
                ],
                "works_count": 29,
                "summary_stats": {"h_index": 10},
            },
        ]
    }
    with patch("engine.openalex.requests.get") as mock_get:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = mock_payload
        mock_get.return_value = resp

        authors = search_author(
            "Prem Singh Yadav", "Central Institute for Research on Buffaloes"
        )
        assert len(authors) == 2
        # CIRB author should rank first due to institution hint match
        assert authors[0]["id"] == "A2"
        assert authors[0]["h_index"] == 10
        assert (
            "Central Institute for Research on Buffaloes" in authors[0]["affiliations"]
        )


def test_openalex_get_works_and_convert_sources():
    mock_works_payload = {
        "results": [
            {
                "id": "W123",
                "doi": "https://doi.org/10.1038/s41598-019-47909-8",
                "title": "Successful cloning of a superior buffalo bull",
                "publication_year": 2019,
                "primary_location": {
                    "source": {"display_name": "Scientific Reports"},
                    "landing_page_url": "https://www.nature.com/articles/s41598-019-47909-8",
                },
                "authorships": [
                    {"author": {"display_name": "Prem Singh Yadav"}},
                    {"author": {"display_name": "D. Kumar"}},
                ],
                "grants": [{"funder_display_name": "ICAR", "award_id": "NASF-01"}],
                "cited_by_count": 42,
            }
        ]
    }
    with patch("engine.openalex.requests.get") as mock_get:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = mock_works_payload
        mock_get.return_value = resp

        works = get_author_works("A2", limit=10)
        assert len(works) == 1
        assert works[0]["doi"] == "https://doi.org/10.1038/s41598-019-47909-8"
        assert "D. Kumar" in works[0]["coauthors"]

        sources = convert_works_to_sources(works, "Prem Singh Yadav")
        assert len(sources) == 1
        assert sources[0].title == "Successful cloning of a superior buffalo bull"
        assert sources[0].publisher == "Scientific Reports"
        assert sources[0].coverage_depth == "passing_mention"
        assert sources[0].workflow_stage == "retrieved"


def test_generate_osint_dorks():
    profile = PersonProfile(
        name="Prem Singh Yadav",
        affiliation="ICAR-Central Institute for Research on Buffaloes, Hisar",
    )
    dorks = generate_osint_dorks(profile)
    assert len(dorks) >= 8

    categories = {d.category for d in dorks}
    assert "academic_theses" in categories
    assert "grants_funding" in categories
    assert "gazettes_statutory" in categories
    assert "civic_legal" in categories
    assert "news_investigative" in categories

    # Verify that Google & DuckDuckGo URLs are properly formatted
    for d in dorks:
        assert d.google_url.startswith("https://www.google.com/search?q=")
        assert d.duckduckgo_url.startswith("https://duckduckgo.com/?q=")
        assert "Prem Singh Yadav" in d.query or "प्रेम सिंह" in d.query


def test_pdf_metadata_extraction():
    # Create a small valid PDF in-memory
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test Document Content")
    doc.set_metadata(
        {
            "title": "Cloning Research Report",
            "author": "Dr. Prem Singh Yadav",
            "creator": "Word Processor 2024",
            "creationDate": "D:20240315103000+05'30'",
        }
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    meta = extract_pdf_metadata(pdf_bytes)
    assert meta["title"] == "Cloning Research Report"
    assert meta["author"] == "Dr. Prem Singh Yadav"
    assert meta["creator_software"] == "Word Processor 2024"
    assert meta["page_count"] == 1
    assert meta["created_at"] == "2024-03-15T10:30:00+05:30"


def test_parse_pdf_date_variants():
    assert parse_pdf_date("D:20230706090631+05'30'") == "2023-07-06T09:06:31+05:30"
    assert parse_pdf_date("D:20210101120000Z") == "2021-01-01T12:00:00+00:00"
    assert parse_pdf_date(None) is None
    assert parse_pdf_date("invalid") is None


def test_multi_archive_fallback_to_archive_today():
    target_url = "https://example.com/lost-article"
    # When Wayback fails (returns None or exception), fallback to archive.ph
    with patch("engine.fetcher.requests.get") as mock_get:

        def side_effect(url, **kwargs):
            if "archive.org" in url:
                mock_wb = MagicMock()
                mock_wb.json.return_value = {"archived_snapshots": {}}
                return mock_wb
            elif "archive.ph" in url:
                mock_ph = MagicMock()
                mock_ph.status_code = 200
                mock_ph.text = '<html><a href="https://archive.ph/20240101/https://example.com/lost-article">link</a></html>'
                return mock_ph
            return MagicMock(status_code=404)

        mock_get.side_effect = side_effect
        archive_res = get_wayback_url(target_url)
        assert (
            archive_res
            == "https://archive.ph/20240101/https://example.com/lost-article"
        )
