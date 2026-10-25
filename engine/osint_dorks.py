"""Algorithmic OSINT Search Operator (Dork) Generator.

Constructs precision targeted search queries across academic, legal, civic,
governmental gazettes, and press archives based on the subject's identity anchors.
"""
from __future__ import annotations

import urllib.parse
from typing import Any
from pydantic import BaseModel, Field

from .models import PersonProfile


class OsintDork(BaseModel):
    category: str
    title: str
    target_portal: str
    query: str
    google_url: str
    duckduckgo_url: str
    forensic_objective: str
    expected_evidence_type: str = Field(default="document")


def generate_osint_dorks(profile: PersonProfile) -> list[OsintDork]:
    """Generate categorized OSINT dork templates customized for the person profile."""
    name = profile.name.strip()
    # Name variants
    name_parts = name.split()
    initials_variant = f"{name_parts[0][0]}. {name_parts[-1]}" if len(name_parts) > 1 else name
    initials_dotted = f"{name_parts[0][0]}.{name_parts[-1]}" if len(name_parts) > 1 else name
    surname = name_parts[-1] if name_parts else ""

    inst = (profile.affiliation or "CIRB").strip()
    loc = "Hisar" if "hisar" in (profile.affiliation or "").lower() else "Haryana"

    dorks: list[OsintDork] = []

    def _make_dork(category: str, title: str, portal: str, query: str, objective: str, ev_type: str = "document") -> OsintDork:
        g_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        ddg_url = f"https://duckduckgo.com/?q={urllib.parse.quote_plus(query)}"
        return OsintDork(
            category=category,
            title=title,
            target_portal=portal,
            query=query,
            google_url=g_url,
            duckduckgo_url=ddg_url,
            forensic_objective=objective,
            expected_evidence_type=ev_type,
        )

    # 1. Academic Dissertations & Degrees (Solving the education gap)
    dorks.append(_make_dork(
        category="academic_theses",
        title="KrishiKosh Historical Dissertations & HAU Archive",
        portal="KrishiKosh / E-Granth",
        query=f'site:krishikosh.egranth.ac.in ("{name}" OR "{initials_variant}") ("HAU" OR "Hisar" OR "thesis" OR "dissertation")',
        objective="Uncover 1985/1987/1991 degree dissertations or departmental publications at CCS HAU.",
        ev_type="thesis_roster",
    ))

    dorks.append(_make_dork(
        category="academic_theses",
        title="Shodhganga National Doctoral Theses Repository",
        portal="Shodhganga (INFLIBNET)",
        query=f'site:shodhganga.inflibnet.ac.in ("{name}" OR "{initials_variant}") ("animal" OR "biotechnology" OR "buffalo" OR "reproduction")',
        objective="Verify national repository record of Ph.D. degree or guided doctoral students.",
        ev_type="doctoral_thesis",
    ))

    # 2. Grant Sanctions & Project Budgets (Institutional primary proof)
    dorks.append(_make_dork(
        category="grants_funding",
        title="DBT / DST Government Project Sanction Orders",
        portal="Department of Biotechnology / DST",
        query=f'(site:dbtindia.gov.in OR site:dst.gov.in) ("{name}" OR "{inst}") ("sanction" OR "grant" OR "project") filetype:pdf',
        objective="Extract government project sanction orders, grant numbers, and budget allocations for cloning research.",
        ev_type="grant_sanction",
    ))

    dorks.append(_make_dork(
        category="grants_funding",
        title="ICAR National Agricultural Science Fund (NASF) Sanctions",
        portal="ICAR NASF",
        query=f'site:icar.org.in "NASF" ("{name}" OR "{inst}" OR "CIRB") ("cloning" OR "buffalo") filetype:pdf',
        objective="Corroborate multi-crore flagship cloning project allocations (e.g. CIRB-NEF project codes).",
        ev_type="financial_table",
    ))

    # 3. Official Gazettes & Government Orders (Supreme statutory authority)
    dorks.append(_make_dork(
        category="gazettes_statutory",
        title="The Gazette of India (eGazette Central Appointments)",
        portal="eGazette of India",
        query=f'site:egazette.gov.in ("{name}" OR "{inst}") ("Agricultural Research Service" OR "Principal Scientist" OR "ICAR") filetype:pdf',
        objective="Retrieve official gazetted appointment, seniority list, or central presidential awards.",
        ev_type="gazette_notification",
    ))

    dorks.append(_make_dork(
        category="gazettes_statutory",
        title="Haryana Government Gazette & University Notifications",
        portal="Haryana State Gazette",
        query=f'site:csharyana.gov.in OR site:haryana.gov.in ("{name}" OR "{initials_variant}") ("Hisar" OR "Rewari")',
        objective="Discover state university degree conferrals, state honors, or statutory notifications.",
        ev_type="gazette_notification",
    ))

    # 4. Judicial & Administrative Tribunals (Homonym check & service timeline)
    dorks.append(_make_dork(
        category="civic_legal",
        title="IndianKanoon CAT & High Court Service Dockets",
        portal="IndianKanoon (CAT / HC)",
        query=f'site:indiankanoon.org ("{name}") ("Central Institute for Research on Buffaloes" OR "ICAR" OR "CIRB")',
        objective="Check for service seniority determinations, administrative orders, and rule out legal homonyms.",
        ev_type="tribunal_order",
    ))

    dorks.append(_make_dork(
        category="civic_legal",
        title="eCourts District & Sessions Court Registry",
        portal="e-Courts Services",
        query=f'site:services.ecourts.gov.in ("{name}") ("Hisar" OR "Rewari")',
        objective="Examine civil or land records for legal clean bill and ancestral domicile verification.",
        ev_type="court_docket",
    ))

    # 5. Cloning Milestones & Regional Hindi Press (Independent secondary reporting)
    dorks.append(_make_dork(
        category="news_investigative",
        title="Hindi Daily Investigative Press (Bhaskar, Amar Ujala, Jagran)",
        portal="Regional Hindi Dailies",
        query=f'(site:amarujala.com OR site:bhaskar.com OR site:jagran.com) ("प्रेम सिंह यादव" OR "डॉ. प्रेम सिंह") ("क्लोनिंग" OR "हिसार गौरव" OR "भैंस अनुसंधान")',
        objective="Harvest local Haryana front-page reporting on calf-cloning breakthroughs and retirement celebrations.",
        ev_type="news_article",
    ))

    dorks.append(_make_dork(
        category="news_investigative",
        title="National English Press Historical Archive (Tribune, The Hindu, Indian Express)",
        portal="National English Dailies",
        query=f'(site:tribuneindia.com OR site:thehindu.com OR site:indianexpress.com) ("{name}" OR "{initials_variant}") ("CIRB" OR "cloned calf" OR "Hisar Gaurav")',
        objective="Retrieve syndicated national coverage for Wikipedia GNG notability corroboration.",
        ev_type="news_article",
    ))

    # 6. Patent & Intellectual Property Registry
    dorks.append(_make_dork(
        category="patents_ipr",
        title="Indian Patent Office (IPAIRS / InPASS) Inventions",
        portal="InPASS (IPAIRS)",
        query=f'site:ipindia.gov.in OR site:ipindiaonline.gov.in ("{name}" OR "{initials_dotted}") ("cloning" OR "semen" OR "embryo" OR "cryopreservation")',
        objective="Check for patent filings or technology transfer patents registered in his name or by CIRB.",
        ev_type="patent_filing",
    ))

    return dorks
