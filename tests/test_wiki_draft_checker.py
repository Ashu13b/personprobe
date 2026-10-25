"""Tests for the Standalone Wiki Draft Checker engine and API endpoint."""

from wiki_draft_checker import WikiDraftChecker, check_wiki_draft


VALID_DRAFT = """{{Short description|Indian agricultural scientist}}
{{Infobox scientist
| name = Prem Singh Yadav
| birth_date = {{birth date and age|1963|4|10}}
}}

'''Prem Singh Yadav''' (born 10 April 1963) is an Indian animal physiologist and biotechnology scientist<ref name="src1">{{cite web|url=https://example.com/bio|title=Biographical Profile of Dr PS Yadav|website=example.com}}</ref>. He served as head of animal physiology and reproduction<ref name="src2">{{cite web|url=https://cirb.res.in/scientists|title=ICAR-CIRB Scientist Directory|website=cirb.res.in}}</ref>.

== Early life and education ==
Yadav was born in Haryana, India<ref name="src1" />. He completed his Bachelor of Science in 1985<ref name="src1" />.

== References ==
{{reflist}}

[[Category:1963 births]]
[[Category:Living people]]
"""


def test_valid_draft_passes():
    report = check_wiki_draft(VALID_DRAFT, check_live_links=False)
    assert report.verdict == "PASS"
    assert report.quality_score >= 90
    assert report.sentence_count > 0
    assert report.total_citations >= 3
    assert len(report.link_audits) == 2


def test_missing_structure_flags_errors():
    bad_draft = "Just some text without infobox, short description, or references."
    checker = WikiDraftChecker(check_live_links=False)
    report = checker.check(bad_draft)
    assert report.verdict == "FAIL"
    rule_ids = {f.rule_id for f in report.findings}
    assert "missing_short_description" in rule_ids
    assert "missing_infobox" in rule_ids
    assert "missing_reflist" in rule_ids


def test_bare_external_link_in_prose():
    draft = VALID_DRAFT.replace(
        "== Early life and education ==",
        "See more at [https://external-link.org/test].\n\n== Early life and education ==",
    )
    report = check_wiki_draft(draft, check_live_links=False)
    rule_ids = {f.rule_id for f in report.findings}
    assert "bare_external_link_in_prose" in rule_ids


def test_empty_ref_and_empty_url():
    draft = VALID_DRAFT.replace(
        "== Early life and education ==",
        "Some fact.<ref></ref>\nAnother fact.<ref>{{cite web|url=|title=Empty}}</ref>\n\n== Early life and education ==",
    )
    report = check_wiki_draft(draft, check_live_links=False)
    rule_ids = {f.rule_id for f in report.findings}
    assert "empty_ref_tag" in rule_ids or "empty_citation_url" in rule_ids
    assert report.counts_by_severity["CRITICAL"] > 0


def test_ungrounded_sentence_detected():
    draft = VALID_DRAFT.replace(
        "== Early life and education ==",
        "This is an assertive sentence containing substantial factual claims that lacks any citation footnote whatsoever.\n\n== Early life and education ==",
    )
    report = check_wiki_draft(draft, check_live_links=False)
    rule_ids = {f.rule_id for f in report.findings}
    assert "ungrounded_sentence" in rule_ids


def test_peacock_terms_npov():
    draft = (
        VALID_DRAFT
        + "\nHe was a visionary and legendary genius in animal biotechnology<ref name='src1' />."
    )
    report = check_wiki_draft(draft, check_live_links=False)
    rule_ids = {f.rule_id for f in report.findings}
    assert "peacock_term" in rule_ids


def test_blp_privacy_phone_and_address():
    draft = (
        VALID_DRAFT
        + "\nHe lives at House No. 1425, Sector 14, Hisar and can be reached at +91 9812345678<ref name='src1' />."
    )
    report = check_wiki_draft(draft, check_live_links=False)
    assert report.verdict == "FAIL"
    rule_ids = {f.rule_id for f in report.findings}
    assert "blp_privacy_violation" in rule_ids


def test_isbn_not_falsely_flagged_as_phone():
    draft = VALID_DRAFT + "\n{{cite book|title=Test Book|isbn=8189304801}}"
    report = check_wiki_draft(draft, check_live_links=False)
    blp_violations = [
        f for f in report.findings if f.rule_id == "blp_privacy_violation"
    ]
    assert len(blp_violations) == 0


def test_api_checker_endpoint():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/draft/checker", json={"wikitext": VALID_DRAFT, "check_live_links": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "PASS"
    assert data["quality_score"] >= 90
    assert "findings" in data
    assert "link_audits" in data
    assert "grounding" in data
