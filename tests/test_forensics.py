"""Tests for the Forensic Investigation Engine: Pivots, Auxiliary Leads, and Sweeps."""
from engine.models import PersonProfile, InvestigationPivot, AuxiliaryLead
from engine.forensics import (
    seed_default_pivots,
    generate_forensic_queries_for_pivot,
    generate_deductive_inquiries,
)
from backend import store


def test_seed_default_pivots_from_profile():
    profile = PersonProfile(
        name="Prem Singh Yadav",
        affiliation="ICAR - Central Institute for Research on Buffaloes (CIRB), Hisar",
        known_for="Hand-guided cloning in buffaloes",
        field="Animal Biotechnology",
    )
    pivots = seed_default_pivots(profile)
    assert len(pivots) >= 3

    types = {p.pivot_type for p in pivots}
    assert "institution" in types
    assert "project_grant" in types
    assert "location" in types

    inst_pivot = next(p for p in pivots if p.pivot_type == "institution")
    assert "CIRB" in inst_pivot.title
    assert inst_pivot.location == "Hisar"


def test_generate_forensic_queries():
    pivot = InvestigationPivot(
        pivot_id="piv-test1",
        pivot_type="project_grant",
        title="Project Hisar Gaurav",
        description="Cloning project at CIRB",
        location="Hisar",
    )
    queries = generate_forensic_queries_for_pivot(pivot, "Prem Singh Yadav")
    assert len(queries) >= 3

    categories = {q["category"] for q in queries}
    assert "thesis_dissertation" in categories
    assert "grant_sanction" in categories

    shodhganga_q = next(q for q in queries if q["category"] == "thesis_dissertation")
    assert "shodhganga.inflibnet.ac.in" in shodhganga_q["query"]


from fastapi.testclient import TestClient
from backend.main import api_app


def test_forensic_routes():
    client = TestClient(api_app)
    # Initialize session
    profile = PersonProfile(
        name="Dr Forensic Subject",
        affiliation="ICAR - National Dairy Research Institute (NDRI), Karnal",
        known_for="In vitro fertilization in cattle",
    )
    store._save_session(profile)

    # 1. GET /forensics/summary (should auto-seed initial anchors)
    resp = client.get("/forensics/summary", params={"profile_name": profile.name})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["pivots"]) >= 2
    assert data["metrics"]["pivots_count"] >= 2

    first_pivot = data["pivots"][0]
    pivot_id = first_pivot["pivot_id"]

    # 2. POST /forensics/leads (add an auxiliary lead)
    lead_resp = client.post("/forensics/leads", json={
        "profile_name": profile.name,
        "pivot_id": pivot_id,
        "title": "NDRI Annual Report 2017 Staff Roster",
        "url": "https://ndri.res.in/reports/2017.pdf",
        "category": "annual_report",
        "lead_notes": "Verify scientist grade and sanctioned laboratory staff",
        "actor": "human",
    })
    assert lead_resp.status_code == 200
    lead_data = lead_resp.json()
    assert lead_data["ok"] is True
    lead_id = lead_data["lead"]["lead_id"]

    # 3. PATCH /forensics/leads/{lead_id} (mark corroborated)
    patch_resp = client.patch(f"/forensics/leads/{lead_id}", json={
        "profile_name": profile.name,
        "lead_id": lead_id,
        "status": "corroborated",
        "source_snippet": "Dr Forensic Subject listed as Principal Scientist, Division of Animal Biotech",
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["lead"]["status"] == "corroborated"

    # 4. POST /forensics/sweep (generate automated public record query leads)
    sweep_resp = client.post("/forensics/sweep", json={
        "profile_name": profile.name,
        "pivot_id": pivot_id,
        "actor": "agent",
    })
    assert sweep_resp.status_code == 200
    assert sweep_resp.json()["new_leads_count"] >= 2


def test_generate_deductive_inquiries_unit():
    profile = PersonProfile(
        name="Prem Singh Yadav",
        affiliation="ICAR - Central Institute for Research on Buffaloes (CIRB), Hisar",
        known_for="Buffalo cloning and embryology",
    )
    # Add an auxiliary lead mentioning 1985 HAU graduation and 1991 Ph.D.
    profile.auxiliary_leads.append(
        AuxiliaryLead(
            lead_id="lead-test-hau",
            title="Graduation Record 1985 HAU",
            lead_notes="Completed B.Sc. in 1985 and Ph.D. in 1991 at CCS HAU Hisar. Funded by NASF ₹89L grant, retired 30.04.2025.",
        )
    )
    inquiries = generate_deductive_inquiries(profile)
    assert len(inquiries) >= 4

    domains = {inq.domain for inq in inquiries}
    assert "academic_degree" in domains
    assert "doctoral_thesis" in domains
    assert "research_grant" in domains
    assert "superannuation" in domains

    deg_inq = next(inq for inq in inquiries if inq.domain == "academic_degree")
    assert "1985" in deg_inq.fact_anchor
    assert any("Convocation" in pt for pt in deg_inq.expected_paper_trails)
    assert any("krishikosh" in q for q in deg_inq.probe_queries)


def test_forensic_inquiries_api():
    client = TestClient(api_app)
    profile = PersonProfile(
        name="Dr Deductive Subject",
        affiliation="CCS Haryana Agricultural University, Hisar",
    )
    profile.auxiliary_leads.append(
        AuxiliaryLead(
            lead_id="lead-inq-1",
            title="B.Sc. 1985 HAU",
            lead_notes="Graduated B.Sc. in 1985 at HAU.",
        )
    )
    store._save_session(profile)

    # 1. POST /forensics/inquiries/generate
    gen_resp = client.post("/forensics/inquiries/generate", json={"profile_name": profile.name})
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["ok"] is True
    assert gen_data["new_inquiries_count"] >= 1
    assert len(gen_data["inquiries"]) >= 1

    inquiry_id = gen_data["inquiries"][0]["inquiry_id"]

    # 2. PATCH /forensics/inquiries/{inquiry_id}
    patch_resp = client.patch(f"/forensics/inquiries/{inquiry_id}", json={
        "profile_name": profile.name,
        "status": "confirmed",
        "findings_summary": "Located convocation entry in CCS HAU library catalogue archive.",
        "actor": "human",
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["ok"] is True
    updated = next(i for i in patch_resp.json()["inquiries"] if i["inquiry_id"] == inquiry_id)
    assert updated["status"] == "confirmed"
    assert "CCS HAU library" in updated["findings_summary"]

    # 3. POST /forensics/inquiries (custom hypothesis)
    custom_resp = client.post("/forensics/inquiries", json={
        "profile_name": profile.name,
        "fact_anchor": "Awarded ICAR Jawaharlal Nehru Award in 1992",
        "domain": "academic_degree",
        "deductive_question": "If awarded JN Award in 1992, what ICAR citation booklet exists?",
        "expected_paper_trails": ["ICAR Foundation Day Awardees Booklet 1992"],
        "probe_queries": ['"Jawaharlal Nehru Award" "1992" "Prem Singh Yadav"'],
        "actor": "human",
    })
    assert custom_resp.status_code == 200
    assert custom_resp.json()["ok"] is True
    assert any(i["fact_anchor"] == "Awarded ICAR Jawaharlal Nehru Award in 1992" for i in custom_resp.json()["inquiries"])

    # 4. POST /forensics/inquiries/{inquiry_id}/probe
    probe_resp = client.post(f"/forensics/inquiries/{inquiry_id}/probe", json={
        "profile_name": profile.name,
        "actor": "agent",
    })
    assert probe_resp.status_code == 200
    assert probe_resp.json()["ok"] is True

    # 4b. POST /forensics/inquiries/probe-all
    probe_all_resp = client.post("/forensics/inquiries/probe-all", json={
        "profile_name": profile.name,
        "actor": "human",
    })
    assert probe_all_resp.status_code == 200
    assert probe_all_resp.json()["ok"] is True
    assert "inquiries" in probe_all_resp.json()

    # 5. DELETE /forensics/inquiries/{inquiry_id}
    del_resp = client.delete(f"/forensics/inquiries/{inquiry_id}", params={"profile_name": profile.name})
    assert del_resp.status_code == 200
    assert not any(i["inquiry_id"] == inquiry_id for i in del_resp.json()["inquiries"])

    # 6. GET /forensics/atlas
    atlas_resp = client.get("/forensics/atlas")
    assert atlas_resp.status_code == 200
    assert atlas_resp.json()["ok"] is True
    assert atlas_resp.json()["total_repositories"] >= 8

    # 7. GET /forensics/atlas/matrix
    matrix_resp = client.get("/forensics/atlas/matrix", params={"profile_name": profile.name})
    assert matrix_resp.status_code == 200
    assert matrix_resp.json()["ok"] is True
    matrix = matrix_resp.json()["matrix"]
    assert "online_reachable" in matrix
    assert "offline_archives" in matrix

    # 8. POST /forensics/inquiries/expand-civic
    civic_resp = client.post("/forensics/inquiries/expand-civic", json={"profile_name": profile.name})
    assert civic_resp.status_code == 200
    assert civic_resp.json()["ok"] is True
    assert civic_resp.json()["added_count"] >= 1

    # 9. POST /forensics/atlas/repository
    new_repo = {
        "category_id": "test_punjab_plrs_registry",
        "category_name": "Punjab Land Records Society (PLRS Jamabandi)",
        "domain": "land_revenue",
        "jurisdiction_level": "state",
        "state": "Punjab",
        "online_since_year": 2011,
        "offline_cutoff_year": 2010,
        "digitization_status": "digitized_open_search",
        "portal_url": "https://jamabandi.punjab.gov.in",
        "search_query_template": 'site:jamabandi.punjab.gov.in "{name}"',
        "offline_repository_name": "District Revenue Archives (सदर मालखाना)",
        "offline_custodian": "District Revenue Officer & Tehsildar",
        "offline_retrieval_method": "Inspection of Jamabandi Registers with Halqa Patwari; RTI Sec 6(1)",
        "required_identifiers": ["Khewat No", "Village Name"],
        "forensic_utility_notes": "Statutory proof of ancestral landholding and rural domicile.",
        "is_custom": True,
    }
    repo_resp = client.post("/forensics/atlas/repository", json=new_repo)
    assert repo_resp.status_code == 200
    assert repo_resp.json()["ok"] is True
    assert repo_resp.json()["repository"]["category_id"] == "test_punjab_plrs_registry"
    assert repo_resp.json()["repository"]["is_custom"] is True

    # Check that atlas now includes the newly registered repository
    atlas_updated = client.get("/forensics/atlas").json()
    assert any(r["category_id"] == "test_punjab_plrs_registry" for r in atlas_updated["repositories"])

    # 10. DELETE /forensics/atlas/repository/{category_id}
    del_repo_resp = client.delete("/forensics/atlas/repository/test_punjab_plrs_registry")
    assert del_repo_resp.status_code == 200
    assert del_repo_resp.json()["ok"] is True
    assert del_repo_resp.json()["deleted_id"] == "test_punjab_plrs_registry"

    # Confirm deleted
    atlas_after_del = client.get("/forensics/atlas").json()
    assert not any(r["category_id"] == "test_punjab_plrs_registry" for r in atlas_after_del["repositories"])

    # 11. POST /forensics/inquiries/log-failure (Learn from Mistakes and Failures)
    target_inq = profile.forensic_inquiries[0]
    fail_payload = {
        "profile_name": profile.name,
        "inquiry_id": target_inq.inquiry_id,
        "failure_mode": "pre_digitization_cutoff",
        "failure_reason": "Online convocation rolls for 1985 not scanned; portal only indexes 2012+.",
        "learned_lesson": "Skip digital queries for pre-1990 degree records; immediately route to physical university library archives.",
        "associated_repository_id": "krishikosh_agricultural_repository",
        "actor": "human",
    }
    fail_resp = client.post("/forensics/inquiries/log-failure", json=fail_payload)
    assert fail_resp.status_code == 200
    assert fail_resp.json()["ok"] is True
    updated_inq = fail_resp.json()["inquiry"]
    assert updated_inq["status"] == "dead_end"
    assert updated_inq["failure_mode"] == "pre_digitization_cutoff"
    assert "Skip digital queries" in updated_inq["learned_lesson"]

    # Verify repository in Atlas accumulated the learned failure mode and warning
    repo_atlas = client.get("/forensics/atlas").json()
    krishi_repo = next(r for r in repo_atlas["repositories"] if r["category_id"] == "krishikosh_agricultural_repository")
    assert "pre_digitization_cutoff" in krishi_repo["known_failure_modes"]
    assert krishi_repo["failure_count"] >= 1

