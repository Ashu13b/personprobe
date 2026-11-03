"""Algorithmic OSINT Search Operator (Dork) Generator.

Constructs precision targeted search queries across academic, legal, civic,
governmental gazettes, and press archives based on the subject's identity anchors.
"""

from __future__ import annotations

import urllib.parse
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
    from engine.forensics import build_subject_context
    from engine.multilingual_search import transliterate_name

    context = build_subject_context(profile)
    name = profile.name.strip()
    name_parts = name.split()
    initials_variant = (
        f"{name_parts[0][0]}. {name_parts[-1]}" if len(name_parts) > 1 else name
    )
    initials_dotted = (
        f"{name_parts[0][0]}.{name_parts[-1]}" if len(name_parts) > 1 else name
    )

    inst = (context.primary_institution or profile.affiliation or "").strip()
    inst_part = f' OR "{inst}"' if inst else ""

    dorks: list[OsintDork] = []

    def _make_dork(
        category: str,
        title: str,
        portal: str,
        query: str,
        objective: str,
        ev_type: str = "document",
    ) -> OsintDork:
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
    inst_or_city = f'"{inst}" OR "{context.city}" OR ' if (inst and context.city) else (f'"{inst or context.city}" OR ' if (inst or context.city) else "")
    dorks.append(
        _make_dork(
            category="academic_theses",
            title="KrishiKosh Historical Dissertations & University Archive",
            portal="KrishiKosh / E-Granth",
            query=f'site:krishikosh.egranth.ac.in ("{name}" OR "{initials_variant}") ({inst_or_city}"thesis" OR "dissertation")',
            objective="Uncover degree dissertations or departmental publications at affiliated university archives.",
            ev_type="thesis_roster",
        )
    )

    kw_term = " OR ".join(f'"{kw}"' for kw in context.field_keywords[:4]) if context.field_keywords else '"thesis" OR "dissertation"'
    dorks.append(
        _make_dork(
            category="academic_theses",
            title="Shodhganga National Doctoral Theses Repository",
            portal="Shodhganga (INFLIBNET)",
            query=f'site:shodhganga.inflibnet.ac.in ("{name}" OR "{initials_variant}") ({kw_term})',
            objective="Verify national repository record of Ph.D. degree or guided doctoral students.",
            ev_type="doctoral_thesis",
        )
    )

    # 2. Grant Sanctions & Project Budgets (Institutional primary proof)
    dorks.append(
        _make_dork(
            category="grants_funding",
            title="DBT / DST Government Project Sanction Orders",
            portal="Department of Biotechnology / DST",
            query=f'(site:dbtindia.gov.in OR site:dst.gov.in) ("{name}"{inst_part}) ("sanction" OR "grant" OR "project") filetype:pdf',
            objective="Extract government project sanction orders, grant numbers, and budget allocations.",
            ev_type="grant_sanction",
        )
    )

    dorks.append(
        _make_dork(
            category="grants_funding",
            title="National Research & Scientific Grants",
            portal="National Funding Agencies / Ministries",
            query=f'(site:icar.org.in OR site:dst.gov.in OR site:csir.res.in) ("{name}"{inst_part}) ("grant" OR "sanction" OR "project") filetype:pdf',
            objective="Corroborate research project allocations and funding sanctions.",
            ev_type="financial_table",
        )
    )

    # 3. Official Gazettes & Government Orders (Supreme statutory authority)
    dorks.append(
        _make_dork(
            category="gazettes_statutory",
            title="The Gazette of India (eGazette Central Appointments)",
            portal="eGazette of India",
            query=f'site:egazette.gov.in ("{name}"{inst_part}) ("appointment" OR "gazette" OR "cadre" OR "promotion") filetype:pdf',
            objective="Retrieve official gazetted appointment, seniority list, or central presidential awards.",
            ev_type="gazette_notification",
        )
    )

    if context.state == "Haryana":
        state_title = "Haryana Government Gazette & University Notifications"
        state_portal = "Haryana State Gazette"
        geo_terms = f' ("{context.city}" OR "{context.district}")' if (context.city or context.district) else ""
        state_query = f'site:csharyana.gov.in OR site:haryana.gov.in ("{name}" OR "{initials_variant}"){geo_terms}'
    elif context.state:
        state_title = f"{context.state} Government Gazette & University Notifications"
        state_portal = f"{context.state} State Gazette"
        state_query = f'"{name}" "{context.state}" "gazette" OR "notification"'
    else:
        state_title = "State Government Gazette & University Notifications"
        state_portal = "State Gazette"
        state_query = f'"{name}" "gazette" OR "notification"'

    dorks.append(
        _make_dork(
            category="gazettes_statutory",
            title=state_title,
            portal=state_portal,
            query=state_query,
            objective="Discover state university degree conferrals, state honors, or statutory notifications.",
            ev_type="gazette_notification",
        )
    )

    # 4. Judicial & Administrative Tribunals (Homonym check & service timeline)
    inst_search = f' ("{inst}")' if inst else ""
    dorks.append(
        _make_dork(
            category="civic_legal",
            title="IndianKanoon CAT & High Court Service Dockets",
            portal="IndianKanoon (CAT / HC)",
            query=f'site:indiankanoon.org ("{name}"){inst_search}',
            objective="Check for service seniority determinations, administrative orders, and rule out legal homonyms.",
            ev_type="tribunal_order",
        )
    )

    geo = context.district or context.city or context.state
    geo_term = f' ("{geo}")' if geo else ""
    dorks.append(
        _make_dork(
            category="civic_legal",
            title="eCourts District & Sessions Court Registry",
            portal="e-Courts Services",
            query=f'site:services.ecourts.gov.in ("{name}"){geo_term}',
            objective="Examine civil or land records for legal clean bill and ancestral domicile verification.",
            ev_type="court_docket",
        )
    )

    # 5. Regional Hindi / Vernacular Press
    dev_name = transliterate_name(name, "hi") if context.is_indian else None
    name_filter = f'("{name}" OR "{dev_name}")' if dev_name else f'"{name}"'
    topic_terms = " OR ".join(f'"{kw}"' for kw in context.field_keywords[:3]) if context.field_keywords else '"अनुसंधान"'
    dorks.append(
        _make_dork(
            category="news_investigative",
            title="Hindi Daily Investigative Press (Bhaskar, Amar Ujala, Jagran)",
            portal="Regional Hindi Dailies",
            query=f'(site:amarujala.com OR site:bhaskar.com OR site:jagran.com) {name_filter} ({topic_terms})',
            objective="Harvest regional press reporting on research breakthroughs and career milestones.",
            ev_type="news_article",
        )
    )

    kw = context.field_keywords[0] if context.field_keywords else ""
    if inst and kw:
        topic_context = f' ("{inst}" OR "{kw}")'
    elif inst or kw:
        topic_context = f' ("{inst or kw}")'
    else:
        topic_context = ""
    dorks.append(
        _make_dork(
            category="news_investigative",
            title="National English Press Historical Archive (Tribune, The Hindu, Indian Express)",
            portal="National English Dailies",
            query=f'(site:tribuneindia.com OR site:thehindu.com OR site:indianexpress.com) ("{name}" OR "{initials_variant}"){topic_context}',
            objective="Retrieve syndicated national coverage for Wikipedia GNG notability corroboration.",
            ev_type="news_article",
        )
    )

    # 6. Patent & Intellectual Property Registry
    field_term = " OR ".join(f'"{kw}"' for kw in context.field_keywords[:4]) if context.field_keywords else '"patent" OR "invention"'
    dorks.append(
        _make_dork(
            category="patents_ipr",
            title="Indian Patent Office (IPAIRS / InPASS) Inventions",
            portal="InPASS (IPAIRS)",
            query=f'site:ipindia.gov.in OR site:ipindiaonline.gov.in ("{name}" OR "{initials_dotted}") ({field_term})',
            objective="Check for patent filings or technology transfer patents registered in his/her name or institution.",
            ev_type="patent_filing",
        )
    )

    return dorks
