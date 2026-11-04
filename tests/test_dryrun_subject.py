"""Tests for the generic dry-run subject harness and custom repository state gating."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from engine.models import PersonProfile
from engine.public_records_atlas import (
    PublicRecordRepository,
    register_public_repository,
    derive_subject_record_matrix,
)
from scripts.dryrun_subject import (
    check_differential_residue,
    run_dryrun,
    DEFAULT_BLOCKLIST,
)


def test_differential_residue_clean():
    """Clean generated text with no blocklist tokens must pass."""
    gen_text = "Dr. Katoch studied leprosy and mycobacterial immunology at JALMA Agra and AIIMS New Delhi."
    sub_text = "Vishwa Mohan Katoch Agra Uttar Pradesh Leprosy"
    passed, violations = check_differential_residue(
        gen_text, sub_text, DEFAULT_BLOCKLIST
    )
    assert passed is True
    assert violations == []


def test_differential_residue_planted_violation():
    """Planted blocklist term not in subject context must be flagged as violation."""
    gen_text = "Examined doctoral thesis repository at CIRB Hisar campus."
    sub_text = "Vishwa Mohan Katoch Agra Uttar Pradesh Leprosy"
    passed, violations = check_differential_residue(
        gen_text, sub_text, DEFAULT_BLOCKLIST
    )
    assert passed is False
    assert "cirb" in violations
    assert "hisar" in violations


def test_differential_residue_word_boundaries_and_legitimate_overlap():
    """Word boundary matching prevents false positives like 'hau' inside Chauhan or Hauz Khas."""
    # 'hau' must not match inside 'Chauhan'
    gen_text = (
        "Co-authored publication with Dr. B. S. Chauhan at Hauz Khas IIT Delhi campus."
    )
    sub_text = "Vishwa Mohan Katoch Leprosy Research"
    passed, violations = check_differential_residue(gen_text, sub_text, ["hau"])
    assert passed is True
    assert violations == []

    # 'gaurav' is legitimate if it appears in subject's own context
    gen_text_coauthor = "Project with Dr. Gaurav Sharma published in 2018."
    sub_text_coauthor = "Dr. Gaurav Sharma co-author on ICMR leprosy monograph."
    passed_coauthor, violations_coauthor = check_differential_residue(
        gen_text_coauthor, sub_text_coauthor, ["gaurav"]
    )
    assert passed_coauthor is True
    assert violations_coauthor == []


def test_custom_repository_state_gating():
    """Verify that user-registered custom repositories are strictly state-gated.

    A Haryana custom repo registered in the database/registry must NOT leak into a
    UP subject's public records matrix.
    """
    custom_repo = PublicRecordRepository(
        category_id="test_custom_haryana_land_records",
        category_name="Haryana Test Custom Revenue Archive",
        domain="land_revenue",
        jurisdiction_level="state",
        state="Haryana",
        online_since_year=2012,
        offline_cutoff_year=2011,
        digitization_status="digitized_open_search",
        portal_url="https://jamabandi.nic.in",
        search_query_template='site:jamabandi.nic.in "{name}"',
        offline_repository_name="District Revenue Record Room (Hisar / Rewari)",
        offline_custodian="District Revenue Officer",
        offline_retrieval_method="Inspection of jamabandi registers",
        required_identifiers=["Khewat Number"],
        forensic_utility_notes="Proof of ancestral agricultural landholding in Haryana.",
        is_custom=True,
    )
    register_public_repository(custom_repo)

    # 1. UP Subject: Katoch
    katoch = PersonProfile(
        name="Dr. Vishwa Mohan Katoch",
        affiliation="National JALMA Institute for Leprosy, Agra, Uttar Pradesh",
        birth_place="Agra, Uttar Pradesh",
    )
    katoch_matrix = derive_subject_record_matrix(katoch)
    katoch_all_repos = (
        katoch_matrix["online_reachable"] + katoch_matrix["offline_archives"]
    )
    katoch_ids = {r["category_id"] for r in katoch_all_repos}

    assert "test_custom_haryana_land_records" not in katoch_ids, (
        "Haryana custom repo leaked into UP subject matrix!"
    )

    # Verify differential residue on katoch matrix
    katoch_matrix_text = " ".join(
        f"{r.get('category_name', '')} {r.get('offline_repository_name', '')} {r.get('custom_search_query', '')}"
        for r in katoch_all_repos
    )
    katoch_context = f"{katoch.name} {katoch.affiliation} {katoch.birth_place}"
    passed, violations = check_differential_residue(katoch_matrix_text, katoch_context)
    assert passed is True, f"Yadav residue leaked into Katoch matrix: {violations}"

    # 2. Haryana Subject: Yadav
    yadav = PersonProfile(
        name="Prem Singh Yadav",
        affiliation="ICAR - Central Institute for Research on Buffaloes, Hisar, Haryana",
        birth_place="Nimoth, Rewari, Haryana",
    )
    yadav_matrix = derive_subject_record_matrix(yadav)
    yadav_ids = {
        r["category_id"]
        for r in (yadav_matrix["online_reachable"] + yadav_matrix["offline_archives"])
    }
    assert "test_custom_haryana_land_records" in yadav_ids, (
        "Haryana custom repo should be present for Haryana subject!"
    )


def test_national_umbrella_domain_relevance_gating():
    """Verify that discipline-specialized national umbrella repos (e.g. KrishiKosh)
    are gated by subject domain/discipline relevance.

    For example, KrishiKosh with CCSHAU in its offline repository name must NOT leak
    into a medical subject (Katoch) matrix, but MUST be present for an agricultural
    subject (Yadav).
    """
    agri_umbrella = PublicRecordRepository(
        category_id="test_krishikosh_agri_repository",
        category_name="KrishiKosh Test Institutional Repository",
        domain="academic_theses_and_faculty_publications",
        jurisdiction_level="national",
        state="Central / Agricultural Universities",
        online_since_year=2010,
        offline_cutoff_year=2009,
        digitization_status="digitized_open_search",
        portal_url="https://krishikosh.egranth.ac.in",
        search_query_template='site:krishikosh.egranth.ac.in "{name}"',
        offline_repository_name="ICAR-SAU Library / CCSHAU Nehru Library Archive",
        offline_custodian="University Librarian",
        offline_retrieval_method="Inter-library loan",
        required_identifiers=["Thesis Accession No"],
        forensic_utility_notes="MSc/PhD theses submitted to Indian agricultural universities.",
        is_custom=True,
    )
    register_public_repository(agri_umbrella)

    # 1. UP Medical Subject: Dr. Katoch (medical microbiology / leprosy)
    katoch = PersonProfile(
        name="Dr. Vishwa Mohan Katoch",
        field="Medical Microbiology, Leprosy",
        affiliation="National JALMA Institute for Leprosy, Agra, Uttar Pradesh",
        birth_place="Agra, Uttar Pradesh",
    )
    katoch_matrix = derive_subject_record_matrix(katoch)
    katoch_all = (
        katoch_matrix["online_reachable"] + katoch_matrix["offline_archives"]
    )
    katoch_ids = {r["category_id"] for r in katoch_all}

    assert "test_krishikosh_agri_repository" not in katoch_ids, (
        "Agricultural repository must NOT be included for medical subject Katoch!"
    )

    katoch_matrix_text = " ".join(
        f"{r.get('category_name', '')} {r.get('offline_repository_name', '')} {r.get('custom_search_query', '')}"
        for r in katoch_all
    )
    katoch_context = f"{katoch.name} {katoch.affiliation} {katoch.birth_place}"
    passed, violations = check_differential_residue(katoch_matrix_text, katoch_context)
    assert passed is True, f"CCSHAU/Yadav residue leaked into Katoch matrix: {violations}"
    assert "ccshau" not in katoch_matrix_text.lower(), "ccshau leaked into Katoch matrix!"

    # 2. Agricultural Subject: Yadav (animal biotechnology / CIRB)
    yadav = PersonProfile(
        name="Prem Singh Yadav",
        field="Animal Biotechnology, Cryopreservation",
        affiliation="ICAR - Central Institute for Research on Buffaloes, Hisar, Haryana",
        birth_place="Nimoth, Rewari, Haryana",
    )
    yadav_matrix = derive_subject_record_matrix(yadav)
    yadav_ids = {
        r["category_id"]
        for r in (yadav_matrix["online_reachable"] + yadav_matrix["offline_archives"])
    }
    assert "test_krishikosh_agri_repository" in yadav_ids, (
        "Agricultural repository MUST be included for agricultural/animal biotech subject Yadav!"
    )


def test_harness_stage_report_mocked_http(capsys):
    """Test full initial dryrun harness stages with mocked HTTP server calls."""
    identify_mock = {
        "results": [
            {
                "kind": "identity",
                "name": "Dr. Vishwa Mohan Katoch",
                "wikidata_id": "Q131160362",
                "wikipedia_url": None,
                "field": "Microbiology, Leprosy",
                "affiliation": "National JALMA Institute for Leprosy, Agra",
                "nationality": "Indian",
                "birth_year": "1953",
            }
        ]
    }

    research_mock = {
        "profile": {
            "name": "Dr. Vishwa Mohan Katoch",
            "session_id": "katoch-sess-test1",
            "field": "Microbiology, Leprosy",
            "affiliation": "National JALMA Institute for Leprosy, Agra, Uttar Pradesh",
            "sources": [
                {
                    "url": "https://pubmed.ncbi.nlm.nih.gov/12345",
                    "title": "Diagnosis of Leprosy by PCR",
                    "reliability": "primary",
                    "source_type": "academic_paper",
                },
                {
                    "url": "https://www.thehindu.com/news/katoch-appointed-dg-icmr",
                    "title": "Dr Katoch takes charge as DG ICMR",
                    "reliability": "secondary",
                    "source_type": "news",
                },
            ],
            "claims": [],
        }
    }

    forensics_mock = {
        "pivots": [
            {
                "pivot_id": "piv1",
                "pivot_type": "institution",
                "title": "National JALMA Institute for Leprosy",
                "location": "Agra",
            }
        ],
        "inquiries": [
            {
                "inquiry_id": "inq1",
                "fact_anchor": "Doctoral Thesis in Microbiology",
                "deductive_question": "Where was the Ph.D. submitted?",
                "probe_queries": ['"V. M. Katoch" "thesis"'],
                "expected_paper_trails": ["University Library Deposit"],
            }
        ],
    }

    civic_mock = {
        "added_count": 2,
        "inquiries": forensics_mock["inquiries"]
        + [
            {
                "inquiry_id": "civ1",
                "fact_anchor": "Electoral Roll in Agra",
                "deductive_question": "Which voter roll lists Dr. Katoch?",
                "probe_queries": ['"V. M. Katoch" "Agra"'],
                "expected_paper_trails": ["ECI Voter Roll"],
            }
        ],
    }

    matrix_mock = {
        "matrix": {
            "online_reachable": [
                {
                    "category_id": "shodhganga_theses",
                    "category_name": "Shodhganga",
                    "custom_search_query": 'site:shodhganga.inflibnet.ac.in "Katoch"',
                }
            ],
            "offline_archives": [],
        }
    }

    dorks_mock = {
        "dorks": [
            {
                "category": "academic_theses",
                "title": "Shodhganga / INFLIBNET Doctoral Dissertation",
                "query": 'site:shodhganga.inflibnet.ac.in "Katoch"',
                "description": "Thesis query",
            }
        ]
    }

    def _mock_urlopen(req, *args, **kwargs):
        url = req.full_url
        if "/api/identify" in url:
            data = identify_mock
        elif "/api/research/start" in url:
            data = research_mock
        elif "/api/forensics/summary" in url:
            data = forensics_mock
        elif "/api/forensics/inquiries/expand-civic" in url:
            data = civic_mock
        elif "/api/forensics/atlas/matrix" in url:
            data = matrix_mock
        elif "/api/forensics/dorks" in url:
            data = dorks_mock
        else:
            data = {"ok": True}

        resp_bytes = json.dumps(data).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_bytes
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        exit_code = run_dryrun(
            name="Dr. Vishwa Mohan Katoch",
            api_base="http://localhost:3890",
            wikidata_id="Q131160362",
        )
        assert exit_code == 0

    captured = capsys.readouterr().out
    assert "identify(QID=Q131160362, candidates=1, article=False)" in captured
    assert "research(sources=2" in captured
    assert "discovery(" in captured
    assert "residue=PASS" in captured
    assert (
        "[GATE] Session ID: katoch-sess-test1 — Awaiting human verify/approve in UI"
        in captured
    )


def test_harness_resume_draft_mocked_http(capsys):
    """Test resume-draft mode post-human approval with mocked HTTP server calls."""
    resume_mock = {
        "profile": {
            "name": "Dr. Vishwa Mohan Katoch",
            "session_id": "katoch-sess-approved",
            "field": "Microbiology",
            "affiliation": "National JALMA Institute for Leprosy, Agra",
            "claims": [
                {
                    "text": "Dr. Katoch served as Director-General of ICMR from 2008 to 2015."
                }
            ],
        }
    }
    audit_mock = {"audit": {"ready": True, "blockers": []}}
    draft_mock = {
        "wikitext_en": (
            "'''Vishwa Mohan Katoch''' is an Indian medical microbiologist who served as "
            "Director-General of the Indian Council of Medical Research.<ref>Test ref</ref>"
        )
    }
    qa_mock = {"passed": True, "counts": {"errors": 0, "warnings": 0}}

    def _mock_urlopen(req, *args, **kwargs):
        url = req.full_url
        if "/api/sessions/resume" in url:
            data = resume_mock
        elif "/api/draft/audit" in url:
            data = audit_mock
        elif "/api/draft/qa" in url:
            data = qa_mock
        elif "/api/draft" in url:
            data = draft_mock
        else:
            data = {"ok": True}

        resp_bytes = json.dumps(data).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_bytes
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        exit_code = run_dryrun(
            name="Dr. Vishwa Mohan Katoch",
            api_base="http://localhost:3890",
            resume_draft_sid="katoch-sess-approved",
        )
        assert exit_code == 0

    captured = capsys.readouterr().out
    assert "post-approval(audit_ready=True, issues=0, qa_passed=True" in captured
    assert "residue=PASS" in captured
