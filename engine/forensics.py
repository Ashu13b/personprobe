"""Forensic Investigation Engine: Pivots, Auxiliary Leads, and Public Record Queries.

This engine separates forensic background intelligence from surface-level Wikipedia
draft citations. It tracks institutions, projects, co-actors, grants, spatial quarters,
and generates multi-hop public record sweeps across:
- Shodhganga (National doctoral theses and dissertation acknowledgments)
- IndianKanoon (Central Administrative Tribunal and High Court seniority/orders)
- ICAR & Ministry Annual Reports (Project grant numbers, budgets, sanctioned posts)
- Recruitment & Vacancy Notices (Project fellows, JRF/SRF/RA hired on grants)
- Gazette & Electoral Archives (Residential, campus, and statutory appointments)
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from engine.models import (
    PersonProfile,
    InvestigationPivot,
    AuxiliaryLead,
    ForensicInquiry,
)


@dataclass
class LifeEvent:
    category: str  # "education", "phd", "service_entry", "grant", "superannuation", "deputation", "award", "ancestry", "residence"
    anchor_text: str  # exact quoted string from profile claims / fields
    domain: str
    date_context: str | None = None
    institution: str | None = None
    raw_text: str = ""


@dataclass
class SubjectContext:
    country: str = "India"
    is_indian: bool = True
    state: str = ""
    district: str = ""
    city: str = ""
    village: str = ""
    address: str = ""
    institutions: list[str] = field(default_factory=list)
    primary_institution: str = ""
    institution_slug: str = ""
    field_keywords: list[str] = field(default_factory=list)
    life_events: list[LifeEvent] = field(default_factory=list)


def get_valid_indian_states(active_atlas: list | None = None) -> list[str]:
    """Derive registered Indian state names from active atlas repositories without hardcoding."""
    if active_atlas is None:
        try:
            from engine.public_records_atlas import get_public_records_atlas

            active_atlas = get_public_records_atlas()
        except Exception:
            try:
                from engine.public_records_atlas import BUILTIN_REPOSITORIES

                active_atlas = BUILTIN_REPOSITORIES
            except Exception:
                active_atlas = []
    states: list[str] = []
    seen: set[str] = set()
    for repo in active_atlas:
        st = getattr(repo, "state", None)
        if st and not st.startswith("Central") and not st.startswith("National"):
            if st not in seen:
                seen.add(st)
                states.append(st)
    return states


def _extract_field_keywords(
    field_val: str | None, known_for_val: str | None
) -> list[str]:
    combined = f"{field_val or ''} {known_for_val or ''}"
    words = re.findall(r"\b[A-Za-z]{4,}\b", combined)
    stopwords = {
        "research",
        "institute",
        "central",
        "department",
        "division",
        "university",
        "technology",
        "studies",
        "science",
        "sciences",
        "about",
        "with",
        "from",
        "into",
        "their",
        "under",
        "team",
        "national",
        "international",
        "indian",
        "development",
    }
    keywords: list[str] = []
    seen: set[str] = set()
    for w in words:
        w_l = w.lower()
        if w_l not in stopwords and w_l not in seen:
            seen.add(w_l)
            keywords.append(w_l)
    return keywords


def build_subject_context(profile: PersonProfile) -> SubjectContext:
    """Derive geography, institutions, field keywords, and dated life events from PersonProfile."""
    context = SubjectContext()
    valid_states = get_valid_indian_states()

    # 1. Nationality & Indian detection
    nationality = profile.nationality or ""
    nat_l = nationality.strip().lower()
    if nat_l:
        if nat_l in ("indian", "india"):
            context.country = "India"
            context.is_indian = True
        else:
            context.country = nationality.strip()
            context.is_indian = "india" in nat_l
    else:
        bp_l = (profile.birth_place or "").lower()
        if "india" in bp_l or "bharat" in bp_l:
            context.country = "India"
            context.is_indian = True
        else:
            try:
                from engine.multilingual_search import detect_languages

                langs = detect_languages(None, profile.name)
                context.is_indian = "hi" in langs
            except Exception:
                context.is_indian = True
            context.country = "India" if context.is_indian else "Unknown"

    # 2. State & Geography from birth_place & affiliation
    combined_geo = f"{profile.birth_place or ''} {profile.affiliation or ''}"
    combined_l = combined_geo.lower()
    for st in valid_states:
        if st.lower() in combined_l:
            context.state = st
            break
        for part in st.split("/"):
            p_clean = part.strip().lower()
            if len(p_clean) >= 4 and p_clean in combined_l:
                context.state = st
                break
        if context.state:
            break

    if context.state and not (nationality and not context.is_indian):
        context.is_indian = True
        context.country = "India"

    # Birth place components
    if profile.birth_place:
        parts = [p.strip() for p in profile.birth_place.split(",") if p.strip()]
        for p in parts:
            p_l = p.lower()
            if "district" in p_l or "dist." in p_l:
                context.district = re.sub(r"(?i)\b(district|dist\.?)\b", "", p).strip()
            elif "village" in p_l or "vill." in p_l:
                context.village = re.sub(r"(?i)\b(village|vill\.?)\b", "", p).strip()
            elif p_l in ("india", "bharat"):
                context.is_indian = True
                context.country = "India"
            elif any(p_l == st.lower() or p_l in st.lower() for st in valid_states):
                if not context.state:
                    context.state = p

        non_geo = [
            p
            for p in parts
            if not (
                "district" in p.lower()
                or "dist." in p.lower()
                or "village" in p.lower()
                or "vill." in p.lower()
                or p.lower() in ("india", "bharat")
                or any(
                    p.lower() == st.lower() or p.lower() in st.lower()
                    for st in valid_states
                )
            )
        ]
        if non_geo:
            first = non_geo[0]
            if context.village:
                if not context.city and not context.district:
                    context.city = first
            elif len(parts) >= 4 or "tehsil" in first.lower():
                context.village = first
            else:
                if not context.city:
                    context.city = first
                if not context.district:
                    context.district = first

    # Affiliation components
    if profile.affiliation:
        affil_clean = profile.affiliation.strip()
        context.primary_institution = affil_clean
        m_acronym = re.search(r"\(([A-Za-z0-9\-]+)\)", affil_clean)
        if m_acronym:
            acronym = m_acronym.group(1)
            context.institutions.append(acronym)
            context.institution_slug = acronym.lower()
        context.institutions.append(affil_clean)

        affil_parts = [p.strip() for p in affil_clean.split(",") if p.strip()]
        if len(affil_parts) >= 2:
            for part in affil_parts[1:]:
                p_l = part.lower()
                if any(
                    p_l == st.lower() or p_l in st.lower() for st in valid_states
                ) or p_l in ("india", "bharat"):
                    continue
                cleaned = re.sub(r"-\s*\d+", "", part).strip()
                if cleaned and not any(
                    w in cleaned.lower()
                    for w in (
                        "institute",
                        "university",
                        "centre",
                        "center",
                        "division",
                        "college",
                        "council",
                        "department",
                    )
                ):
                    if not context.city:
                        context.city = cleaned
                    if not context.district and not context.village:
                        context.district = cleaned
                    break

    # 3. Field keywords
    context.field_keywords = _extract_field_keywords(profile.field, profile.known_for)

    # 4. Life Events from claims
    events: list[LifeEvent] = []
    for c in profile.claims:
        text = (c.text or "").strip()
        if not text:
            continue
        fld = (c.field or "").lower()
        t_l = text.lower()
        date = c.date_context

        if fld == "education":
            if any(
                k in t_l
                for k in ("ph.d", "phd", "doctorate", "doctoral", "dissertation")
            ):
                events.append(
                    LifeEvent(
                        category="phd",
                        anchor_text=text,
                        domain="doctoral_thesis",
                        date_context=date,
                        raw_text=text,
                    )
                )
            if any(
                k in t_l
                for k in (
                    "b.sc",
                    "m.sc",
                    "bachelor",
                    "master",
                    "degree",
                    "graduat",
                    "college",
                    "university",
                )
            ):
                events.append(
                    LifeEvent(
                        category="education",
                        anchor_text=text,
                        domain="academic_degree",
                        date_context=date,
                        raw_text=text,
                    )
                )
            if not any(
                k in t_l
                for k in (
                    "ph.d",
                    "phd",
                    "doctorate",
                    "doctoral",
                    "b.sc",
                    "m.sc",
                    "bachelor",
                    "master",
                )
            ):
                events.append(
                    LifeEvent(
                        category="education",
                        anchor_text=text,
                        domain="academic_degree",
                        date_context=date,
                        raw_text=text,
                    )
                )
        elif fld in ("career", "position"):
            if any(k in t_l for k in ("retir", "superannuat", "farewell")):
                events.append(
                    LifeEvent(
                        category="superannuation",
                        anchor_text=text,
                        domain="superannuation",
                        date_context=date,
                        raw_text=text,
                    )
                )
            elif any(
                k in t_l
                for k in (
                    "overseas",
                    "deputation",
                    "daad",
                    "fellowship",
                    "research stay",
                    "associateship",
                    "visiting",
                )
            ):
                events.append(
                    LifeEvent(
                        category="deputation",
                        anchor_text=text,
                        domain="research_grant",
                        date_context=date,
                        raw_text=text,
                    )
                )
            elif any(
                k in t_l
                for k in (
                    "joined",
                    "appointed",
                    "selected",
                    "principal scientist",
                    "scientist",
                    "head",
                    "director",
                    "professor",
                    "cadre",
                    "officer",
                )
            ):
                events.append(
                    LifeEvent(
                        category="service_entry",
                        anchor_text=text,
                        domain="service_entry",
                        date_context=date,
                        raw_text=text,
                    )
                )
            else:
                events.append(
                    LifeEvent(
                        category="service_entry",
                        anchor_text=text,
                        domain="service_entry",
                        date_context=date,
                        raw_text=text,
                    )
                )
        elif fld == "award":
            events.append(
                LifeEvent(
                    category="award",
                    anchor_text=text,
                    domain="general",
                    date_context=date,
                    raw_text=text,
                )
            )
        elif fld in ("known_for", "project"):
            if any(
                k in t_l
                for k in (
                    "grant",
                    "sanction",
                    "fund",
                    "project",
                    "nasf",
                    "dbt",
                    "dst",
                    "icar",
                )
            ):
                events.append(
                    LifeEvent(
                        category="grant",
                        anchor_text=text,
                        domain="research_grant",
                        date_context=date,
                        raw_text=text,
                    )
                )
        elif fld in ("birth_place", "birth_date", "ancestry"):
            if not any(
                k in t_l
                for k in (
                    "kg",
                    "calf",
                    "bull",
                    "animal",
                    "delivery",
                    "litter",
                    "offspring",
                )
            ):
                events.append(
                    LifeEvent(
                        category="ancestry",
                        anchor_text=text,
                        domain="general",
                        date_context=date,
                        raw_text=text,
                    )
                )

    # Auxiliary leads fallback / additions
    def _extract_lead_clause(lead: AuxiliaryLead, kws: tuple[str, ...]) -> str:
        if any(k in lead.title.lower() for k in kws):
            return lead.title
        notes = lead.lead_notes or ""
        parts = re.split(r",\s*|;\s*|\.\s+(?=[A-Z])|\s+and\s+(?=Ph\.?D)", notes)
        for p in parts:
            p_clean = p.strip()
            if any(k in p_clean.lower() for k in kws):
                return p_clean
        return f"{lead.title} ({kws[0]})"

    for lead in profile.auxiliary_leads:
        full_lead = f"{lead.title} {lead.lead_notes or ''}".strip()
        fl_l = full_lead.lower()
        if any(
            k in fl_l
            for k in ("b.sc", "m.sc", "bachelor", "master", "graduation", "graduated")
        ):
            anchor = _extract_lead_clause(lead, ("b.sc", "m.sc", "graduat", "degree"))
            events.append(
                LifeEvent(
                    category="education",
                    anchor_text=anchor,
                    domain="academic_degree",
                    raw_text=full_lead,
                )
            )
        if any(k in fl_l for k in ("ph.d", "phd", "doctoral", "dissertation")):
            anchor = _extract_lead_clause(
                lead, ("ph.d", "phd", "doctoral", "dissertation")
            )
            events.append(
                LifeEvent(
                    category="phd",
                    anchor_text=anchor,
                    domain="doctoral_thesis",
                    raw_text=full_lead,
                )
            )
        if any(k in fl_l for k in ("grant", "funded", "sanction")):
            anchor = _extract_lead_clause(lead, ("grant", "funded", "sanction"))
            events.append(
                LifeEvent(
                    category="grant",
                    anchor_text=anchor,
                    domain="research_grant",
                    raw_text=full_lead,
                )
            )
        if any(k in fl_l for k in ("retir", "superannuat", "farewell")):
            anchor = _extract_lead_clause(lead, ("retir", "superannuat", "farewell"))
            events.append(
                LifeEvent(
                    category="superannuation",
                    anchor_text=anchor,
                    domain="superannuation",
                    raw_text=full_lead,
                )
            )
        if any(k in fl_l for k in ("award", "medal", "honor", "prize")):
            anchor = _extract_lead_clause(lead, ("award", "medal", "honor", "prize"))
            events.append(
                LifeEvent(
                    category="award",
                    anchor_text=anchor,
                    domain="general",
                    raw_text=full_lead,
                )
            )

    # Fallback origins from profile fields
    if profile.birth_place:
        anchor = f"Born {profile.birth_date + ' in ' if profile.birth_date else 'in '}{profile.birth_place}".strip()
        events.append(
            LifeEvent(
                category="ancestry",
                anchor_text=anchor,
                domain="general",
                date_context=profile.birth_date,
                raw_text=profile.birth_place,
            )
        )
    if profile.affiliation and not any(e.category == "service_entry" for e in events):
        anchor = f"Appointed at {profile.affiliation}".strip()
        events.append(
            LifeEvent(
                category="service_entry",
                anchor_text=anchor,
                domain="service_entry",
                raw_text=profile.affiliation,
            )
        )

    context.life_events = events
    return context


def generate_pivot_id() -> str:
    return f"piv-{uuid.uuid4().hex[:8]}"


def generate_lead_id() -> str:
    return f"lead-{uuid.uuid4().hex[:8]}"


def generate_inquiry_id() -> str:
    return f"inq-{uuid.uuid4().hex[:8]}"


def seed_default_pivots(profile: PersonProfile) -> list[InvestigationPivot]:
    """Inspect profile attributes (affiliation, field, known_for) and seed initial pivots."""
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_titles = {p.title.lower() for p in profile.investigation_pivots}
    new_pivots: list[InvestigationPivot] = []
    context = build_subject_context(profile)

    # 1. Institutional Pivot
    if profile.affiliation:
        affil_clean = profile.affiliation.strip()
        if affil_clean.lower() not in existing_titles:
            piv = InvestigationPivot(
                pivot_id=generate_pivot_id(),
                pivot_type="institution",
                title=affil_clean,
                description=f"Primary research/workplace institution for {profile.name}",
                created_by="system",
                created_at=now_iso,
            )
            if context.city:
                piv.location = context.city
            elif context.state:
                piv.location = context.state
            new_pivots.append(piv)
            existing_titles.add(affil_clean.lower())

    # 2. Project / Landmark Breakthrough Pivot
    if profile.known_for:
        kf_clean = profile.known_for.strip()
        if kf_clean.lower() not in existing_titles:
            new_pivots.append(
                InvestigationPivot(
                    pivot_id=generate_pivot_id(),
                    pivot_type="project_grant",
                    title=kf_clean,
                    description=f"Key research project or landmark achievement attributed to {profile.name}",
                    created_by="system",
                    created_at=now_iso,
                )
            )
            existing_titles.add(kf_clean.lower())

    # 3. Spatial / Residential Campus Pivot (plain derived geography)
    loc_found = None
    for p in new_pivots:
        if p.location:
            loc_found = p.location
            break
    if not loc_found:
        if context.city and context.state:
            loc_found = f"{context.city}, {context.state}"
        elif context.city:
            loc_found = context.city
        elif context.district and context.state:
            loc_found = f"{context.district}, {context.state}"
        elif context.state:
            loc_found = context.state

    if loc_found and "residential & campus footprint" not in existing_titles:
        new_pivots.append(
            InvestigationPivot(
                pivot_id=generate_pivot_id(),
                pivot_type="location",
                title=f"Residential & Campus Footprint ({loc_found})",
                description=f"Staff quarters, campus housing, municipal ward electoral rolls in {loc_found}",
                location=loc_found,
                created_by="system",
                created_at=now_iso,
            )
        )
        existing_titles.add("residential & campus footprint")

    # 4. Administrative & Recruited Fellows Pivot
    if "project fellows & recruited personnel" not in existing_titles:
        new_pivots.append(
            InvestigationPivot(
                pivot_id=generate_pivot_id(),
                pivot_type="associate",
                title="Project Fellows & Recruited Personnel",
                description="Senior/Junior Research Fellows (SRF/JRF) and Research Associates hired on project stipends whose dissertations acknowledge the lab",
                created_by="system",
                created_at=now_iso,
            )
        )
        existing_titles.add("project fellows & recruited personnel")

    return new_pivots


def generate_forensic_queries_for_pivot(
    pivot: InvestigationPivot, subject_name: str
) -> list[dict[str, str]]:
    """Generate specialized multi-hop OSINT search queries for an investigation pivot."""
    queries: list[dict[str, str]] = []
    p_title = pivot.title.replace('"', "")
    s_name = subject_name.replace('"', "")
    last_name = s_name.split()[-1] if len(s_name.split()) > 1 else s_name

    if pivot.pivot_type in ("project_grant", "institution"):
        # A. Shodhganga Theses
        queries.append(
            {
                "category": "thesis_dissertation",
                "title": f"Shodhganga Doctoral Theses: {p_title}",
                "query": f'site:shodhganga.inflibnet.ac.in "{p_title}" OR ("{s_name}" guide OR supervisor)',
                "rationale": "Student dissertations contain raw lab logbooks, exact experiment dates, and acknowledge lab personnel.",
            }
        )
        # B. Grants & Sanction Orders
        queries.append(
            {
                "category": "grant_sanction",
                "title": f"Grant Sanctions & Budgets: {p_title}",
                "query": f'"{p_title}" "sanction" OR "grant" OR "project code" OR "budget" filetype:pdf',
                "rationale": "Uncovers the funding agency, official grant code, budget, and project duration.",
            }
        )
        # C. Recruitment & Fellow Notices
        queries.append(
            {
                "category": "recruitment_notice",
                "title": f"Walk-in-Interviews & Recruited Fellows: {p_title}",
                "query": f'"{p_title}" "walk-in-interview" OR "Senior Research Fellow" OR "SRF" OR "JRF" filetype:pdf',
                "rationale": "Recruitment notifications prove project activity and identify the junior researchers working at the bench.",
            }
        )
        # D. Annual Reports & Division Rosters
        queries.append(
            {
                "category": "annual_report",
                "title": f"Institutional Annual Reports: {p_title}",
                "query": f'"{p_title}" "Annual Report" OR "staff list" filetype:pdf',
                "rationale": "Institute annual reports list ongoing research schemes, publications, and verified staff designations.",
            }
        )

    if pivot.pivot_type in ("location", "family_social"):
        loc = pivot.location or ""
        loc_term = f'"{loc}" ' if loc else ""
        # E. Residential & Electoral Footprint
        queries.append(
            {
                "category": "electoral_gazette",
                "title": f"Municipal & Campus Housing Footprint: {loc}".strip(": "),
                "query": f'"{s_name}" {loc_term}"quarter" OR "colony" OR "electoral roll" OR "voter list"'.strip(),
                "rationale": "Confirms residential dates, campus quarter numbers, and household relationships to rule out namesakes.",
            }
        )
        # F. Campus Schooling & Local Societies
        queries.append(
            {
                "category": "general_lead",
                "title": f"Campus Schools & Local Societies: {loc}".strip(": "),
                "query": f'"{last_name}" {loc_term}"Campus School" OR "school" OR "housing society"'.strip(),
                "rationale": "Uncovers school-going children and local civic society footprint during the tenure.",
            }
        )

    if pivot.pivot_type in ("associate", "institution", "gazette_legal"):
        # G. Tribunal & Legal Orders (IndianKanoon)
        queries.append(
            {
                "category": "legal_tribunal",
                "title": f"CAT & High Court Orders: {p_title}",
                "query": f'site:indiankanoon.org "{p_title}" "{s_name}"',
                "rationale": "Central Administrative Tribunal filings contain exact civil service dates, seniority lists, and appointment orders.",
            }
        )

    return queries


def check_subject_mention(text: str, profile_name: str) -> bool:
    """Check if the provided text directly contains the subject's name or common initials."""
    if not text or not profile_name:
        return False
    t_lower = text.lower()
    name_lower = profile_name.lower()
    if name_lower in t_lower:
        return True
    # Check initials variant (e.g. "Prem Singh Yadav" -> "p.s. yadav" or "p s yadav" or "p. s. yadav")
    parts = profile_name.split()
    if len(parts) >= 2:
        last = parts[-1].lower()
        initials = "".join([p[0].lower() for p in parts[:-1]])
        if f"{initials} {last}" in t_lower or f"{'.'.join(initials)} {last}" in t_lower:
            return True
        first_initial = parts[0][0].lower()
        if (
            f"{first_initial}. {last}" in t_lower
            or f"{first_initial} {last}" in t_lower
        ):
            return True
    return False


def build_forensic_sweep_leads(
    profile: PersonProfile, pivot: InvestigationPivot
) -> list[AuxiliaryLead]:
    """Create preliminary lead objects based on forensic queries for a pivot."""
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_queries = generate_forensic_queries_for_pivot(pivot, profile.name)
    leads: list[AuxiliaryLead] = []

    for q in raw_queries:
        mention = check_subject_mention(
            f"{q['title']} {q['query']} {q['rationale']}", profile.name
        )
        leads.append(
            AuxiliaryLead(
                lead_id=generate_lead_id(),
                pivot_id=pivot.pivot_id,
                title=q["title"],
                category=q["category"],
                lead_notes=q["rationale"],
                automated_query=q["query"],
                actor_logged="system",
                status="lead",
                has_subject_mention=mention,
                created_at=now_iso,
            )
        )

    return leads


def _enrich_inquiry_dual_track(
    inq: ForensicInquiry, context: SubjectContext | None = None
) -> None:
    """Populates statutory custodian, physical room/archive location, and offline retrieval methods."""
    inq.offline_archive_flag = True
    if not inq.online_probe_status or inq.online_probe_status == "open":
        if inq.corroborating_links:
            inq.online_probe_status = "confirmed"
        elif inq.status == "probed":
            inq.online_probe_status = "probed"
        else:
            inq.online_probe_status = "open"

    inst = (
        context.primary_institution if context else ""
    ) or "University / Institutional Headquarters"
    geo = (
        context.city or context.district or context.state if context else ""
    ) or "Regional Headquarters"

    domain = (inq.domain or "").lower()
    anchor_lower = (inq.fact_anchor or "").lower()

    if (
        domain in ("academic_degree", "doctoral_thesis")
        or "degree" in anchor_lower
        or "ph.d" in anchor_lower
        or "dissertation" in anchor_lower
        or "thesis" in anchor_lower
        or "convocation" in anchor_lower
        or "b.sc" in anchor_lower
        or "m.sc" in anchor_lower
    ):
        inq.offline_archive_location = f"Academic Branch Record Room & Central Library Historical Theses Archive, {inst}"
        inq.offline_custodian = (
            "Registrar (Academic & Examinations) & University Librarian"
        )
        inq.offline_retrieval_method = "Formal degree verification request; convocation degree register folio inspection; or RTI Act 2005 Sec 6(1) to SPIO for Tabulation Register (TR) excerpt."
    elif (
        domain == "superannuation"
        or "retir" in anchor_lower
        or "superannuat" in anchor_lower
        or "farewell" in anchor_lower
    ):
        inq.offline_archive_location = f"Establishment & Pension Cell, {inst}"
        inq.offline_custodian = "Drawing and Disbursing Officer (DDO) & Head of Office"
        inq.offline_retrieval_method = "Official Relinquishment of Charge & Superannuation Office Order; Pension Payment Order (PPO) records."
    elif (
        domain == "research_grant"
        or "grant" in anchor_lower
        or "sanction" in anchor_lower
        or "project" in anchor_lower
        or "fund" in anchor_lower
        or "fellowship" in anchor_lower
        or "associateship" in anchor_lower
        or "deputation" in anchor_lower
    ):
        inq.offline_archive_location = f"Extramural Research Secretariat & Institutional Finance/Project Cell, {inst}"
        inq.offline_custodian = (
            "Funding Agency Section Officer / Head of Research Division"
        )
        inq.offline_retrieval_method = "Grant Sanction Order & Utilization Certificate verification; or RTI Act 2005 to funding agency CPIO."
    elif (
        domain == "service_entry"
        or "scientist" in anchor_lower
        or "joining" in anchor_lower
        or "joined" in anchor_lower
        or "appointed" in anchor_lower
        or "appointment" in anchor_lower
        or "ars" in anchor_lower
        or "head" in anchor_lower
    ):
        inq.offline_archive_location = (
            f"Establishment Section & Administrative Record Room, {inst}"
        )
        inq.offline_custodian = (
            "Head of Office / Senior Administrative Officer (Establishment)"
        )
        inq.offline_retrieval_method = "Service Book (Part-I) inspection, joining verification order, or RTI Sec 6(1) to CPIO for cadre seniority and gazetted appointment records."
    elif (
        domain == "campus_quarters"
        or "quarters" in anchor_lower
        or "housing" in anchor_lower
        or "resided" in anchor_lower
    ):
        inq.offline_archive_location = (
            f"Estate Section & Housing Allotment Committee, {inst}"
        )
        inq.offline_custodian = "Estate Officer / Chairman, House Allotment Committee"
        inq.offline_retrieval_method = "Staff Quarter Allotment Roster, License Fee deduction register in Service Book, or local Municipal Corporation utility files."
    elif (
        domain == "civic_electoral"
        or "electoral" in anchor_lower
        or "voter" in anchor_lower
    ):
        inq.offline_archive_location = f"District Election Office & Tehsildar (Election) Record Room, Mini Secretariat, {geo}"
        inq.offline_custodian = f"District Election Officer (Deputy Commissioner) & Tehsildar (Election), {geo}"
        inq.offline_retrieval_method = "Inspection of Historical Electoral Rolls in District Election Archives; or RTI Act 2005 Sec 6(1) to SPIO Office of Chief Electoral Officer."
    elif domain == "utility_electricity" or "electricity" in anchor_lower:
        inq.offline_archive_location = (
            f"Sub-Divisional Office (Operations), Electricity Utility Discom, {geo}"
        )
        inq.offline_custodian = (
            f"Sub-Divisional Officer (Operations) & Executive Engineer, {geo}"
        )
        inq.offline_retrieval_method = "Inspection of Consumer Service Ledger at local Sub-Division; or RTI Sec 6(1) to Discom SPIO."
    elif domain == "gazette_official" or "gazette of india" in anchor_lower:
        inq.offline_archive_location = (
            "National Archives of India, New Delhi & Central Secretariat Library"
        )
        inq.offline_custodian = "Director General of Archives, National Archives of India & Controller of Publications"
        inq.offline_retrieval_method = "Archival research in National Archives Gazette Collection; or online search on e-Gazette portal."
    elif (
        "born" in anchor_lower
        or "birth" in anchor_lower
        or "village" in anchor_lower
        or "ancestral" in anchor_lower
    ):
        inq.offline_archive_location = f"Tehsil & District Record Room, Mini Secretariat {geo} & Gram Panchayat / Municipality Office"
        inq.offline_custodian = (
            "Tehsildar / District Revenue Officer & Gram Sachiv / Municipal Registrar"
        )
        inq.offline_retrieval_method = "Physical Application for Certified Copy of Jamabandi / revenue records; or Family Register (Parivar Register) inspection."
    elif (
        "award" in anchor_lower
        or "record" in anchor_lower
        or "citation" in anchor_lower
        or "honor" in anchor_lower
    ):
        inq.offline_archive_location = f"National / Institutional Awards Secretariat & Central Library Historical Archives, {inst}"
        inq.offline_custodian = "Secretary (Coordination & Awards) & Chief Librarian"
        inq.offline_retrieval_method = "Public inspection of Foundation Day Annual Citation Volumes; or Record Verification Query to awarding body archives."
    else:
        inq.offline_archive_location = (
            f"Institutional Record Room & Central Library Historical Archives, {inst}"
        )
        inq.offline_custodian = (
            "Head of Office / Registrar / Public Information Officer"
        )
        inq.offline_retrieval_method = "Right to Information (RTI) Act 2005 application or certified archival document request."


def generate_deductive_inquiries(profile: PersonProfile) -> list[ForensicInquiry]:
    """Generate deductive 'If True, What Must Exist?' hypotheses based on established biographical facts.

    For any verified or alleged life-milestone (degree, tenure, grant, retirement),
    this generates the required institutional paper trail that must exist in public/archival records.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_anchors = {inq.fact_anchor.lower() for inq in profile.forensic_inquiries}
    new_inquiries: list[ForensicInquiry] = []
    s_name = profile.name
    last_name = s_name.split()[-1] if s_name.split() else s_name
    context = build_subject_context(profile)

    category_order = [
        "education",
        "phd",
        "service_entry",
        "grant",
        "superannuation",
        "deputation",
        "award",
        "ancestry",
        "residence",
    ]

    events_by_category: dict[str, list[LifeEvent]] = {}
    for ev in context.life_events:
        events_by_category.setdefault(ev.category, []).append(ev)

    inst_name = context.primary_institution or "University / Research Institution"
    state_name = context.state or ""

    for cat in category_order:
        matching_events = events_by_category.get(cat, [])
        if not matching_events:
            continue
        sorted_events = sorted(
            matching_events,
            key=lambda e: (bool(e.date_context), len(e.anchor_text)),
            reverse=True,
        )
        best_event = next(
            (
                ev
                for ev in sorted_events
                if ev.anchor_text.lower() not in existing_anchors
            ),
            None,
        )
        if not best_event:
            continue
        anchor = best_event.anchor_text

        inq: ForensicInquiry | None = None
        anchor_snippet = anchor[:90] + ("..." if len(anchor) > 90 else "")

        if cat == "education":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="academic_degree",
                deductive_question=f"If {s_name} completed academic degrees ({anchor_snippet}), what convocation registers, student records, and exam gazettes must exist?",
                expected_paper_trails=[
                    f"Annual Convocation Degree Recipient Register at {inst_name}",
                    "University Historical Student Archive & Tabulation Register (TR)",
                    f"{state_name + ' ' if state_name else ''}Government Gazette: Higher Education Examination Notifications",
                    "KrishiKosh / National Academic Thesis & Student Archive",
                ],
                probe_queries=[
                    f'site:krishikosh.egranth.ac.in "{s_name}" OR "{last_name}"'
                    if context.is_indian
                    else f'"{s_name}" "convocation" OR "degree"',
                    f'"{inst_name}" "{s_name}" convocation OR alumni OR degree',
                    f'"{state_name} Gazette" "{s_name}" examination OR degree'
                    if state_name
                    else f'"{s_name}" "degree" "convocation"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "phd":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="doctoral_thesis",
                deductive_question=f"If {s_name} completed a doctoral degree ({anchor_snippet}), what mandatory dissertation filings and faculty records must exist?",
                expected_paper_trails=[
                    f"Hardbound Ph.D. Thesis Deposit at {inst_name} Central Library",
                    "Shodhganga / National Doctoral Thesis Database (Title & Accession Number)",
                    "Doctoral Advisory Committee Records (Major Advisor, Co-Guides, External Examiners)",
                    "Doctoral Viva Voce Notification and Degree Conferment Gazette",
                ],
                probe_queries=[
                    f'site:shodhganga.inflibnet.ac.in "{s_name}" OR "{last_name}"'
                    if context.is_indian
                    else f'"{s_name}" thesis OR dissertation',
                    f'"{inst_name}" "{last_name}" thesis OR dissertation',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "service_entry":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="service_entry",
                deductive_question=f"If {s_name} held official appointments ({anchor_snippet}), what statutory gazette notifications, recruitment orders, and seniority lists must exist?",
                expected_paper_trails=[
                    "Public Service / Scientific Recruitment Board Selection List & Notification",
                    "Statutory Government Gazette (Class-I / Scientific Cadre Appointments)",
                    f"Official Cadre Seniority List at {inst_name}",
                    "Service Book Record (Part-I) & Joining Verification Order",
                ],
                probe_queries=[
                    f'site:egazette.gov.in "{s_name}" OR "{last_name}"'
                    if context.is_indian
                    else f'"{s_name}" "appointment" OR "gazette"',
                    f'"{inst_name}" "{s_name}" appointment OR selection OR seniority',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "grant":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="research_grant",
                deductive_question=f"If {s_name} was awarded research grants or headed extramural schemes ({anchor_snippet}), where are the audited public disclosures and sanction orders?",
                expected_paper_trails=[
                    "Funding Agency Project Sanction Order & Audited Utilization Certificate",
                    "Public Advertisements for Project Fellow (JRF/SRF/RA) Recruitment",
                    "Institutional Annual Report Extramural Biotechnology / Project Disclosures",
                    "Institutional Ethics and Research Review Approvals",
                ],
                probe_queries=[
                    f'"{s_name}" "sanction" OR "grant" OR "project" filetype:pdf',
                    f'"{inst_name}" "{s_name}" sanction OR grant',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "superannuation":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="superannuation",
                deductive_question=f"If {s_name} superannuated ({anchor_snippet}), what official retirement orders and pension notifications exist?",
                expected_paper_trails=[
                    f"Official Relinquishment of Charge & Superannuation Office Order at {inst_name}",
                    "Central Pension Accounting Office (CPAO) / Pension Sanction Order",
                    "Institutional Newsletter Farewell & Valedictory Felicitation Proceedings",
                ],
                probe_queries=[
                    f'"{s_name}" "superannuation" OR "retired" OR "farewell"',
                    f'"{inst_name}" "{last_name}" retired OR superannuation',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "deputation":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="research_grant",
                deductive_question=f"If {s_name} completed overseas research or deputations ({anchor_snippet}), what ministerial sanction orders and host institute records exist?",
                expected_paper_trails=[
                    "Government Cadre Clearance & Relieving Office Order for Foreign Deputation",
                    "Host Institute Annual Report & Visiting Scholar Registry",
                    "Fellowship Sanction Order and Final Research Report",
                ],
                probe_queries=[
                    f'"{s_name}" fellowship OR deputation OR associateship',
                    f'"{last_name}" "{inst_name}" fellowship',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "award":
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="general",
                deductive_question=f"If {s_name} was conferred honors or awards ({anchor_snippet}), what official citation booklets and verification certificates exist?",
                expected_paper_trails=[
                    "Official Annual Award Citation Booklet & Ceremony Proceedings",
                    "National / Society Registry Certificate of Achievement",
                    "Institutional Cash Prize Disbursement Voucher & Felicitation Minutes",
                ],
                probe_queries=[
                    f'"{s_name}" award OR citation OR honor OR medal',
                    f'"{s_name}" "{last_name}" award',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "ancestry":
            geo_name = (
                context.village
                or context.city
                or context.district
                or context.state
                or "domicile"
            )
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="general",
                deductive_question=f"If {s_name} originated from ({anchor_snippet}), what civil registers, matriculation gazettes, and land records must exist?",
                expected_paper_trails=[
                    f"Gram Panchayat / Municipal Birth & Family Register in {geo_name}",
                    "State Board of School Education Matriculation Examination Gazette",
                    f"Department of Revenue Land Records (Jamabandi / Intiqal) in {geo_name}",
                    f"Assembly Constituency Electoral Roll at Local Polling Station in {geo_name}",
                ],
                probe_queries=[
                    f'"{s_name}" "{geo_name}"',
                    f'"{state_name} Gazette" "{s_name}" matriculation OR school'
                    if state_name
                    else f'"{s_name}" matriculation OR school',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )
        elif cat == "residence":
            geo_name = (
                context.city or context.district or context.state or "campus premises"
            )
            inq = ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="campus_quarters",
                deductive_question=f"If {s_name} resided at ({anchor_snippet}), which civil and municipal registers must document their presence?",
                expected_paper_trails=[
                    f"Institutional Staff Housing Allotment Committee Minutes at {inst_name}",
                    "Chief Electoral Officer (CEO) Assembly Constituency Electoral Roll",
                    f"Municipal Water Supply & Civic Utility Records in {geo_name}",
                ],
                probe_queries=[
                    f'"{s_name}" "{geo_name}" quarters OR allotment',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            )

        if inq:
            new_inquiries.append(inq)
            existing_anchors.add(anchor.lower())

    for inq in profile.forensic_inquiries:
        _enrich_inquiry_dual_track(inq, context)

    for inq in new_inquiries:
        _enrich_inquiry_dual_track(inq, context)

    return new_inquiries
