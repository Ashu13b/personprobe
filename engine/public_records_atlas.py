"""Civic & Institutional Public Records Atlas: Digitization Horizons and Archive Directory.

Maps statutory and open-source public record categories across India (National, State, District,
and Institutional levels). This registry is dynamically extensible: as researchers and autonomous
agents explore new states and discover open/reachable records, they can register them into
the permanent atlas so the 100th person research is immediate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from engine.models import PublicRecordRepository, PersonProfile, ForensicInquiry
from engine.forensics import generate_inquiry_id

REGISTRY_DIR = Path(__file__).resolve().parent.parent / "data"
REGISTRY_FILE = REGISTRY_DIR / "public_records_registry.json"


# ── Built-in Universal Public Records Master Directory ───────────────────────
BUILTIN_REPOSITORIES: list[PublicRecordRepository] = [
    # 1. Civic & Electoral
    PublicRecordRepository(
        category_id="electoral_roll_haryana",
        category_name="Electoral Roll / Voter List (CEO Haryana & ECI)",
        domain="civic_electoral",
        jurisdiction_level="state",
        state="Haryana",
        district_or_city=None,
        online_since_year=2009,
        offline_cutoff_year=2008,
        digitization_status="digitized_open_search",
        portal_url="https://ceoharyana.gov.in",
        search_query_template='site:ceoharyana.gov.in "{name}" OR "{district}" OR "{city}"',
        offline_repository_name="District Election Office & Tehsildar (Election) Record Room",
        offline_custodian="District Election Officer (Deputy Commissioner) & Tehsildar (Election)",
        offline_retrieval_method="Inspection of Historical Electoral Rolls (1952–2008) in District Election Archives; or RTI Act 2005 Sec 6(1) to SPIO Office of Chief Electoral Officer.",
        required_identifiers=["Assembly Constituency (AC)", "Polling Station / Ward", "Father/Husband Name", "EPIC No. (if known)"],
        forensic_utility_notes="Confirms physical residential domicile, age, parental names, and co-habitating family members across time.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="electoral_search_national",
        category_name="National Electoral Search (ECI Voters Service Portal)",
        domain="civic_electoral",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2014,
        offline_cutoff_year=2013,
        digitization_status="digitized_captcha_gated",
        portal_url="https://electoralsearch.eci.gov.in",
        search_query_template='site:voters.eci.gov.in "{name}" "{state}"',
        offline_repository_name="Election Commission of India National Archives, Nirvachan Sadan, Ashoka Road, New Delhi",
        offline_custodian="Under Secretary (Electoral Rolls) & Central Public Information Officer (CPIO), ECI",
        offline_retrieval_method="Application under Registration of Electors Rules 1960 for certified extract of Electoral Roll (Form 8/9 historical series).",
        required_identifiers=["Full Legal Name", "State", "District", "Relative Name"],
        forensic_utility_notes="Authoritative proof of adult citizenship, living status, and constituency enrollment.",
        is_custom=False,
    ),

    # 2. Electricity & Discom Utilities
    PublicRecordRepository(
        category_id="dhbvn_electricity_haryana",
        category_name="Electricity Utility Billing Ledger (DHBVN - South Haryana)",
        domain="utility_electricity",
        jurisdiction_level="district",
        state="Haryana",
        district_or_city="Hisar / Rewari / Gurgaon / Faridabad",
        online_since_year=2015,
        offline_cutoff_year=2014,
        digitization_status="digitized_id_required",
        portal_url="https://epayment.dhbvn.org.in",
        search_query_template='site:dhbvn.org.in "{name}" OR "{address}"',
        offline_repository_name="Sub-Divisional Office (SDO 'OP' Sub-Division), DHBVN",
        offline_custodian="Sub-Divisional Officer (Operations) & Executive Engineer (XEN), DHBVN",
        offline_retrieval_method="Inspection of Consumer Service Ledger (खाता बही / A&A Form) at local Sub-Division; or RTI Sec 6(1) to SPIO DHBVN requesting meter connection sanction and load verification.",
        required_identifiers=["10-digit Account Number (CA No.)", "Meter Number", "Premises Address"],
        forensic_utility_notes="Incontrovertible proof of continuous premises occupation, institutional vs private connection, and billing address history.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="uhbvn_electricity_haryana",
        category_name="Electricity Utility Billing Ledger (UHBVN - North Haryana)",
        domain="utility_electricity",
        jurisdiction_level="district",
        state="Haryana",
        district_or_city="Karnal / Ambala / Rohtak / Panchkula",
        online_since_year=2015,
        offline_cutoff_year=2014,
        digitization_status="digitized_id_required",
        portal_url="https://epayment.uhbvn.org.in",
        search_query_template='site:uhbvn.org.in "{name}"',
        offline_repository_name="Sub-Divisional Office (SDO 'OP'), UHBVN",
        offline_custodian="Sub-Divisional Officer (Operations), UHBVN",
        offline_retrieval_method="Consumer record request or RTI application to SPIO UHBVN.",
        required_identifiers=["10-digit Account No.", "Meter Serial No."],
        forensic_utility_notes="Corroborates North Haryana postings, university residences, or ancestral properties.",
        is_custom=False,
    ),

    # 3. Land & Revenue Records (Jamabandi / ROR / Bhulekh)
    PublicRecordRepository(
        category_id="jamabandi_haryana_revenue",
        category_name="Land & Revenue Record of Rights (Jamabandi Haryana)",
        domain="land_revenue",
        jurisdiction_level="state",
        state="Haryana",
        district_or_city=None,
        online_since_year=2000,
        offline_cutoff_year=1999,
        digitization_status="digitized_open_search",
        portal_url="https://jamabandi.nic.in",
        search_query_template='site:jamabandi.nic.in "{village}" "{name}"',
        offline_repository_name="Tehsil & District Record Room (सदर मालखाना), Mini Secretariat",
        offline_custodian="Tehsildar & District Revenue Officer (DRO) / Halqa Patwari / Kanungo",
        offline_retrieval_method="Application for Certified Copy (नकल दरख्वास्त) with court fee stamp in Tehsil Record Room under Punjab Land Revenue Act 1887 for Misal Bandobast (बंदोबस्त), Shajra Nasab (वंशावली), and historical Jamabandi (1950–1999).",
        required_identifiers=["District", "Tehsil", "Village / Hadbast No.", "Owner Name (मालिक) or Khewat/Khasra No."],
        forensic_utility_notes="Definitive legal proof of ancestral origin, rural village heritage, pedigree lineage, and land ownership.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="up_bhulekh_revenue",
        category_name="UP Bhulekh Land Records (Board of Revenue, Uttar Pradesh)",
        domain="land_revenue",
        jurisdiction_level="state",
        state="Uttar Pradesh",
        online_since_year=2006,
        offline_cutoff_year=2005,
        digitization_status="digitized_open_search",
        portal_url="https://upbhulekh.gov.in",
        search_query_template='site:upbhulekh.gov.in "{name}"',
        offline_repository_name="Tehsil Revenue Record Room (तहसील अभिलेखागार), Uttar Pradesh",
        offline_custodian="Sub-Divisional Magistrate (SDM) / Tehsildar & Registrar Kanungo",
        offline_retrieval_method="Application for Certified Copy of Khatauni (नकल खतौनी) under UP Revenue Code 2006.",
        required_identifiers=["District", "Tehsil", "Village (ग्राम)", "Khata / Gata / Khasra No."],
        forensic_utility_notes="Verifies ancestral landholding, native district, and inherited agrarian titles in Uttar Pradesh.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="delhi_dlrc_land_records",
        category_name="Delhi Online Land Records (DLRC / Revenue Department)",
        domain="land_revenue",
        jurisdiction_level="state",
        state="Delhi / NCR",
        online_since_year=2010,
        offline_cutoff_year=2009,
        digitization_status="digitized_open_search",
        portal_url="https://dlrc.delhi.gov.in",
        search_query_template='site:dlrc.delhi.gov.in "{name}"',
        offline_repository_name="Deputy Commissioner Revenue Record Room, Delhi Districts",
        offline_custodian="Sub-Divisional Magistrate (SDM) & Tehsildar",
        offline_retrieval_method="Certified copy application under Delhi Land Revenue Act 1954.",
        required_identifiers=["District", "Sub-Division", "Village", "Khasra No."],
        forensic_utility_notes="Verifies farm houses, Lal Dora properties, and rural Delhi ancestries.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="mahabhulekh_maharashtra",
        category_name="MahaBhulekh 7/12 & 8A (Revenue & Forest Department, Maharashtra)",
        domain="land_revenue",
        jurisdiction_level="state",
        state="Maharashtra",
        online_since_year=2008,
        offline_cutoff_year=2007,
        digitization_status="digitized_open_search",
        portal_url="https://bhulekh.mahabhumi.gov.in",
        search_query_template='site:bhulekh.mahabhumi.gov.in "{name}"',
        offline_repository_name="Taluka Record Room & Tahsildar Office, Maharashtra",
        offline_custodian="Tahsildar & Talathi (तलाठी)",
        offline_retrieval_method="Application under Maharashtra Land Revenue Code 1966 for certified 7/12 extract (सातबारा उतारा).",
        required_identifiers=["District", "Taluka", "Village", "Survey / Gat No."],
        forensic_utility_notes="Authoritative proof of landholding and rural ancestral lineage across Maharashtra.",
        is_custom=False,
    ),

    # 4. Municipal & Property Tax
    PublicRecordRepository(
        category_id="ulb_haryana_property_tax",
        category_name="Urban Municipal Property Register & NDC (ULB Haryana)",
        domain="municipal_property",
        jurisdiction_level="district",
        state="Haryana",
        district_or_city="Hisar / Rewari / Municipal Corporations",
        online_since_year=2018,
        offline_cutoff_year=2017,
        digitization_status="digitized_open_search",
        portal_url="https://property.ulbharyana.gov.in",
        search_query_template='site:ulbharyana.gov.in "{city}" "{name}"',
        offline_repository_name="Municipal Corporation / Municipal Council Assessment Branch",
        offline_custodian="Joint Commissioner / Executive Officer / Tax Superintendent",
        offline_retrieval_method="Inspection of House Tax Assessment Register (हाउस टैक्स रजिस्टर) or RTI Application to SPIO Municipal Corporation for Property Tax Ledger.",
        required_identifiers=["Property ID", "Colony / Sector Name", "Owner Name"],
        forensic_utility_notes="Validates urban home ownership, institutional campus quarters vs private bungalow, and civic dues clearance.",
        is_custom=False,
    ),

    # 5. Civil Registration (Birth & Death)
    PublicRecordRepository(
        category_id="crs_birth_death_registration",
        category_name="Civil Registration System (CRS / Saral Haryana Birth Register)",
        domain="civil_registration",
        jurisdiction_level="state",
        state="Haryana",
        online_since_year=2015,
        offline_cutoff_year=2014,
        digitization_status="digitized_id_required",
        portal_url="https://saralharyana.gov.in",
        search_query_template='site:saralharyana.gov.in "Birth Certificate" "{name}"',
        offline_repository_name="Office of Registrar of Births and Deaths (Civil Hospital / Municipal Health Office / PHC)",
        offline_custodian="District Registrar of Births and Deaths & Civil Surgeon / Medical Officer In-Charge",
        offline_retrieval_method="Formal Application under Section 17 of the Registration of Births and Deaths Act 1969 for certified extract of Birth Register Entry; or Sub-Divisional Magistrate (SDM) delayed registration order.",
        required_identifiers=["Date of Birth (exact or approximate year)", "Place of Birth (Hospital/Village/Ward)", "Father/Mother Name"],
        forensic_utility_notes="Primary biological proof of birth date, maternal/paternal lineage, and civil registration legality.",
        is_custom=False,
    ),

    # 6. Official Gazettes
    PublicRecordRepository(
        category_id="egazette_india_central",
        category_name="The Gazette of India (Government of India Press, New Delhi)",
        domain="gazette_official",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2008,
        offline_cutoff_year=2007,
        digitization_status="digitized_open_search",
        portal_url="https://egazette.gov.in",
        search_query_template='site:egazette.gov.in "{name}" OR "{institution}" filetype:pdf',
        offline_repository_name="National Archives of India (Janpath, New Delhi) & Central Secretariat Library",
        offline_custodian="Director General of Archives, National Archives of India & Controller of Publications, Civil Lines, Delhi",
        offline_retrieval_method="In-person archival research in National Archives Gazette Collection (Stack III); or RTI to CPIO Department of Publication.",
        required_identifiers=["Year / Notification Quarter", "Ministry / Department (e.g. DARE, Agriculture, Finance)"],
        forensic_utility_notes="Supreme sovereign public record: appointment notifications, presidential honours, gazetted pay scales, and statutory rules.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="haryana_state_gazette",
        category_name="Haryana Government Gazette (Controller of Printing & Stationery)",
        domain="gazette_official",
        jurisdiction_level="state",
        state="Haryana",
        online_since_year=2014,
        offline_cutoff_year=2013,
        digitization_status="digitized_open_search",
        portal_url="https://csharyana.gov.in",
        search_query_template='site:csharyana.gov.in "{name}" OR "{city}"',
        offline_repository_name="Haryana Government Printing Press & Archives, Sector 18, Chandigarh",
        offline_custodian="Controller of Printing and Stationery, Haryana",
        offline_retrieval_method="Archival request to Printing & Stationery Department Chandigarh; or Punjab University / Haryana State Archives (Panchkula) bound gazette collection.",
        required_identifiers=["Year / Volume", "Department (Higher Education, Agriculture, Animal Husbandry)"],
        forensic_utility_notes="Official notifications of state university degree grants, board affiliations, and provincial awards.",
        is_custom=False,
    ),

    # 7. Judicial & Court Dockets
    PublicRecordRepository(
        category_id="ecourts_district_national",
        category_name="e-Courts National Services (District & Sessions Courts)",
        domain="judicial_dockets",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2013,
        offline_cutoff_year=2012,
        digitization_status="digitized_open_search",
        portal_url="https://services.ecourts.gov.in",
        search_query_template='site:services.ecourts.gov.in "{name}" "{city}"',
        offline_repository_name="Judicial Record Room (बस्ताजात न्यायिक / Bastajat), District Court Complex",
        offline_custodian="Chief Judicial Magistrate & Superintendent, Judicial Copying Agency",
        offline_retrieval_method="Application for Certified Copy (नकल दरख्वास्त) in District Court Copying Agency with court fee stamp under High Court Rules & Orders.",
        required_identifiers=["Case Type (Civil Suit / Criminal / Misc)", "Case Number / Year", "Party Name (Petitioner/Respondent)"],
        forensic_utility_notes="Reveals civil property disputes, service matters, succession certificates, and sworn affidavits under oath.",
        is_custom=False,
    ),

    # 8. Academic Theses, Vidwan & Scholar Databases
    PublicRecordRepository(
        category_id="krishikosh_agricultural_repository",
        category_name="KrishiKosh ICAR-SAU National Agricultural Repository",
        domain="academic_thesis",
        jurisdiction_level="national",
        state="Central / Agricultural Universities",
        online_since_year=1965,  # Retrospectively scanned
        offline_cutoff_year=1964,
        digitization_status="retrospectively_scanned_partial",
        portal_url="https://krishikosh.egranth.ac.in",
        search_query_template='site:krishikosh.egranth.ac.in "{name}" OR "Major Advisor" OR "Director Nominee"',
        offline_repository_name="University Central Library Historical Theses Archive (e.g. CCSHAU Nehru Library / LUVAS Library)",
        offline_custodian="University Librarian & Dean, Postgraduate Studies",
        offline_retrieval_method="Physical reading room access request in Thesis Section (Stack Room II) with Call/Accession Number; or RTI to University SPIO for examination committee sign-off certificate.",
        required_identifiers=["Degree (M.Sc., M.V.Sc., Ph.D.)", "Department (Animal Physiology, Biotechnology)", "Year Range"],
        forensic_utility_notes="Absolute peer-reviewed proof of scientific research output, faculty supervision, and academic pedigree.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="vidwan_inflibnet_scholars",
        category_name="INFLIBNET Vidwan Database & IRINS Expert Profiles",
        domain="academic_profile",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2012,
        digitization_status="digitized_open_search",
        portal_url="https://vidwan.inflibnet.ac.in",
        search_query_template='site:vidwan.inflibnet.ac.in "{name}" OR "{institution}"',
        offline_repository_name="INFLIBNET Centre, Infocity, Gandhinagar, Gujarat - 382007",
        offline_custodian="Director, INFLIBNET Centre & Scientist-In-Charge (e-Content)",
        offline_retrieval_method="Direct public search via National Researcher Network or RTI to CPIO INFLIBNET.",
        required_identifiers=["Full Academic Name", "Primary Institution", "ResearcherID / Scopus ID"],
        forensic_utility_notes="Verified government faculty database: sanctioned projects, h-index, honors, and verified identity.",
        is_custom=False,
    ),

    # 9. Academic Book Publishers & Monograph Catalogs (Books & ISBNs)
    PublicRecordRepository(
        category_id="satish_serial_publishing_house",
        category_name="Satish Serial Publishing House (SSPH - Agricultural & Veterinary Monograph Catalog)",
        domain="academic_monograph",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2005,
        digitization_status="digitized_open_search",
        portal_url="https://www.satishserial.com",
        search_query_template='site:satishserial.com "{name}"',
        offline_repository_name="SSPH Editorial Archives, Azadpur Commercial Complex, New Delhi - 110033",
        offline_custodian="Chief Editor & Managing Director, Satish Serial Publishing House",
        offline_retrieval_method="Inspection of Historical Print Catalog / Publisher Stock Register; or Publisher direct order request.",
        required_identifiers=["Author / Editor Name", "Book Title", "ISBN", "Subject Area"],
        forensic_utility_notes="Authoritative peer-reviewed proof of authored textbooks, edited monographs, reference treatises, and ISBN numbers in agricultural, biotechnology, and veterinary sciences.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="icar_dkma_publications",
        category_name="ICAR-DKMA Publications, e-Books & Monographs Portal",
        domain="academic_monograph",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2008,
        digitization_status="digitized_open_search",
        portal_url="https://epubs.icar.org.in",
        search_query_template='site:epubs.icar.org.in "{name}"',
        offline_repository_name="ICAR-DKMA Sales & Distribution Section, Krishi Anusandhan Bhavan-I, Pusa, New Delhi - 110012",
        offline_custodian="Project Director, DKMA & Business Manager, ICAR Publications",
        offline_retrieval_method="Direct inspection in ICAR Krishi Vigyan Book Stalls / Central Library; or RTI to CPIO DKMA.",
        required_identifiers=["Author Name", "Title / Technical Bulletin", "ICAR Institute"],
        forensic_utility_notes="Statutory publications of Government of India agricultural research institutes: bulletins, monographs, and official technology manuals.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="daya_publishing_house_astral",
        category_name="Daya Publishing House / Astral Books (Life & Agricultural Sciences)",
        domain="academic_monograph",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2006,
        digitization_status="digitized_open_search",
        portal_url="https://astralint.com",
        search_query_template='site:astralint.com "{name}"',
        offline_repository_name="Astral International / Daya Publishing Archives, Ansari Road, Daryaganj, New Delhi",
        offline_custodian="Managing Editor, Astral International Private Limited",
        offline_retrieval_method="Search in National Library of India (Kolkata) / Raja Rammohun Roy National Agency for ISBN.",
        required_identifiers=["Author Name", "Book Title", "ISBN"],
        forensic_utility_notes="Authoritative record of scholarly monographs in fisheries, veterinary medicine, agronomy, and animal breeding.",
        is_custom=False,
    ),

    # 10. Patents & Inventions
    PublicRecordRepository(
        category_id="inpass_patents_india",
        category_name="Indian Patent Advanced Search System (InPASS / CGPDTM)",
        domain="patent_registry",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=1995,
        offline_cutoff_year=1994,
        digitization_status="digitized_open_search",
        portal_url="https://ipindiaservices.gov.in/publicsearch",
        search_query_template='site:ipindiaservices.gov.in "{name}" "Patent"',
        offline_repository_name="Patent Office Technical Library, Intellectual Property Office Building (Delhi / Kolkata / Chennai / Mumbai)",
        offline_custodian="Controller General of Patents, Designs and Trade Marks (CGPDTM)",
        offline_retrieval_method="Inspection of Register of Patents under Section 72 of Patents Act 1970; or Certified Extract of Patent Register entry.",
        required_identifiers=["Inventor Name", "Applicant Name (e.g. ICAR)", "Application / Patent Number"],
        forensic_utility_notes="Legal proof of technological inventions, patent filings, commercial licensing, and statutory priority dates.",
        is_custom=False,
    ),

    # 10. Professional Councils (Medical & Legal)
    PublicRecordRepository(
        category_id="nmc_indian_medical_register",
        category_name="National Medical Commission (Indian Medical Register / NMC)",
        domain="professional_council",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=1960,  # Retrospectively digitized
        digitization_status="digitized_open_search",
        portal_url="https://www.nmc.org.in/information-desk/indian-medical-register",
        search_query_template='site:nmc.org.in "Doctor" "{name}"',
        offline_repository_name="National Medical Commission Office, Pocket 14, Sector 8, Dwarka, New Delhi",
        offline_custodian="Secretary, National Medical Commission & Registrar, State Medical Council",
        offline_retrieval_method="Formal Application under NMC Act 2019 for verified certificate of registration.",
        required_identifiers=["Registration Number", "State Medical Council", "Year of Registration"],
        forensic_utility_notes="Statutory verification of medical degrees (MBBS/MD/MS) and valid medical practice licensure.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="bar_council_advocate_rolls",
        category_name="Bar Council of India & State Bar Councils (Advocates Rolls)",
        domain="professional_council",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2010,
        offline_cutoff_year=2009,
        digitization_status="digitized_open_search",
        portal_url="https://www.barcouncilofindia.org",
        search_query_template='site:barcouncilofindia.org "{name}" OR "Advocate"',
        offline_repository_name="State Bar Council Record Room (e.g. Bar Council of Punjab & Haryana, Chandigarh)",
        offline_custodian="Secretary, State Bar Council",
        offline_retrieval_method="Inspection of Roll of Advocates under Section 17 of Advocates Act 1961.",
        required_identifiers=["Enrollment Number (e.g. P/123/1990)", "State Bar Council", "Father Name"],
        forensic_utility_notes="Confirms legal practice enrollment, Law degree validity, and official bar membership.",
        is_custom=False,
    ),

    # 11. Central Pension & Service Benefits
    PublicRecordRepository(
        category_id="cpao_central_pension",
        category_name="Central Pension Accounting Office (CPAO) & Bhavishya Portal",
        domain="pension_benefits",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2017,
        offline_cutoff_year=2016,
        digitization_status="digitized_id_required",
        portal_url="https://cpao.nic.in",
        search_query_template='site:cpao.nic.in "{name}" "ICAR"',
        offline_repository_name="CPAO Archives, Trikoot-II, Bhikaji Cama Place, New Delhi & ICAR Establishment Pension Cell",
        offline_custodian="Chief Controller of Pensions (CPAO) & Drawing & Disbursing Officer (DDO), ICAR-CIRB",
        offline_retrieval_method="RTI Act 2005 Sec 6(1) to CPIO CPAO or CPIO ICAR HQ for Pension Payment Order (PPO) number, qualifying service computation, and superannuation gratuity schedule.",
        required_identifiers=["Pension Payment Order (PPO) No.", "PAN / Date of Retirement"],
        forensic_utility_notes="Legally binding proof of exact superannuation date, total years of government service, and final gazetted pay rank.",
        is_custom=False,
    ),
    PublicRecordRepository(
        category_id="sparsh_defence_pension",
        category_name="SPARSH Defence Pension Portal (PCDA Pensions, Prayagraj)",
        domain="pension_benefits",
        jurisdiction_level="national",
        state="Central / Defence",
        online_since_year=2020,
        offline_cutoff_year=2019,
        digitization_status="digitized_id_required",
        portal_url="https://sparsh.defencepension.gov.in",
        search_query_template='site:sparsh.defencepension.gov.in "{name}"',
        offline_repository_name="Office of Principal Controller of Defence Accounts (PCDA Pensions), Draupadi Ghat, Prayagraj - 211014",
        offline_custodian="Principal Controller of Defence Accounts (Pensions)",
        offline_retrieval_method="Defence Pension Claim Verification / Record Office Verification Order under Pension Regulations for the Army/Navy/Air Force.",
        required_identifiers=["Service Number", "Rank", "Arm / Corps", "Date of Discharge / PPO No."],
        forensic_utility_notes="Authoritative military career record: verification of rank, wartime deployments, decorations, and defence pension.",
        is_custom=False,
    ),

    # 12. Corporate & Producer Company Directorships
    PublicRecordRepository(
        category_id="mca_directors_registry",
        category_name="Ministry of Corporate Affairs (MCA21 Directors Registry)",
        domain="corporate_directorship",
        jurisdiction_level="national",
        state="Central / All-India",
        online_since_year=2006,
        offline_cutoff_year=2005,
        digitization_status="digitized_open_search",
        portal_url="https://www.mca.gov.in",
        search_query_template='site:zaubacorp.com OR site:mca.gov.in "{name}" "Director"',
        offline_repository_name="Registrar of Companies (RoC Delhi & Haryana), 4th Floor, IFCI Tower, Nehru Place, New Delhi",
        offline_custodian="Registrar of Companies (RoC) Delhi & Haryana",
        offline_retrieval_method="Public Company Document Inspection (MCA Portal Form GNL-2) or physical RoC file inspection.",
        required_identifiers=["Director Identification Number (DIN)", "Company Name / CIN"],
        forensic_utility_notes="Exposes private commercial interests, advisory board directorships in biotech startups, and Section 8 agricultural trusts.",
        is_custom=False,
    ),
]


def _ensure_registry_dir() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def load_custom_repositories() -> list[PublicRecordRepository]:
    """Load user-added or agent-discovered custom public repositories from disk."""
    if not REGISTRY_FILE.exists():
        return []
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [PublicRecordRepository(**item) for item in data]
    except Exception:
        return []


def save_custom_repositories(repos: list[PublicRecordRepository]) -> None:
    """Save user-added custom public repositories to disk."""
    _ensure_registry_dir()
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in repos], f, indent=2, ensure_ascii=False)


def register_public_repository(repo: PublicRecordRepository) -> PublicRecordRepository:
    """Add or update a tested public repository in the permanent registry."""
    repo.is_custom = True
    custom_list = load_custom_repositories()
    # Replace existing by category_id or append
    updated = False
    new_list: list[PublicRecordRepository] = []
    for existing in custom_list:
        if existing.category_id == repo.category_id:
            new_list.append(repo)
            updated = True
        else:
            new_list.append(existing)
    if not updated:
        new_list.append(repo)

    save_custom_repositories(new_list)
    return repo


def delete_custom_repository(category_id: str) -> bool:
    """Remove a custom repository from the registry."""
    custom_list = load_custom_repositories()
    filtered = [r for r in custom_list if r.category_id != category_id]
    if len(filtered) < len(custom_list):
        save_custom_repositories(filtered)
        return True
    return False


def record_repository_learning(
    category_id: str,
    success: bool,
    failure_mode: Optional[str] = None,
    operational_warning: Optional[str] = None,
) -> Optional[PublicRecordRepository]:
    """Record empirical search outcomes and learn from failures.

    Persists learned failure modes (e.g. pre-2008 records missing, cloudflare bot blocked,
    requires OTP/meter ID) so subsequent searches across any profile benefit immediately.
    """
    all_repos = get_public_records_atlas()
    target: Optional[PublicRecordRepository] = None
    for r in all_repos:
        if r.category_id == category_id:
            target = r
            break

    if not target:
        return None

    if success:
        target.success_count += 1
    else:
        target.failure_count += 1
        if failure_mode and failure_mode not in target.known_failure_modes:
            target.known_failure_modes.append(failure_mode)
        if operational_warning and operational_warning not in target.operational_warnings:
            target.operational_warnings.append(operational_warning)

    # Persist in custom registry
    register_public_repository(target)
    return target


def get_public_records_atlas() -> list[PublicRecordRepository]:
    """Returns all repositories: built-in defaults merged with user-added custom repositories."""
    custom = load_custom_repositories()
    custom_map = {r.category_id: r for r in custom}

    result: list[PublicRecordRepository] = []
    for r in BUILTIN_REPOSITORIES:
        if r.category_id in custom_map:
            result.append(custom_map.pop(r.category_id))
        else:
            result.append(r)

    # Append any novel custom repositories
    for r in custom_map.values():
        result.append(r)

    return result


def derive_subject_record_matrix(profile: PersonProfile) -> dict:
    """Analyze a biographical profile across time, geography, and institution to build a custom research matrix.

    This works for any subject (subject #1 or subject #100):
    Determines which public records are digitally reachable online vs. which fall
    before the historical digitization horizon and must be flagged as offline physical archives.
    """
    # Extract subject timeline hints
    birth_year: Optional[int] = None
    if profile.birth_date:
        for token in profile.birth_date.replace("-", " ").split():
            if token.isdigit() and 1900 <= int(token) <= 2025:
                birth_year = int(token)
                break

    # Check geographical and institutional context
    all_context = " ".join(
        filter(None, [
            profile.name,
            profile.birth_place,
            profile.affiliation,
            profile.field,
            profile.full_name,
        ] + [c.text for c in profile.claims if c.text])
    ).lower()

    # Detect active jurisdictions
    is_haryana = any(k in all_context for k in ["haryana", "hisar", "rewari", "bhiwani", "karnal", "rohtak", "hau", "luvas", "cirb"])
    is_up = any(k in all_context for k in ["uttar pradesh", "lucknow", "kanpur", "varanasi", "meerut", "agra", "ivri", "bareilly", "mathura"])
    is_delhi = any(k in all_context for k in ["delhi", "new delhi", "pusa", "iari", "icar hq", "krishi bhavan"])
    is_maharashtra = any(k in all_context for k in ["maharashtra", "mumbai", "pune", "nagpur", "cife"])
    is_punjab = any(k in all_context for k in ["punjab", "ludhiana", "pau", "gadvasu", "chandigarh"])

    has_hisar = "hisar" in all_context or "cirb" in all_context or "hau" in all_context
    has_rewari = "rewari" in all_context or "nimoth" in all_context

    online_reachable: list[dict] = []
    offline_archives: list[dict] = []
    id_required_portals: list[dict] = []

    active_atlas = get_public_records_atlas()

    for repo in active_atlas:
        # Check geographical relevance
        if repo.state == "Haryana" and not is_haryana:
            continue
        if repo.state == "Uttar Pradesh" and not is_up:
            continue
        if repo.state == "Delhi / NCR" and not is_delhi:
            continue
        if repo.state == "Maharashtra" and not is_maharashtra:
            continue
        if repo.district_or_city and "Hisar" in repo.district_or_city and not (has_hisar or is_haryana):
            continue

        repo_dict = repo.model_dump()
        template = repo.search_query_template or ""
        repo_dict["custom_search_query"] = (
            template.replace("{name}", profile.name)
            .replace("{district}", "Hisar" if has_hisar else ("Rewari" if has_rewari else "Haryana"))
            .replace("{city}", "Hisar" if has_hisar else ("Rewari" if has_rewari else ""))
            .replace("{village}", "Nimoth" if has_rewari else "")
            .replace("{institution}", profile.affiliation or "ICAR")
            .replace("{state}", "Haryana" if is_haryana else ("Uttar Pradesh" if is_up else "India"))
            .replace("{address}", profile.birth_place or "Hisar")
        )

        # Categorize into digital vs offline vs id-gated
        if repo.digitization_status in ("digitized_open_search", "retrospectively_scanned_partial"):
            online_reachable.append(repo_dict)
        elif repo.digitization_status in ("digitized_id_required", "digitized_captcha_gated"):
            id_required_portals.append(repo_dict)
        else:
            offline_archives.append(repo_dict)

        # If subject's birth or early career occurred before digitization cutoff, flag corresponding physical repository
        if birth_year and repo.offline_cutoff_year and birth_year <= repo.offline_cutoff_year:
            repo_dict_pre = dict(repo_dict)
            repo_dict_pre["pre_digitization_reason"] = (
                f"Subject's milestone (c. {birth_year}) predates {repo.category_name} digitization "
                f"horizon ({repo.online_since_year}+). Physical archive search mandatory."
            )
            offline_archives.append(repo_dict_pre)

    primary_state = "Haryana" if is_haryana else ("Uttar Pradesh" if is_up else ("Delhi / NCR" if is_delhi else ("Maharashtra" if is_maharashtra else "National")))

    return {
        "profile_name": profile.name,
        "birth_year": birth_year,
        "primary_state": primary_state,
        "primary_districts": [d for d, flag in [("Hisar", has_hisar), ("Rewari", has_rewari)] if flag],
        "online_reachable_count": len(online_reachable),
        "id_required_count": len(id_required_portals),
        "offline_archives_count": len(offline_archives),
        "online_reachable": online_reachable,
        "id_required_portals": id_required_portals,
        "offline_archives": offline_archives,
    }


def generate_civic_inquiries(profile: PersonProfile) -> list[ForensicInquiry]:
    """Generate generalized civic, utility, and municipal public record inquiries for any subject."""
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_anchors = {inq.fact_anchor.lower() for inq in profile.forensic_inquiries}
    civic_inquiries: list[ForensicInquiry] = []
    s_name = profile.name

    all_context = " ".join(
        filter(None, [
            profile.name,
            profile.birth_place,
            profile.affiliation,
            profile.field,
        ] + [c.text for c in profile.claims if c.text])
    ).lower()

    # 1. Electoral Roll Domicile Inquiry
    if "electoral roll" not in " ".join(existing_anchors):
        district = "Hisar" if "hisar" in all_context else ("Rewari" if "rewari" in all_context else "Haryana")
        civic_inquiries.append(ForensicInquiry(
            inquiry_id=generate_inquiry_id(),
            fact_anchor=f"Electoral Roll & Domicile Registration in District {district} (CEO Haryana)",
            domain="civic_electoral",
            deductive_question=f"If {s_name} is a long-term registered voter in {district} (Haryana), which Assembly Constituency and Polling Station voter roll lists their family household?",
            expected_paper_trails=[
                "Election Commission of India (ECI) / CEO Haryana Assembly Constituency Electoral Roll (PDF)",
                "Electoral Photo Identity Card (EPIC) Central Database Registration Record",
                "Form 6 New Voter Enrollment Verification / Booth Level Officer (BLO) Inspection Report",
            ],
            probe_queries=[
                f'site:ceoharyana.gov.in "{district}" "{s_name}"',
                f'site:voters.eci.gov.in "{s_name}" "{district}"',
                f'"Electoral Roll" "{district}" "{s_name}"',
            ],
            status="open",
            actor_logged="system",
            created_at=now_iso,
            online_probe_status="open",
            offline_archive_flag=True,
            offline_archive_location=f"District Election Office & Tehsildar (Election) Record Room, Mini Secretariat, {district}",
            offline_custodian=f"District Election Officer (Deputy Commissioner) & Tehsildar (Election), {district}",
            offline_retrieval_method="Inspection of Pre-2009 Historical Electoral Rolls (1952–2008) in District Election Archives; or RTI Act 2005 Sec 6(1) to SPIO Office of Chief Electoral Officer.",
        ))

    # 2. Electricity / Discom Connection (DHBVN)
    if "electricity" not in " ".join(existing_anchors) and ("hisar" in all_context or "rewari" in all_context or "cirb" in all_context):
        civic_inquiries.append(ForensicInquiry(
            inquiry_id=generate_inquiry_id(),
            fact_anchor="Residential Electricity Utility Meter & Connection (DHBVN Hisar / Residential Complex)",
            domain="utility_electricity",
            deductive_question=f"If {s_name} maintained a residential electrical connection in Hisar, what meter ledger and Discom consumer records verify premises occupation?",
            expected_paper_trails=[
                "Dakshin Haryana Bijli Vitran Nigam (DHBVN) Consumer Account (CA) Ledger & Monthly Energy Bills",
                "DHBVN Agreement & Application (A&A) Form for Domestic Electric Connection",
                "Sub-Divisional Office (SDO 'OP') Meter Test & Installation Verification Sheet",
            ],
            probe_queries=[
                f'site:dhbvn.org.in "Hisar" "{s_name}"',
                f'"DHBVN" "Hisar" electricity "{s_name}"',
            ],
            status="open",
            actor_logged="system",
            created_at=now_iso,
            online_probe_status="open",
            offline_archive_flag=True,
            offline_archive_location="Sub-Divisional Office (SDO 'OP' Sub-Division), DHBVN, Hisar",
            offline_custodian="Sub-Divisional Officer (Operations) & Executive Engineer (XEN), DHBVN Hisar",
            offline_retrieval_method="Inspection of Consumer Service Ledger (खाता बही) at local Sub-Division; or RTI Sec 6(1) to SPIO DHBVN requesting connection sanction and load verification.",
        ))

    # 3. Official Gazette of India (Central Appointment & Cadre Notifications)
    if "gazette of india" not in " ".join(existing_anchors):
        civic_inquiries.append(ForensicInquiry(
            inquiry_id=generate_inquiry_id(),
            fact_anchor="The Gazette of India Central Government Notifications (ICAR / DARE Appointment & Cadre)",
            domain="gazette_official",
            deductive_question=f"If {s_name} served as a Group-A scientific officer in the Government of India / ICAR for 32 years, what statutory notifications exist in The Gazette of India?",
            expected_paper_trails=[
                "The Gazette of India (Part I, Section 2: Notifications regarding Appointments, Promotions, Leave, etc. of Officers)",
                "Department of Agricultural Research & Education (DARE) Statutory Office Memorandum in Gazette",
                "Government of India Press Historical Gazette Register (New Delhi)",
            ],
            probe_queries=[
                f'site:egazette.gov.in "{s_name}" "ICAR" filetype:pdf',
                f'site:egazette.gov.in "{s_name}" "Buffalo" OR "CIRB"',
                '"Gazette of India" "Prem Singh Yadav" "ICAR"',
            ],
            status="open",
            actor_logged="system",
            created_at=now_iso,
            online_probe_status="open",
            offline_archive_flag=True,
            offline_archive_location="National Archives of India, Janpath, New Delhi - 110001 & Central Secretariat Library",
            offline_custodian="Director General of Archives, National Archives of India & Controller of Publications, Delhi",
            offline_retrieval_method="Archival research in National Archives Gazette Collection (Stack Room III) for Pre-2008 gazette issues; or online search on e-Gazette portal for 2008–present.",
        ))

    return civic_inquiries
