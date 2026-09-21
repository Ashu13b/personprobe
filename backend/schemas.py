"""Pydantic request/response models for the personprobe API."""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal, Optional


class IdentifyRequest(BaseModel):
    name: str
    field: Optional[str] = None
    affiliation: Optional[str] = None


class ResearchRequest(BaseModel):
    name: str
    wikidata_id: Optional[str] = None
    wikipedia_url: Optional[str] = None
    photo_url: Optional[str] = None
    field: Optional[str] = None
    affiliation: Optional[str] = None
    nationality: Optional[str] = None
    birth_year: Optional[str] = None


class AddSourceRequest(BaseModel):
    profile_name: str
    url: str
    title: Optional[str] = None
    text: Optional[str] = None


class AddNamesakeRequest(BaseModel):
    """Session-scoped same-name-different-person signature (engine input)."""
    profile_name: str
    display_name: str
    signature_terms: list[str] = Field(default_factory=list)
    distinguishing_traits: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    namesake_id: Optional[str] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class DeleteNamesakeRequest(BaseModel):
    profile_name: str
    namesake_id: str



class AssessSourceRequest(BaseModel):
    """Human editorial assessment retained with a research source."""
    profile_name: str
    url: str
    coverage_depth: Literal["unassessed", "passing_mention", "significant"]
    editorial_origin: Optional[str] = None
    research_notes: str = ""
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class VerifySourceLevelRequest(BaseModel):
    """Multi-level source verification request (L1 Liveness, L2 Identity, L3 Provenance)."""
    profile_name: str
    url: str
    level: Literal["liveness", "identity", "provenance", "all"]
    actor: Literal["human", "agent", "system"] = "human"
    status: Optional[str] = None  # e.g., "alive", "confirmed", "wrong_person", "suspect"
    note: Optional[str] = None
    coverage_depth: Optional[Literal["unassessed", "passing_mention", "significant"]] = None
    editorial_origin: Optional[str] = None


class AddDocumentFact(BaseModel):
    """A fact the user typed from a document — has no web source, timeline only."""
    profile_name: str
    field: str
    text: str


class AddSourcedClaimRequest(BaseModel):
    """A fact the user read directly in a source and wants bound to it."""
    profile_name: str
    url: str
    field: str
    text: str
    date_context: Optional[str] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class VerifyClaimRequest(BaseModel):
    claim_index: int
    action: str   # confirm | edit | skip | approve_draft | remove_draft
    edited_text: Optional[str] = None  # only for action=edit
    actor: Optional[Literal["human", "agent", "system"]] = "human"
    settled_quote: Optional[str] = None  # verbatim quote/snippet from source


class BatchVerifyClaimsRequest(BaseModel):
    action: str  # approve_all_usable | confirm_all | skip_unverified
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class AddSourcePaste(BaseModel):
    """User pasted text from a blocked page, screenshot, or PDF."""
    profile_name: str
    url: str           # the real URL (for citation) — even if we couldn't fetch it
    pasted_text: str   # what the user copied from the page


class CrawlRequest(BaseModel):
    profile_name: str
    seed_urls: list[str]
    keywords: list[str] = []
    max_nodes: int = 40
    max_depth: int = 3


class TargetedSearchRequest(BaseModel):
    profile_name: str
    slot: str
    hint: Optional[str] = None


class DraftRequest(BaseModel):
    profile_name: str


class FindIdsRequest(BaseModel):
    profile_name: str


class RefreshPapersRequest(BaseModel):
    profile_name: str
    id_type: str   # orcid | semantic_scholar
    id_value: str
    confirm: bool = False  # if True, mark as confirmed before refreshing


class AddInvestigationPivotRequest(BaseModel):
    profile_name: str
    pivot_type: str = "project_grant"
    title: str
    description: str = ""
    time_period: Optional[str] = None
    location: Optional[str] = None
    associated_entities: list[str] = []
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class AddAuxiliaryLeadRequest(BaseModel):
    profile_name: str
    pivot_id: Optional[str] = None
    title: str
    url: Optional[str] = None
    category: str = "general_lead"
    lead_notes: str = ""
    source_snippet: Optional[str] = None
    automated_query: Optional[str] = None
    status: Optional[Literal["lead", "inspected", "corroborated", "dead_end"]] = "lead"
    has_subject_mention: Optional[bool] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class UpdateAuxiliaryLeadRequest(BaseModel):
    profile_name: str
    lead_id: str
    status: Optional[str] = None       # lead | inspected | corroborated | dead_end
    lead_notes: Optional[str] = None
    source_snippet: Optional[str] = None
    url: Optional[str] = None
    has_subject_mention: Optional[bool] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class RunForensicSweepRequest(BaseModel):
    profile_name: str
    pivot_id: Optional[str] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class PromoteLeadToSourceRequest(BaseModel):
    profile_name: str
    lead_id: str
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class AddForensicInquiryRequest(BaseModel):
    profile_name: str
    fact_anchor: str
    domain: str = "academic_degree"
    deductive_question: str
    expected_paper_trails: list[str] = []
    probe_queries: list[str] = []
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class UpdateForensicInquiryRequest(BaseModel):
    profile_name: str
    inquiry_id: Optional[str] = None       # open | probed | confirmed | unarchived_offline | dead_end
    status: Optional[str] = None
    findings_summary: Optional[str] = None
    corroborating_links: Optional[list[str]] = None
    failure_mode: Optional[str] = None
    failure_reason: Optional[str] = None
    learned_lesson: Optional[str] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class LogInquiryFailureRequest(BaseModel):
    profile_name: str
    inquiry_id: str
    failure_mode: str          # pre_digitization_cutoff | bot_blocked | captcha_gated | id_gated | not_found | domain_down | other
    failure_reason: str        # Explanation of what failed
    learned_lesson: str        # Concrete lesson / workaround for future queries
    associated_repository_id: Optional[str] = None # Update global repository memory in atlas
    actor: Optional[Literal["human", "agent", "system"]] = "human"


class ProbeForensicInquiryRequest(BaseModel):
    profile_name: str
    inquiry_id: Optional[str] = None
    actor: Optional[Literal["human", "agent", "system"]] = "human"

