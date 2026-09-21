from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from enum import Enum


class SourceReliability(str, Enum):
    reliable_secondary = "reliable_secondary"
    primary = "primary"
    self_published = "self_published"
    unreliable = "unreliable"


class VerificationState(str, Enum):
    unverified = "unverified"    # auto-extracted, not checked by user
    confirmed = "confirmed"      # user opened source and confirmed
    edited = "edited"            # user corrected the extracted text
    skipped = "skipped"          # user chose not to verify


class VerificationActor(str, Enum):
    human = "human"
    agent = "agent"
    system = "system"


class VerificationLevel(str, Enum):
    liveness = "liveness"        # L1: Is the link live, accessible, unblocked?
    identity = "identity"        # L2: Is this for the same person (not a namesake/homonym)?
    provenance = "provenance"    # L3: Is this independent secondary coverage or primary?
    claim = "claim"              # L4: Does this link settle/substantiate the claim?
    draft = "draft"              # L5: Is this approved for Wikipedia AfC drafting?


class VerificationLogEntry(BaseModel):
    level: str                   # liveness | identity | provenance | claim | draft
    actor: str                   # human | agent | system
    action: str                  # e.g., "check_liveness", "confirm_person", "reject_person", "settle_claim", "approve_draft"
    verdict: str                 # "passed" | "rejected" | "warning" | "unverified"
    timestamp: str               # ISO timestamp
    summary: str                 # Human/agent readable explanation
    details: dict[str, Any] = Field(default_factory=dict)


class Source(BaseModel):
    url: str
    title: str
    publisher: str
    reliability: SourceReliability = SourceReliability.primary
    snippet: str = ""
    date: Optional[str] = None
    user_provided: bool = False   # True = user pasted this URL manually
    human_verified: bool = False  # True = user explicitly checked this source

    # Human editorial assessment. A reliable independent source may still be
    # only a passing mention, so it must not automatically become notability
    # evidence. Notes and origin grouping remain in the durable research record
    # even when no claim from the source is selected for a draft.
    coverage_depth: Literal["unassessed", "passing_mention", "significant"] = "unassessed"
    editorial_origin: Optional[str] = None
    research_notes: str = ""

    # Provenance and Trust scoring
    is_independent: bool = True
    domain_trust: str = "medium"             # high|medium|low|untrusted
    provenance_category: str = "general_web" # independent_secondary|authored_publication|institutional_bio|self_published|general_web

    # Where this source came from
    fetched_by: Optional[str] = None  # semantic_scholar|google_search|duckduckgo|crawl|user
    name_hit_in_body: Optional[bool] = None   # full-text name verification at fetch time (None = not checked)
    name_hit_variant: Optional[str] = None    # which name variant matched

    # Liveness & archiving (populated by check_liveness at add/verify time)
    liveness: str = "unknown"  # alive | blocked | dead | unknown
    archive_url: Optional[str] = None  # Wayback URL used as the citation when the source is dead

    # Author match result (populated for DOI/academic sources)
    author_match_status: Optional[str] = None   # confirmed|possible|wrong_person|not_found|no_data
    author_match_name: Optional[str] = None      # matched author as it appears in paper
    author_match_affiliation: Optional[str] = None
    all_paper_authors: list[str] = Field(default_factory=list)

    # Relevance flag (populated for web/news sources)
    relevance_flag: str = "unscored"

    # Where the page actually loaded after redirects ("" = not captured). A
    # meaningful redirect to a different article is surfaced here so the flag
    # and the human reviewer can see the silent trap instead of trusting the URL.
    redirected_to: Optional[str] = None

    # Profile-shaped outbound links found on this page — feed into suggestion queue
    profile_links: list[str] = Field(default_factory=list)

    # Multi-level verification & actor audit trail (L1, L2, L3)
    verification_trail: list[VerificationLogEntry] = Field(default_factory=list)
    liveness_by: Optional[str] = None          # human | agent | system
    liveness_at: Optional[str] = None
    identity_status: str = "unverified"        # unverified | confirmed | suspect | wrong_person
    identity_by: Optional[str] = None          # human | agent
    identity_at: Optional[str] = None
    identity_note: Optional[str] = None
    provenance_by: Optional[str] = None        # human | agent | system
    provenance_at: Optional[str] = None
    confirmed_for_extraction_by: Optional[str] = None  # human | agent
    confirmed_for_extraction_at: Optional[str] = None

    # Extraction diagnostics (explains why 0 claims were extracted or status of fact parsing)
    extraction_status: Optional[str] = None  # extracted | redundant | thin_content | passing_mention | stub_mode | likely_wrong
    extraction_note: Optional[str] = None


class DiscardedSource(BaseModel):
    url: str
    canonical_url: str
    title: str = ""
    reason: str = "no_name_match"  # no_name_match | off_topic | homonym | dead | user_rejected | paywall | redundant
    name_checked: str = ""
    snippet: str = ""
    date_recorded: Optional[str] = None


class KnownNamesake(BaseModel):
    """A documented same-name different person this session must never attach evidence to.

    Namesake adjudications live with the session (per-person), so a fresh
    subject researches without inheriting another person's traps. The engine
    reads these signatures mechanically at ingest time.
    """
    namesake_id: str
    display_name: str                     # "Prem Singh Yadav (CBI matter, Delhi)"
    signature_terms: list[str] = Field(default_factory=list)  # terms that in page text signal this namesake
    distinguishing_traits: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_by: str = "human"             # human | agent | system
    created_at: Optional[str] = None


class Claim(BaseModel):
    text: str
    field: str  # birth_date, affiliation, award, publication, education, position, etc.
    source_url: Optional[str] = None   # None = unsourced
    verification: VerificationState = VerificationState.unverified
    user_provided: bool = False        # True = user typed this fact directly
    auto_source_attempted: bool = False  # True = we tried to find a source, failed
    date_context: Optional[str] = None  # e.g. "2005", "2005–2015", "since 2020" — only if verbatim in source
    draft_approved: bool = False  # Explicit editorial decision; verification alone is insufficient
    draft_text: Optional[str] = None  # Neutral paraphrase used by the deterministic renderer

    # Strict Provenance & Trust Scoring
    trust_score: float = 0.5            # 0.0–1.0 trust score
    provenance_status: str = "unverified" # verified_independent|primary_sourced|unverified
    is_independent: bool = False

    # Multi-level verification & actor audit trail (L4, L5)
    verification_trail: list[VerificationLogEntry] = Field(default_factory=list)
    verified_by: Optional[str] = None          # human | agent
    verified_at: Optional[str] = None
    settled_quote: Optional[str] = None        # verbatim quote/snippet from source substantiating fact
    draft_approved_by: Optional[str] = None    # human | agent
    draft_approved_at: Optional[str] = None


class NotabilityResult(BaseModel):
    score: float          # 0.0–1.0
    label: str            # "Strong coverage" / "Moderate coverage" / etc.
    rs_count: int         # human-assessed significant independent origins
    reason: str
    candidate_count: int = 0  # independent outlets awaiting/including assessment
    wp_prof_signals: list[str] = Field(default_factory=list)  # academic-specific signals


class PersonCandidate(BaseModel):
    name: str
    photo_url: Optional[str] = None
    bio_snippet: str = ""
    birth_year: Optional[str] = None
    nationality: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    wikipedia_url: Optional[str] = None
    wikidata_id: Optional[str] = None


class UrlSuggestion(BaseModel):
    """A ranked candidate URL from the suggestion queue (suggester → frontend).

    Contract for `suggest_next_urls` output; validating at the API boundary means
    a renamed/removed key fails loudly instead of rendering as undefined in the UI.
    """
    url: str
    title: str = ""
    snippet: str = ""
    reason: str = ""
    query: Optional[str] = None
    expected_slots: list[str] = Field(default_factory=list)
    priority: int = 0
    source_type: Optional[Literal["profile", "publication", "news"]] = None
    fetchable: Literal["open", "needs_browser", "paywalled"] = "open"
    relevance: Literal["high", "medium", "low"] = "medium"
    completion_value: int = 0


class ClaimCluster(BaseModel):
    canonical_text: str
    field: str
    corroborating_sources: list[str] = Field(default_factory=list)
    claim_indices: list[int] = Field(default_factory=list)
    repetition_count: int = 1


class ResearchSaturation(BaseModel):
    score: float          # 0.0–1.0 saturation score
    level: str            # "saturated" | "mature" | "exploring"
    repetition_rate: float # 0.0–1.0 percentage of claims that repeat existing facts
    syndication_rate: float # 0.0–1.0 percentage of sources sharing editorial origins/wires
    unique_fact_count: int
    total_claims_analyzed: int
    summary: str
    corroborated_clusters: list[ClaimCluster] = Field(default_factory=list)


class InvestigationPivot(BaseModel):
    """An institutional, project, relational, or spatial anchor for forensic investigation."""
    pivot_id: str
    pivot_type: str = "project_grant"  # project_grant | institution | location | associate | gazette_legal | family_social
    title: str                         # e.g. "Project Hisar Gaurav (Cloning Scheme)"
    description: str = ""              # Context / background
    time_period: Optional[str] = None  # e.g. "2014-2018"
    location: Optional[str] = None     # e.g. "Hisar, Haryana"
    associated_entities: list[str] = Field(default_factory=list) # e.g. ["Dr. Inderjeet Singh", "NASF", "ICAR-CIRB"]
    created_by: str = "human"          # human | agent | system
    created_at: Optional[str] = None


class AuxiliaryLead(BaseModel):
    """A helping record, lead URL, or evidentiary anchor that assists forensic investigation.
    Distinct from direct Wikipedia sources: these provide administrative, financial,
    locational, or human-network corroboration."""
    lead_id: str
    pivot_id: Optional[str] = None     # Optional link to an InvestigationPivot
    title: str
    url: Optional[str] = None
    category: str = "general_lead"     # grant_sanction | annual_report | thesis_dissertation | recruitment_notice | electoral_gazette | legal_tribunal | general_lead
    lead_notes: str = ""               # Forensic clue, what to look for
    source_snippet: Optional[str] = None
    actor_logged: str = "human"        # human | agent | system
    status: str = "lead"               # lead | inspected | corroborated | dead_end
    automated_query: Optional[str] = None # Search string to reproduce / dig deeper
    has_subject_mention: bool = False  # True if the document explicitly names the subject
    promoted_source_id: Optional[str] = None # Set when promoted to primary profile.sources
    created_at: Optional[str] = None


class ForensicInquiry(BaseModel):
    """A deductive forensic hypothesis: If [fact] is true, what necessary public paper trail must exist?"""
    inquiry_id: str
    fact_anchor: str                 # e.g. "B.Sc. from CCS HAU Hisar in 1985"
    domain: str = "academic_degree"  # academic_degree | doctoral_thesis | service_entry | research_grant | campus_quarters | superannuation
    deductive_question: str          # "If a student graduated B.Sc. from CCS HAU in 1985, what public records and paper trails must exist?"
    expected_paper_trails: list[str] = Field(default_factory=list) # Specific real-world record categories
    probe_queries: list[str] = Field(default_factory=list)        # Targeted queries for digital archives/web
    status: str = "open"             # open | probed | confirmed | unarchived_offline
    findings_summary: Optional[str] = None
    corroborating_links: list[str] = Field(default_factory=list)
    actor_logged: str = "agent"      # human | agent | system
    created_at: Optional[str] = None

    # Dual-Track Paper Trail (Online Digital vs. Offline Physical Archive)
    online_probe_status: str = "open"             # open | probed | confirmed | not_digitized | dead_end
    offline_archive_flag: bool = True             # True indicates an official offline physical repository exists
    offline_archive_location: Optional[str] = None # Physical room/stacks location
    offline_custodian: Optional[str] = None        # Official statutory custodian
    offline_retrieval_method: Optional[str] = None # RTI Sec 6(1), Certified Copy (नकल), in-person inspection

    # Failure & Negative Knowledge Learning (Learn from Mistakes)
    failure_mode: Optional[str] = None             # pre_digitization_cutoff | bot_blocked | captcha_gated | id_gated | not_found | domain_down | other
    failure_reason: Optional[str] = None           # What went wrong during inquiry/probe
    learned_lesson: Optional[str] = None           # Durable insight: how subsequent searches should adapt


class PublicRecordRepository(BaseModel):
    """An open-source or statutory public repository with its historical digitization horizon."""
    category_id: str                              # e.g. "electoral_roll_haryana", "dhbvn_electricity"
    category_name: str                            # Human readable name
    domain: str                                   # civic_electoral | utility_electricity | land_revenue | municipal_property | gazette_official | academic_thesis | judicial_dockets | civil_registration | pension_benefits | corporate_directorship
    jurisdiction_level: str                       # national | state | district | institutional
    state: Optional[str] = None                   # "Haryana", "Central / All-India", etc.
    district_or_city: Optional[str] = None        # "Hisar", "Rewari", etc.
    online_since_year: Optional[int] = None       # e.g. 2009 for CEO Haryana, 2000 for Jamabandi, 2008 for eGazette
    digitization_status: str                      # digitized_open_search | digitized_id_required | digitized_captcha_gated | retrospectively_scanned_partial | strictly_offline_physical
    portal_url: Optional[str] = None
    search_query_template: Optional[str] = None
    offline_cutoff_year: Optional[int] = None     # Records prior to this year are only physical
    offline_repository_name: str
    offline_custodian: str
    offline_retrieval_method: str                 # RTI Sec 6(1), Certified Copy (नकल दरख्वास्त), in-person inspection
    required_identifiers: list[str] = Field(default_factory=list) # e.g. ["EPIC / Voter ID", "Ward"]
    forensic_utility_notes: str                   # Biographical verification purpose
    is_custom: bool = False                       # True if dynamically added by user or agent research

    # Empirical Reliability & Failure Memory
    success_count: int = 0
    failure_count: int = 0
    known_failure_modes: list[str] = Field(default_factory=list) # e.g. ["pre_2009_missing", "cloudflare_bot_blocked"]
    operational_warnings: list[str] = Field(default_factory=list) # e.g. ["Pre-2009 records are strictly physical in district record room", "Datacenter IP blocked; requires Indian mobile bridge"]


class PersonProfile(BaseModel):
    """Central data model. personprobe fills this; future research hub extends it."""
    name: str
    session_id: Optional[str] = None  # stable identity; name is just a mutable label
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    photo_url: Optional[str] = None

    # Core facts
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    nationality: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    known_for: Optional[str] = None
    awards: list[str] = Field(default_factory=list)

    # Research outputs
    sources: list[Source] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    skipped_sources: list[str] = Field(default_factory=list)
    rejected_sources: list[str] = Field(default_factory=list)
    discarded_sources: list[DiscardedSource] = Field(default_factory=list)

    # Forensic Investigation Graph & Auxiliary Leads (separate from Wikipedia citations)
    investigation_pivots: list[InvestigationPivot] = Field(default_factory=list)
    auxiliary_leads: list[AuxiliaryLead] = Field(default_factory=list)
    forensic_inquiries: list[ForensicInquiry] = Field(default_factory=list)

    # Session-scoped namesake signatures: engine screens every incoming source
    # against these mechanically (person-specific facts live here, not in docs)
    known_namesakes: list[KnownNamesake] = Field(default_factory=list)

    # Notability (informational — never a hard gate)
    notability: Optional[NotabilityResult] = None

    # Research Saturation & Diminishing Returns Analytics
    saturation: Optional[ResearchSaturation] = None

    # Slot analysis — which Wikipedia fields are still missing sources
    missing_slots: list[str] = Field(default_factory=list)

    # Researcher profile IDs (orcid, google_scholar, semantic_scholar, scopus, researchgate)
    researcher_ids: dict[str, str] = Field(default_factory=dict)
    # Which IDs have been validated against affiliation / ORCID API
    confirmed_ids: dict[str, bool] = Field(default_factory=dict)

    # Draft outputs
    wikitext_en: Optional[str] = None
    wikitext_hi: Optional[str] = None


def log_source_verification(
    source: Source,
    level: str,
    actor: str,
    action: str,
    verdict: str,
    summary: str,
    details: Optional[dict[str, Any]] = None,
) -> VerificationLogEntry:
    """Record an immutable verification step entry into a source's audit trail."""
    now_iso = datetime.now(timezone.utc).isoformat()
    entry = VerificationLogEntry(
        level=level,
        actor=actor,
        action=action,
        verdict=verdict,
        timestamp=now_iso,
        summary=summary,
        details=details or {},
    )
    source.verification_trail.append(entry)

    # Synchronize top-level fields for convenience & backwards compatibility
    if level == "liveness":
        source.liveness_by = actor
        source.liveness_at = now_iso
    elif level == "identity":
        source.identity_by = actor
        source.identity_at = now_iso
        if verdict == "passed":
            source.identity_status = "confirmed"
        elif verdict == "rejected":
            source.identity_status = "wrong_person"
        elif verdict == "warning":
            source.identity_status = "suspect"
    elif level == "provenance":
        source.provenance_by = actor
        source.provenance_at = now_iso

    return entry


def log_claim_verification(
    claim: Claim,
    level: str,
    actor: str,
    action: str,
    verdict: str,
    summary: str,
    details: Optional[dict[str, Any]] = None,
) -> VerificationLogEntry:
    """Record an immutable verification step entry into a claim's audit trail."""
    now_iso = datetime.now(timezone.utc).isoformat()
    entry = VerificationLogEntry(
        level=level,
        actor=actor,
        action=action,
        verdict=verdict,
        timestamp=now_iso,
        summary=summary,
        details=details or {},
    )
    claim.verification_trail.append(entry)

    # Synchronize top-level fields
    if level == "claim":
        claim.verified_by = actor
        claim.verified_at = now_iso
    elif level == "draft":
        claim.draft_approved_by = actor
        claim.draft_approved_at = now_iso

    return entry

