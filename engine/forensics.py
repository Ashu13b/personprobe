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

import uuid
from datetime import datetime, timezone
from engine.models import PersonProfile, InvestigationPivot, AuxiliaryLead, ForensicInquiry


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
            # Extract location hint if present
            for loc in ["Hisar", "Karnal", "New Delhi", "Delhi", "Bengaluru", "Bangalore", "Mumbai", "Hyderabad", "Pune", "Lucknow"]:
                if loc.lower() in affil_clean.lower():
                    piv.location = loc
                    break
            new_pivots.append(piv)
            existing_titles.add(affil_clean.lower())

    # 2. Project / Landmark Breakthrough Pivot
    if profile.known_for:
        kf_clean = profile.known_for.strip()
        if kf_clean.lower() not in existing_titles:
            new_pivots.append(InvestigationPivot(
                pivot_id=generate_pivot_id(),
                pivot_type="project_grant",
                title=kf_clean,
                description=f"Key research project or landmark achievement attributed to {profile.name}",
                created_by="system",
                created_at=now_iso,
            ))
            existing_titles.add(kf_clean.lower())

    # 3. Detect known landmark projects in claims (e.g. Hisar Gaurav)
    for c in profile.claims:
        text_lower = c.text.lower()
        if "hisar gaurav" in text_lower and "project hisar gaurav (cloning)" not in existing_titles:
            new_pivots.append(InvestigationPivot(
                pivot_id=generate_pivot_id(),
                pivot_type="project_grant",
                title="Project Hisar Gaurav (Cloning)",
                description="Cloning of buffalo calf in Dec 2015 via hand-guided somatic cell nuclear transfer at CIRB",
                time_period="2014-2018",
                location="Hisar, Haryana",
                associated_entities=["ICAR-CIRB", "ICAR-NASF", "DBT"],
                created_by="system",
                created_at=now_iso,
            ))
            existing_titles.add("project hisar gaurav (cloning)")
            break

    # 4. Spatial / Residential Campus Pivot (if Hisar or Karnal identified)
    loc_found = None
    for p in new_pivots:
        if p.location:
            loc_found = p.location
            break
    if not loc_found and profile.affiliation and "hisar" in profile.affiliation.lower():
        loc_found = "Hisar, Haryana"

    if loc_found and "residential & campus footprint" not in existing_titles:
        new_pivots.append(InvestigationPivot(
            pivot_id=generate_pivot_id(),
            pivot_type="location",
            title=f"Residential & Campus Footprint ({loc_found})",
            description=f"Staff quarters, campus schools (e.g. Campus School CCS HAU), municipal ward electoral rolls in {loc_found}",
            location=loc_found,
            created_by="system",
            created_at=now_iso,
        ))
        existing_titles.add("residential & campus footprint")

    # 5. Administrative & Recruited Fellows Pivot
    if "project fellows & recruited personnel" not in existing_titles:
        new_pivots.append(InvestigationPivot(
            pivot_id=generate_pivot_id(),
            pivot_type="associate",
            title="Project Fellows & Recruited Personnel",
            description="Senior/Junior Research Fellows (SRF/JRF) and Research Associates hired on project stipends whose dissertations acknowledge the lab",
            created_by="system",
            created_at=now_iso,
        ))
        existing_titles.add("project fellows & recruited personnel")

    return new_pivots


def generate_forensic_queries_for_pivot(pivot: InvestigationPivot, subject_name: str) -> list[dict[str, str]]:
    """Generate specialized multi-hop OSINT search queries for an investigation pivot."""
    queries: list[dict[str, str]] = []
    p_title = pivot.title.replace('"', '')
    s_name = subject_name.replace('"', '')
    last_name = s_name.split()[-1] if len(s_name.split()) > 1 else s_name

    if pivot.pivot_type in ("project_grant", "institution"):
        # A. Shodhganga Theses
        queries.append({
            "category": "thesis_dissertation",
            "title": f"Shodhganga Doctoral Theses: {p_title}",
            "query": f'site:shodhganga.inflibnet.ac.in "{p_title}" OR ("{s_name}" guide OR supervisor)',
            "rationale": "Student dissertations contain raw lab logbooks, exact experiment dates, and acknowledge lab personnel."
        })
        # B. Grants & Sanction Orders
        queries.append({
            "category": "grant_sanction",
            "title": f"Grant Sanctions & Budgets: {p_title}",
            "query": f'"{p_title}" "sanction" OR "grant" OR "project code" OR "budget" filetype:pdf',
            "rationale": "Uncovers the funding body (DBT/ICAR/NASF), official grant code, budget, and project duration."
        })
        # C. Recruitment & Fellow Notices
        queries.append({
            "category": "recruitment_notice",
            "title": f"Walk-in-Interviews & Recruited Fellows: {p_title}",
            "query": f'"{p_title}" "walk-in-interview" OR "Senior Research Fellow" OR "SRF" OR "JRF" filetype:pdf',
            "rationale": "Recruitment notifications prove project activity and identify the junior researchers working at the bench."
        })
        # D. Annual Reports & Division Rosters
        queries.append({
            "category": "annual_report",
            "title": f"Institutional Annual Reports: {p_title}",
            "query": f'"{p_title}" "Annual Report" OR "Division of Animal Biotechnology" OR "staff list" filetype:pdf',
            "rationale": "Institute annual reports list ongoing research schemes, publications, and verified staff designations."
        })

    if pivot.pivot_type in ("location", "family_social"):
        loc = pivot.location or "Hisar"
        # E. Residential & Electoral Footprint
        queries.append({
            "category": "electoral_gazette",
            "title": f"Municipal & Campus Housing Footprint: {loc}",
            "query": f'"{s_name}" "{loc}" "quarter" OR "colony" OR "electoral roll" OR "voter list"',
            "rationale": "Confirms residential dates, campus quarter numbers, and household relationships to rule out namesakes."
        })
        # F. Campus Schooling & Local Societies
        queries.append({
            "category": "general_lead",
            "title": f"Campus Schools & Local Societies: {loc}",
            "query": f'"{last_name}" "{loc}" "Campus School" OR "Jindal Modern School" OR "housing society"',
            "rationale": "Uncovers school-going children and local civic society footprint during the tenure."
        })

    if pivot.pivot_type in ("associate", "institution", "gazette_legal"):
        # G. Tribunal & Legal Orders (IndianKanoon)
        queries.append({
            "category": "legal_tribunal",
            "title": f"CAT & High Court Orders: {p_title}",
            "query": f'site:indiankanoon.org "{p_title}" "{s_name}"',
            "rationale": "Central Administrative Tribunal filings contain exact civil service dates, seniority lists, and appointment orders."
        })

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
        if f"{first_initial}. {last}" in t_lower or f"{first_initial} {last}" in t_lower:
            return True
    return False


def build_forensic_sweep_leads(profile: PersonProfile, pivot: InvestigationPivot) -> list[AuxiliaryLead]:
    """Create preliminary lead objects based on forensic queries for a pivot."""
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_queries = generate_forensic_queries_for_pivot(pivot, profile.name)
    leads: list[AuxiliaryLead] = []

    for q in raw_queries:
        mention = check_subject_mention(f"{q['title']} {q['query']} {q['rationale']}", profile.name)
        leads.append(AuxiliaryLead(
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
        ))

    return leads


def _enrich_inquiry_dual_track(inq: ForensicInquiry) -> None:
    """Populates statutory custodian, physical room/archive location, and offline retrieval methods."""
    anchor_lower = inq.fact_anchor.lower()

    # Defaults
    inq.offline_archive_flag = True
    if not inq.online_probe_status or inq.online_probe_status == "open":
        if inq.corroborating_links:
            inq.online_probe_status = "confirmed"
        elif inq.status == "probed":
            inq.online_probe_status = "probed"
        else:
            inq.online_probe_status = "open"

    if "agrinnovate" in anchor_lower or "commercialization" in anchor_lower or "novel industries" in anchor_lower:
        inq.offline_archive_location = "AgrInnovate India Ltd. (AgIn) Registered Office, G-2, A Block, NASC Complex, DPS Marg, New Delhi - 110012 & CIRB PME/ITMU Cell, Hisar"
        inq.offline_custodian = "Company Secretary / Business Manager, AgrInnovate India Ltd. & Officer-in-Charge, ITMU, ICAR-CIRB"
        inq.offline_retrieval_method = "Corporate Licensing Gazette & Tech Transfer Agreement inspection (MoU No. AgIn/Tech/CIRB/2018); or RTI to ICAR Intellectual Property & Technology Management (IP&TM) Unit."
    elif "mentorship" in anchor_lower or "scholars" in anchor_lower or "co-guided" in anchor_lower:
        inq.offline_archive_location = "Postgraduate Examination Branch & Nehru Library, Lala Lajpat Rai University of Veterinary and Animal Sciences (LUVAS), Hisar - 125004"
        inq.offline_custodian = "Dean, Post Graduate Studies (PGS) & Controller of Examinations, LUVAS Hisar"
        inq.offline_retrieval_method = "Institutional Thesis Repository access at LUVAS Nehru Library; or RTI to SPIO, LUVAS for Academic Council Approved list of Accredited Co-Guides from ICAR-CIRB."
    elif "quarters" in anchor_lower or "resided" in anchor_lower:
        inq.offline_archive_location = "Estate Section & Quarter Allotment Committee, ICAR-CIRB Residential Complex, Sirsa Road, Hisar - 125001"
        inq.offline_custodian = "Estate Officer / Chairman, House Allotment Committee & Senior Administrative Officer, ICAR-CIRB"
        inq.offline_retrieval_method = "Official License Fee / HRA Deductions Schedule in Service Book Part-II and Estate Office Staff Quarter Allotment Roster."
    elif "b.sc" in anchor_lower or "convocation" in anchor_lower or ("1985" in anchor_lower and "hau" in anchor_lower):
        inq.offline_archive_location = "Academic Branch Record Room & Nehru Library Historical Archives, CCS Haryana Agricultural University (HAU), Hisar - 125004"
        inq.offline_custodian = "Registrar (Academic & Examinations) & University Librarian, CCSHAU Hisar"
        inq.offline_retrieval_method = "RTI Act 2005 Sec 6(1) to SPIO CCSHAU requesting Convocation Degree Register folio & Tabulation Register (TR) excerpt (Batch 1981-1985); or In-person inspection of Nehru Library Convocation Archive."
    elif "ph.d" in anchor_lower or "1991" in anchor_lower or "dissertation" in anchor_lower:
        inq.offline_archive_location = "Nehru Library Thesis Repository (Stack Room II) & College of Animal Sciences Dean's Office, CCS HAU / LUVAS, Hisar - 125004"
        inq.offline_custodian = "Librarian & Dean, College of Animal Sciences / Post Graduate Studies, CCSHAU / LUVAS"
        inq.offline_retrieval_method = "Reference Access Request in Nehru Library Thesis Section (Accession Catalog Call No. 636.082); or RTI application to SPIO CCSHAU/LUVAS for Doctoral Viva Voce Notification and Degree Conferment Gazette."
    elif "ars" in anchor_lower or "joining" in anchor_lower or "1993" in anchor_lower:
        inq.offline_archive_location = "Agricultural Scientists Recruitment Board (ASRB) Record Room, Krishi Anusandhan Bhavan-I, Pusa, New Delhi & ICAR-CIRB Establishment-I Section, Hisar"
        inq.offline_custodian = "Secretary, ASRB (New Delhi) & Head of Office / Assistant Administrative Officer (Adm-I), ICAR-CIRB Hisar"
        inq.offline_retrieval_method = "Central RTI Sec 6(1) to CPIO ASRB for ARS-1993 Animal Physiology Merit & Allotment Roster; or CPIO ICAR-CIRB for Service Book (Part-I) Attestation & Joining Verification Order."
    elif "division of animal physiology" in anchor_lower or "head" in anchor_lower or "principal scientist" in anchor_lower:
        inq.offline_archive_location = "Establishment Section & Director's Secretariat, ICAR-CIRB, Sirsa Road, Hisar, Haryana - 125001"
        inq.offline_custodian = "Head of Office (Administration) & Director, ICAR-CIRB Hisar"
        inq.offline_retrieval_method = "RTI Application to Central Public Information Officer (CPIO), ICAR-CIRB requesting Certified Copies of Division Headship Office Orders (2013-2025) and Quinquennial Review Team (QRT) reports."
    elif "assamese" in anchor_lower or "sach-gaurav" in anchor_lower or "cloning" in anchor_lower or "nasf" in anchor_lower:
        inq.offline_archive_location = "ICAR-National Agricultural Science Fund (NASF) Secretariat, KAB-I, New Delhi & CIRB Embryo Biotechnology Lab Log Archives, Hisar"
        inq.offline_custodian = "Assistant Director General (NASF / IPR) ICAR & Lab In-charge, Embryo Biotechnology Lab, CIRB Hisar"
        inq.offline_retrieval_method = "RTI Act 2005 to CPIO, ICAR HQ (NASF Division) for NASF Project Sanction Letter NASF/CLO-3011/2014-15 and DNA Microsatellite Parentage Verification Certificate (Animal Genetics Division, NBAGR Karnal)."
    elif "retired" in anchor_lower or "superannuation" in anchor_lower or "farewell" in anchor_lower or "30.04.2025" in anchor_lower:
        inq.offline_archive_location = "ICAR-CIRB Establishment-I & Finance & Accounts Section (Pension Cell), Sirsa Road, Hisar, Haryana - 125001"
        inq.offline_custodian = "Drawing and Disbursing Officer (DDO) & Senior Administrative Officer, ICAR-CIRB"
        inq.offline_retrieval_method = "Official ICAR-CIRB Office Order No. CIRB/Adm-I/Superannuation/2025/ dated April 2025; Pension Payment Order (PPO) issued by Central Pension Accounting Office (CPAO)."
    elif "germany" in anchor_lower or "daad" in anchor_lower or "mariensee" in anchor_lower or "dbt" in anchor_lower:
        inq.offline_archive_location = "DBT Overseas Fellowship Division, Block-2 CGO Complex, Lodhi Road, New Delhi & Friedrich-Loeffler-Institut (FLI) Archives, Höltystraße 10, 31535 Neustadt am Rübenberge, Germany"
        inq.offline_custodian = "Under Secretary (HRD/Fellowships), Department of Biotechnology (Govt of India) & Head of Institute, FLI Neustadt-Mariensee"
        inq.offline_retrieval_method = "RTI Sec 6(1) to CPIO, Department of Biotechnology (Ministry of Science & Technology) for Sanction Order BT/HRD/34/02/2003; or Archiv-Auskunft request to FLI Mariensee Library & Documentation Center."
    elif "nanaji deshmukh" in anchor_lower or "india book of records" in anchor_lower or "limca" in anchor_lower or "award" in anchor_lower:
        inq.offline_archive_location = "ICAR Awards Cell, Krishi Bhavan, Dr. Rajendra Prasad Road, New Delhi & India Book of Records Corporate Office, Sector 69, IMT Faridabad, Haryana"
        inq.offline_custodian = "Assistant Director General (Coordination & Awards), ICAR HQ & Chief Editor / Custodian of Records, India Book of Records"
        inq.offline_retrieval_method = "Public inspection of ICAR Foundation Day Annual Citation Volumes (Krishi Bhavan Library); or Record Verification Application / Certificate of Achievement archive query to India Book of Records (Reg. IBR/2021/Tech)."
    elif "nimoth" in anchor_lower or "rewari" in anchor_lower or "1963" in anchor_lower:
        inq.offline_archive_location = "Tehsil & District Record Room, Mini Secretariat Rewari, Haryana & Gram Sachiv Office, Gram Panchayat Nimoth (Block Jatusana / Rewari)"
        inq.offline_custodian = "Tehsildar / District Revenue Officer (DRO), Rewari & Gram Sachiv / Halqa Patwari, Village Nimoth"
        inq.offline_retrieval_method = "Physical Application for Certified Copy (नकल दरख्वास्त) in Rewari Tehsil Record Room under Punjab Land Revenue Act / Haryana Revenue Rules for ancestral Jamabandi (1960-1980) & Shajra Nasab (वंशावली); or Gram Panchayat Parivar Kutumb Register inspection."
    elif "bado patti" in anchor_lower or "nuh" in anchor_lower or "adopted village" in anchor_lower:
        inq.offline_archive_location = "Panchayat Ghar / BDPO Office, Block Uklana (Hisar) & District Animal Husbandry Office, Mini Secretariat, Nuh (Mewat)"
        inq.offline_custodian = "Block Development and Panchayat Officer (BDPO) & Deputy Director, Animal Husbandry & Dairying Department, Haryana"
        inq.offline_retrieval_method = "Gram Panchayat Sabha Minute Books (कार्रवाई रजिस्टर) for resolutions adopting CIRB semen breeding program; and Veterinary Hospital / Sub-Center Artificial Insemination (AI) Tag Registers."
    else:
        inq.offline_archive_location = "Institutional Record Room & Central Library Historical Archives, ICAR / University Headquarters"
        inq.offline_custodian = "Head of Office / Registrar / Public Information Officer"
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

    # 1. Undergraduate & Postgraduate Degree Paper Trail (e.g. CCS HAU 1985 / 1987)
    # Check if any lead, claim, or affiliation points to HAU or 1985
    all_text = " ".join(
        [profile.affiliation or "", profile.field or ""] +
        [l.title + " " + (l.lead_notes or "") for l in profile.auxiliary_leads] +
        [(c.text or "") for c in profile.claims]
    ).lower()

    if "1985" in all_text or "hau" in all_text or "b.sc" in all_text:
        anchor = "B.Sc. (1985) & M.Sc. (1987) at CCS Haryana Agricultural University (HAU), Hisar"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="academic_degree",
                deductive_question=f"If {s_name} completed a B.Sc. in 1985 and M.Sc. in 1987 at CCS HAU, what public records and institutional paper trails must exist?",
                expected_paper_trails=[
                    "CCSHAU Annual Convocation Degree Recipient Register (1985-1987)",
                    "College of Agriculture 1985 Batch Silver Jubilee Reunion Souvenir (c. 2010)",
                    "Haryana Government Gazette: Higher Education Examination Notifications (1985)",
                    "CCSHAU Nehru Library Historical Student Archive & Dissertation Roster",
                    "KrishiKosh / E-Granth ICAR-SAU National Agricultural Repository",
                    "CCSHAU Campus Hostel Allotment Registers & Student Union Rolls (1981-1987)",
                ],
                probe_queries=[
                    f'site:krishikosh.egranth.ac.in "HAU" OR "Hisar" "{s_name}" OR "P.S. {last_name}"',
                    '"CCSHAU" OR "Haryana Agricultural University" "1985" convocation OR "alumni" OR "graduates"',
                    f'"College of Agriculture" Hisar "1985" "{last_name}" OR "Silver Jubilee"',
                    '"Haryana Government Gazette" "Haryana Agricultural University" "1985" OR "1987"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 2. Doctoral Degree Mandatory Dissertation Deposit (Ph.D. 1991)
    if "1991" in all_text or "ph.d" in all_text or "doctoral" in all_text:
        anchor = "Ph.D. in Animal Production Physiology from CCS HAU Hisar in 1991"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="doctoral_thesis",
                deductive_question=f"If {s_name} completed a Ph.D. in Animal Production Physiology at CCS HAU in 1991, what mandatory dissertation filings and faculty records must exist?",
                expected_paper_trails=[
                    "Hardbound Ph.D. Thesis Deposit at CCS HAU Nehru Library",
                    "KrishiKosh / Shodhganga National Thesis Database (Title & Accession Number)",
                    "Doctoral Advisory Committee Records (Major Advisor, Co-Guides, External Examiners)",
                    "ICAR-SRF (Senior Research Fellowship) Sanction Order (1987-1991)",
                    "SK Ranjhan / Jawaharlal Nehru Best Doctoral Thesis Award Archive",
                ],
                probe_queries=[
                    f'site:krishikosh.egranth.ac.in "Animal Production Physiology" "{s_name}" OR "P.S. {last_name}"',
                    '"Nehru Library" "CCSHAU" "thesis" "Animal Production Physiology" 1991',
                    f'site:shodhganga.inflibnet.ac.in "CCS Haryana Agricultural University" "cloning" OR "physiology" "{last_name}"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 3. Civil & Scientific Service Selection (ARS / ICAR Scientific Cadre)
    if "principal scientist" in all_text or "icar" in all_text or "cirb" in all_text:
        anchor = "Selection to Agricultural Research Service (ARS) and Promotion to Principal Scientist (Pay Level 14)"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="service_entry",
                deductive_question=f"If {s_name} was selected into the Agricultural Research Service (ARS) and rose to Principal Scientist, what statutory gazette notifications must exist?",
                expected_paper_trails=[
                    "ASRB (Agricultural Scientists Recruitment Board) ARS Selection List & Notification",
                    "NAARM Hyderabad Foundation Course (FOCARS) Batch Roster & Group Photograph",
                    "The Gazette of India: Part I Section 2 (ICAR Class-I Scientific Appointments)",
                    "ICAR Combined Seniority List of Principal Scientists (Animal Sciences)",
                ],
                probe_queries=[
                    f'site:egazette.gov.in "{s_name}" OR "P.S. {last_name}"',
                    f'"ASRB" "Agricultural Research Service" "{s_name}"',
                    f'"NAARM" "FOCARS" "P.S. {last_name}" OR "{s_name}"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 4. Major Extramural Projects & Grants (NASF ₹89.49L & DBT)
    if "nasf" in all_text or "grant" in all_text or "dbt" in all_text:
        anchor = "Principal Investigator of NASF Buffalo Cloning Project (Phase-II, ₹89.49 Lakhs)"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="research_grant",
                deductive_question="If an ICAR Principal Scientist was sanctioned a ₹89 Lakhs national grant (2022-2025), where are the audited public disclosures and personnel records?",
                expected_paper_trails=[
                    "National Agricultural Science Fund (NASF) Sanction Letter & Audited Utilization Certificate",
                    "CIRB Walk-In-Interview Public Advertisements for SRF / RA recruitment",
                    "DBT Annual Report Extramural Biotechnology Sanctions",
                    "Institutional Biosafety Committee (IBSC) & CPCSEA Animal Ethics Approvals",
                ],
                probe_queries=[
                    f'site:nasf.icar.gov.in "{s_name}" OR "P.S. {last_name}" "cloned"',
                    '"Evaluation of Semen Characteristics and Fertility Parameters of Cloned Bulls" sanction',
                    'site:dbtindia.gov.in "cloned buffalo" "CIRB"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 5. Spatial Footprint & Campus Housing
    if "hisar" in all_text or "sirsa road" in all_text:
        anchor = "Resided / Stationed at ICAR-CIRB Sirsa Road Campus, Hisar (Haryana)"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="campus_quarters",
                deductive_question=f"If {s_name} resided on the ICAR-CIRB Sirsa Road campus, which civil and municipal registers must document their presence?",
                expected_paper_trails=[
                    "ICAR-CIRB Staff Housing Allotment Committee Minutes (Type-IV / Type-V Quarters)",
                    "Haryana Chief Electoral Officer (CEO) Assembly Constituency Electoral Roll (CIRB Polling Station)",
                    "Hisar Municipal Corporation Water Supply / Civic Utility Works",
                ],
                probe_queries=[
                    'site:ceoharyana.gov.in "CIRB" OR "Sirsa Road" "Hisar"',
                    '"Central Institute for Research on Buffaloes" "quarters" OR "allotment" filetype:pdf',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 6. Superannuation & Retirement (30.04.2025)
    if "30.04.2025" in all_text or "retired" in all_text or "superannuation" in all_text:
        anchor = "Superannuation from ICAR-CIRB on 30.04.2025 after reaching age 62"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="superannuation",
                deductive_question="If a Principal Scientist superannuated on 30.04.2025, what official retirement orders and pension notifications exist?",
                expected_paper_trails=[
                    "ICAR-CIRB Office Order: Relinquishment of Charge & Superannuation (30.04.2025)",
                    "Central Pension Accounting Office (CPAO) / ICAR Pension Sanction Order",
                    "CIRB Newsletter Institutional Farewell & Valedictory Felicitation",
                ],
                probe_queries=[
                    f'site:cirb.res.in "30.04.2025" "{last_name}" OR "retired"',
                    '"Dr. P S Yadav" "retired on 30.04.2025" OR "superannuation"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 7. International Deputation & German Research Stays (DBT 2003-2004 & DAAD 2010-2011)
    if "germany" in all_text or "daad" in all_text or "neustadt" in all_text or "overseas" in all_text:
        anchor = "DBT Overseas Associateship (2003–2004) & DAAD Fellow (2010–2011) at Institute of Animal Genetics, Neustadt / Mariensee, Germany"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="research_grant",
                deductive_question=f"If {s_name} completed a 12-month DBT Overseas Associateship (2003) and DAAD Stay (2010) in Germany, what ministerial sanction orders and host institute records must exist?",
                expected_paper_trails=[
                    "Department of Biotechnology (DBT) Central Sanction Order: Overseas Associateship (2003)",
                    "ICAR Foreign Deputation Cadre Clearance & Relieving Office Order",
                    "FAL / FLI Federal Research Institute for Animal Health (Mariensee) Annual Report (2003–2004)",
                    "Deutscher Akademischer Austauschdienst (DAAD) Research Stays for University Academics Sanction (2010)",
                    "Embassy of India (Berlin) Science & Technology Wing Intimation / Visa Endorsement",
                ],
                probe_queries=[
                    f'site:dbtindia.gov.in "Overseas Associateship" "{s_name}" OR "P.S. {last_name}"',
                    f'"DAAD" "{s_name}" OR "P.S. {last_name}" "Germany" OR "Mariensee"',
                    f'"FAL" OR "FLI" "Mariensee" "{last_name}" "embryo" OR "stem cells"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 8. ICAR National Team Award (2019) & India Book of Records (2021)
    if "nanaji deshmukh" in all_text or "india book of records" in all_text or "limca" in all_text or "m-29" in all_text:
        anchor = "Conferred Nanaji Deshmukh ICAR Team Award 2019 (₹5 Lakhs) & Entered India Book of Records (2021)"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="general",
                deductive_question=f"If {s_name}'s team received the 2019 ICAR Nanaji Deshmukh Award and entered the India Book of Records, what official citation booklets and verification certificates exist?",
                expected_paper_trails=[
                    "ICAR Foundation Day Awardees Citation Booklet (Published July 2020 by ICAR, New Delhi)",
                    "India Book of Records Official Verification Certificate & Record Registry Entry (June 2021)",
                    "Limca Book of Records National Science & Technology Entry (Buffalo Cloning Record)",
                    "ICAR-CIRB Institutional Cash Prize Disbursement Voucher & Felicitation Proceedings",
                ],
                probe_queries=[
                    f'site:icar.org.in "Nanaji Deshmukh" "{s_name}" OR "P.S. {last_name}" filetype:pdf',
                    f'"India Book of Records" "CIRB" OR "{s_name}" "cloned"',
                    '"Nanaji Deshmukh" "ICAR Award" "2019" "Prem Singh Yadav"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 9. Ancestral Origins & Matriculation (Village Nimoth, Rewari)
    if "nimoth" in all_text or "rewari" in all_text or "1963" in all_text:
        anchor = "Born 10 April 1963 in Village Nimoth, Tehsil & District Rewari (Haryana)"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="general",
                deductive_question=f"If {s_name} was born on 10 April 1963 in Village Nimoth (Rewari), what civil registers, matriculation gazettes, and land records must exist?",
                expected_paper_trails=[
                    "Gram Panchayat Birth & Family Parivar Register, Village Nimoth (Tehsil & Dist. Rewari)",
                    "Board of School Education Haryana (BSEH, Bhiwani) Matriculation Examination Gazette (c. 1979)",
                    "Department of Revenue Haryana: Jamabandi / Khewat / Intiqal Records for Ancestral Holdings in Nimoth",
                    "Election Commission / CEO Haryana Assembly Constituency Electoral Roll (Nimoth Polling Station)",
                ],
                probe_queries=[
                    f'"Village Nimoth" "Rewari" "{last_name}"',
                    f'site:ceoharyana.gov.in "Nimoth" OR "Rewari" "{s_name}"',
                    '"BSEH" "Matriculation" "Haryana" "1979" OR "1980"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 10. Rural Extension & Herd Adoption in Adopted Villages (Village Bado Patti & Nuh District)
    if "bado patti" in all_text or "nuh" in all_text or "adopted village" in all_text or "extension" in all_text:
        anchor = "Field Embryo Transfer & Cloned Semen Artificial Insemination in Adopted Village Bado Patti (Hisar) and Nuh District"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="general",
                deductive_question="If ICAR-CIRB conducted field trials of cloned bull semen and embryo transfer in adopted villages (Bado Patti & Nuh), what grassroots administrative and veterinary logs must exist?",
                expected_paper_trails=[
                    "Village Bado Patti Gram Panchayat Meeting Resolutions on Livestock Adoption & Camp Hosting",
                    "CIRB Division of Physiology & Reproduction Field Demonstration Camp Registers & A.I. Logbooks",
                    "Department of Animal Husbandry & Dairying Haryana (District Polyclinic) Artificial Insemination Field Cards",
                    "Kisan Gosthi & Farmers Day Attendance Rosters in Nuh and Hisar villages",
                ],
                probe_queries=[
                    f'"Bado Patti" "CIRB" OR "{s_name}" OR "cloning"',
                    '"Hisar Gaurav" "semen doses" "Nuh" OR "Bado Patti" "farmers"',
                    'site:pashudhanharyana.gov.in "CIRB" "cloned" "AI"',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 11. Technology Commercialization & Extender Protocols (AgrInnovate India)
    if "agrinnovate" in all_text or "commercialization" in all_text or "extender" in all_text or "protocol" in all_text:
        anchor = "Commercialization of Semen Cryopreservation Protocols & Extension Technologies via AgrInnovate India"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="research_grant",
                deductive_question="If CIRB Division of Physiology developed novel cryopreservation protocols and field microscopes commercialized via AgrInnovate India, what licensing agreements and ITMC minutes exist?",
                expected_paper_trails=[
                    "AgrInnovate India Technology Transfer & Non-Exclusive Licensing Agreement",
                    "CIRB Institute Technology Management Committee (ITMC) Sanction Minutes",
                    "ICAR Annual Report Technology Release & IPR Chapter",
                    "Commercial Partner (e.g. Novel Industries, Ambala) Technology Transfer Vouchers",
                ],
                probe_queries=[
                    'site:agrinnovateindia.co.in "CIRB" OR "buffalo"',
                    f'site:cirb.res.in "Agrinnovate" OR "commercialization" "{last_name}"',
                    '"Novel Industries" "Ambala" "CIRB" technology',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    # 12. Student Mentorship & Thesis Guidance (CIRB-HAU/LUVAS MoU)
    if "ph.d" in all_text or "m.sc" in all_text or "mentor" in all_text or "advisory" in all_text or "students" in all_text:
        anchor = "Supervised & Co-Guided M.V.Sc. / Ph.D. Scholars in Animal Biotechnology under CIRB-HAU/LUVAS MoU"
        if anchor.lower() not in existing_anchors:
            new_inquiries.append(ForensicInquiry(
                inquiry_id=generate_inquiry_id(),
                fact_anchor=anchor,
                domain="doctoral_thesis",
                deductive_question=f"If {s_name} supervised and served on advisory committees for postgraduate scholars at CIRB/HAU/LUVAS, which student dissertations list them as Major Advisor or Advisory Committee member?",
                expected_paper_trails=[
                    "KrishiKosh ICAR National Repository Student Dissertations & Advisory Committee Pages",
                    "CCS HAU / LUVAS Nehru Library Bound Thesis Deposits with Advisor Sign-off",
                    "University Academic Council Gazette of Approved Postgraduate External Faculty",
                    "CIRB Annual Report Student Guidance & Degree Completion Acknowledgments",
                ],
                probe_queries=[
                    f'site:krishikosh.egranth.ac.in "Major Advisor" OR "Advisory Committee" "{s_name}" OR "P.S. {last_name}"',
                    f'site:luvas.edu.in "{s_name}" OR "P.S. {last_name}"',
                    'site:cirb.res.in "guided" OR "supervised" "Ph.D." OR "M.V.Sc."',
                ],
                status="open",
                actor_logged="system",
                created_at=now_iso,
            ))
            existing_anchors.add(anchor.lower())

    for inq in profile.forensic_inquiries:
        _enrich_inquiry_dual_track(inq)

    for inq in new_inquiries:
        _enrich_inquiry_dual_track(inq)

    return new_inquiries

