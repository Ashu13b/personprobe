"""Tests verifying subject-agnostic discovery intelligence across PersonProbe.

Verifies:
1. Category parity on the Prem Singh Yadav fixture: inquiries fire for education, PhD,
   service entry, grant, retirement, deputation, award, and origins, with every anchor quoting
   text present in the subject's claims or profile fields.
2. Discriminating negative test: second subject profile outside Haryana and animal science,
   with "1963" and "Ph.D" in claims, has zero occurrences of the Yadav blocklist across all
   discovery generators.
3. Clean fallback for non-Indian subjects (no Indian civic/state record injection).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from engine.models import PersonProfile, Claim
from engine.forensics import (
    seed_default_pivots,
    generate_deductive_inquiries,
    generate_forensic_queries_for_pivot,
    build_subject_context,
)
from engine.osint_dorks import generate_osint_dorks
from engine.public_records_atlas import (
    derive_subject_record_matrix,
    generate_civic_inquiries,
)
from engine.suggester import suggest_next_urls

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "Prem_Singh_Yadav.json"

BLOCKLIST = [
    "nimoth",
    "rewari",
    "hisar",
    "cirb",
    "hau",
    "ccshau",
    "buffalo",
    "cloning",
    "gaurav",
    "nasf",
    "sirsa road",
    "125001",
    "125004",
]


def test_prem_singh_yadav_category_parity():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    profile = PersonProfile(**data["profile"])

    inquiries = generate_deductive_inquiries(profile)
    assert len(inquiries) >= 6

    claim_texts = [c.text for c in profile.claims if c.text]
    profile_text = f"{profile.birth_place} {profile.birth_date} {profile.affiliation}"

    categories_found = set()
    for inq in inquiries:
        # Every anchor must quote text present in claims or profile fields
        in_claims = any(inq.fact_anchor in ct or ct in inq.fact_anchor for ct in claim_texts)
        in_profile = inq.fact_anchor in profile_text or any(part in inq.fact_anchor for part in [profile.birth_place, profile.affiliation] if part)
        assert in_claims or in_profile, f"Anchor not quoted from claims/fields: {inq.fact_anchor}"

        anchor_l = inq.fact_anchor.lower()
        if inq.domain == "academic_degree":
            categories_found.add("education")
        elif inq.domain == "doctoral_thesis":
            categories_found.add("phd")
        elif inq.domain == "service_entry":
            categories_found.add("service_entry")
        elif inq.domain == "research_grant":
            if any(k in anchor_l for k in ("associateship", "deputation", "fellow", "daad", "dbt")):
                categories_found.add("deputation")
            else:
                categories_found.add("grant")
        elif inq.domain == "superannuation":
            categories_found.add("retirement")
        elif inq.domain == "general":
            if any(k in anchor_l for k in ("born", "nimoth", "rewari")):
                categories_found.add("origins")
            else:
                categories_found.add("award")

    required_categories = {
        "education",
        "phd",
        "service_entry",
        "grant",
        "retirement",
        "deputation",
        "award",
        "origins",
    }
    assert required_categories.issubset(categories_found), f"Missing categories: {required_categories - categories_found}"


def test_negative_discriminating_subject():
    """Build a non-Haryana subject with field outside animal science and '1963' and 'Ph.D' in text.

    Assert that NONE of the blocklist appears anywhere in the combined output across EVERY generator.
    """
    profile = PersonProfile(
        name="Dr. Vishwa Mohan Katoch",
        birth_date="15 November 1953",
        birth_place="Varanasi, Uttar Pradesh, India",
        nationality="Indian",
        affiliation="National JALMA Institute for Leprosy, Agra, Uttar Pradesh",
        field="Medical Microbiology & Mycobacterial Diseases",
        known_for="Molecular diagnosis and multidrug regimens for leprosy",
        claims=[
            Claim(field="education", text="Completed Ph.D in Medical Microbiology in 1963 at University of Delhi."),
            Claim(field="position", text="Appointed Director-General of Indian Council of Medical Research (ICMR)."),
            Claim(field="award", text="Conferred Padma Shri in Medicine for distinguished contributions to medical science."),
            Claim(field="career", text="Superannuated after 35 years of civil medical service in 2015."),
        ],
    )

    combined_outputs: list[str] = []

    # 1. Pivots
    pivots = seed_default_pivots(profile)
    for p in pivots:
        combined_outputs.append(str(p.model_dump()))
        # 2. Pivot queries
        queries = generate_forensic_queries_for_pivot(p, profile.name)
        combined_outputs.append(str(queries))

    # 3. Deductive inquiries
    inquiries = generate_deductive_inquiries(profile)
    for inq in inquiries:
        combined_outputs.append(str(inq.model_dump()))

    # 4. OSINT dorks
    dorks = generate_osint_dorks(profile)
    for d in dorks:
        combined_outputs.append(str(d.model_dump()))

    # 5. Public records atlas matrix
    matrix = derive_subject_record_matrix(profile)
    combined_outputs.append(str(matrix))

    # 6. Civic inquiries
    civic = generate_civic_inquiries(profile)
    for c in civic:
        combined_outputs.append(str(c.model_dump()))

    # 7. Suggester path
    with patch("engine.researcher._search_web", return_value=[]):
        suggestions = suggest_next_urls(profile)
    combined_outputs.append(str(suggestions))

    full_output = " ".join(combined_outputs).lower()

    violations = [term for term in BLOCKLIST if term in full_output]
    assert violations == [], f"Found blocklist terms in discovery output for non-Haryana subject: {violations}"


def test_non_indian_subject_clean_isolation():
    """Non-Indian subjects must skip India-specific public records without leakage."""
    profile = PersonProfile(
        name="Dr. Marie Curie",
        birth_date="7 November 1867",
        birth_place="Warsaw, Poland",
        nationality="French",
        affiliation="University of Paris",
        field="Physics and Chemistry",
        known_for="Radioactivity discovery and isolation of radium",
        claims=[
            Claim(field="education", text="Awarded Ph.D from the University of Paris in 1903."),
            Claim(field="award", text="Awarded Nobel Prize in Physics in 1903."),
        ],
    )
    context = build_subject_context(profile)
    assert not context.is_indian
    assert context.state == ""

    civic = generate_civic_inquiries(profile)
    assert len(civic) == 0

    matrix = derive_subject_record_matrix(profile)
    assert matrix["primary_state"] == "International"
    for r in matrix["online_reachable"]:
        assert r.get("state") not in ("Haryana", "Uttar Pradesh", "Delhi / NCR", "Maharashtra")
