export interface PersonCandidate {
  name: string;
  photo_url: string | null;
  bio_snippet: string;
  birth_year: string | null;
  nationality: string | null;
  field: string | null;
  affiliation: string | null;
  wikipedia_url: string | null;
  wikidata_id: string | null;
}

export type SourceReliability = "reliable_secondary" | "primary" | "self_published" | "unreliable";
export type VerificationState = "unverified" | "confirmed" | "edited" | "skipped";
export type SourceFetchedBy = "semantic_scholar" | "google_search" | "duckduckgo" | "crawl" | "user" | "openalex" | "orcid" | "browser" | null;

export type VerificationActor = "human" | "agent" | "system";
export type VerificationLevel = "liveness" | "identity" | "provenance" | "claim" | "draft";

export interface VerificationLogEntry {
  level: VerificationLevel;
  actor: VerificationActor;
  action: string;
  verdict: "passed" | "rejected" | "warning" | "unverified";
  timestamp: string;
  summary: string;
  details?: Record<string, any>;
}

export interface Source {
  url: string;
  coverage_depth: "unassessed" | "passing_mention" | "significant";
  editorial_origin: string | null;
  research_notes: string;
  title: string;
  publisher: string;
  reliability: SourceReliability;
  snippet: string;
  date: string | null;
  user_provided: boolean;
  human_verified: boolean;
  is_independent?: boolean;
  domain_trust?: "high" | "medium" | "low" | "untrusted";
  provenance_category?: "independent_secondary" | "authored_publication" | "institutional_bio" | "self_published" | "general_web" | "cv_blueprint" | "record_registry";
  fetched_by: SourceFetchedBy;
  author_match_status: "confirmed" | "possible" | "wrong_person" | "not_found" | "no_data" | null;
  author_match_name: string | null;
  author_match_affiliation: string | null;
  all_paper_authors: string[];
  relevance_flag: "relevant" | "uncertain" | "likely_wrong" | "unscored";
  redirected_to: string | null;
  liveness?: "alive" | "blocked" | "dead" | "unknown";
  archive_url?: string | null;
  profile_links: string[];
  extraction_status?: "extracted" | "redundant" | "thin_content" | "passing_mention" | "stub_mode" | "likely_wrong" | null;
  extraction_note?: string | null;

  // Multi-level verification & actor attribution (L1, L2, L3)
  verification_trail?: VerificationLogEntry[];
  liveness_by?: VerificationActor | null;
  liveness_at?: string | null;
  identity_status?: "unverified" | "confirmed" | "suspect" | "wrong_person";
  identity_by?: VerificationActor | null;
  identity_at?: string | null;
  identity_note?: string | null;
  provenance_by?: VerificationActor | null;
  provenance_at?: string | null;
  confirmed_for_extraction_by?: VerificationActor | null;
  confirmed_for_extraction_at?: string | null;
}

export interface Claim {
  text: string;
  field: string;
  source_url: string | null;
  verification: VerificationState;
  user_provided: boolean;
  auto_source_attempted: boolean;
  date_context?: string | null;
  draft_approved?: boolean;
  draft_text?: string | null;
  trust_score?: number;
  provenance_status?: "verified_independent" | "primary_sourced" | "unverified";
  is_independent?: boolean;

  // Multi-level verification & actor attribution (L4, L5)
  verification_trail?: VerificationLogEntry[];
  verified_by?: VerificationActor | null;
  verified_at?: string | null;
  settled_quote?: string | null;
  draft_approved_by?: VerificationActor | null;
  draft_approved_at?: string | null;
}

export interface VerificationSummaryResponse {
  levels: {
    l1_liveness: {
      total: number;
      alive: number;
      dead: number;
      blocked: number;
      checked_by_agent: number;
      checked_by_human: number;
    };
    l2_identity: {
      total: number;
      confirmed: number;
      suspect: number;
      unverified: number;
      verified_by_agent: number;
      verified_by_human: number;
    };
    l3_provenance: {
      total: number;
      significant: number;
      passing_mention: number;
      independent_secondary: number;
    };
    l4_claims: {
      total: number;
      settled: number;
      unverified: number;
      skipped: number;
      verified_by_agent: number;
      verified_by_human: number;
    };
    l5_draft: {
      total_approved: number;
      approved_by_agent: number;
      approved_by_human: number;
    };
  };
  audit_events: {
    agent_actions: number;
    human_actions: number;
  };
}

export interface NotabilityResult {
  score: number;
  label: string;
  rs_count: number;
  candidate_count: number;
  reason: string;
  passed: boolean;
}

export interface WikiStatus {
  status: "exists" | "draft" | "deleted" | "clear";
  url: string | null;
  note: string | null;
}

export interface ClaimCluster {
  canonical_text: string;
  field: string;
  corroborating_sources: string[];
  claim_indices: number[];
  repetition_count: number;
}

export interface ResearchSaturation {
  score: number;
  level: "saturated" | "mature" | "exploring";
  repetition_rate: number;
  syndication_rate: number;
  unique_fact_count: number;
  total_claims_analyzed: number;
  summary: string;
  corroborated_clusters: ClaimCluster[];
}

export interface DiscardedSource {
  url: string;
  canonical_url: string;
  title: string;
  reason: string;
  name_checked: string;
  snippet: string;
  date_recorded?: string | null;
}

export interface InvestigationPivot {
  pivot_id: string;
  pivot_type: "project_grant" | "institution" | "location" | "associate" | "gazette_legal" | "family_social" | string;
  title: string;
  description: string;
  time_period?: string | null;
  location?: string | null;
  associated_entities: string[];
  created_by: "human" | "agent" | "system";
  created_at?: string | null;
}

export interface AuxiliaryLead {
  lead_id: string;
  pivot_id?: string | null;
  title: string;
  url?: string | null;
  category: "grant_sanction" | "annual_report" | "thesis_dissertation" | "recruitment_notice" | "electoral_gazette" | "legal_tribunal" | "general_lead" | string;
  lead_notes: string;
  source_snippet?: string | null;
  actor_logged: "human" | "agent" | "system";
  status: "lead" | "inspected" | "corroborated" | "dead_end";
  automated_query?: string | null;
  has_subject_mention?: boolean;
  promoted_source_id?: string | null;
  created_at?: string | null;
}


export interface ForensicInquiry {
  inquiry_id: string;
  fact_anchor: string;
  domain: "academic_degree" | "doctoral_thesis" | "service_entry" | "research_grant" | "campus_quarters" | "superannuation" | string;
  deductive_question: string;
  expected_paper_trails: string[];
  probe_queries: string[];
  status: "open" | "probed" | "confirmed" | "unarchived_offline" | "dead_end" | string;
  findings_summary?: string | null;
  corroborating_links: string[];
  actor_logged: "human" | "agent" | "system";
  created_at?: string | null;

  // Dual-Track Paper Trail (Online Digital vs. Offline Physical Archive)
  online_probe_status?: "open" | "probed" | "confirmed" | "not_digitized" | "dead_end" | string;
  offline_archive_flag?: boolean;
  offline_archive_location?: string | null;
  offline_custodian?: string | null;
  offline_retrieval_method?: string | null;

  // Failure & Negative Knowledge Learning
  failure_mode?: "pre_digitization_cutoff" | "bot_blocked" | "captcha_gated" | "id_gated" | "not_found" | "domain_down" | string | null;
  failure_reason?: string | null;
  learned_lesson?: string | null;
}


export interface ForensicsSummaryResponse {
  ok: boolean;
  profile_name: string;
  pivots: InvestigationPivot[];
  leads: AuxiliaryLead[];
  inquiries?: ForensicInquiry[];
  metrics: {
    pivots_count: number;
    leads_count: number;
    corroborated_leads: number;
    inquiries_count?: number;
  };
}

export interface PublicRecordRepository {
  category_id: string;
  category_name: string;
  domain: string;
  jurisdiction_level: string;
  state?: string | null;
  district_or_city?: string | null;
  online_since_year?: number | null;
  offline_cutoff_year?: number | null;
  digitization_status: "digitized_open_search" | "digitized_id_required" | "digitized_captcha_gated" | "retrospectively_scanned_partial" | "strictly_offline_physical" | string;
  portal_url?: string | null;
  search_query_template?: string | null;
  offline_repository_name: string;
  offline_custodian: string;
  offline_retrieval_method: string;
  required_identifiers: string[];
  forensic_utility_notes: string;
  custom_search_query?: string;
  pre_digitization_reason?: string;
  is_custom?: boolean;
  success_count?: number;
  failure_count?: number;
  known_failure_modes?: string[];
  operational_warnings?: string[];
}

export interface SubjectRecordMatrix {
  profile_name: string;
  birth_year?: number | null;
  primary_state: string;
  primary_districts: string[];
  online_reachable_count: number;
  id_required_count: number;
  offline_archives_count: number;
  online_reachable: PublicRecordRepository[];
  id_required_portals: PublicRecordRepository[];
  offline_archives: PublicRecordRepository[];
}

export interface AtlasResponse {
  ok: boolean;
  total_repositories: number;
  repositories: PublicRecordRepository[];
}

export interface AtlasMatrixResponse {
  ok: boolean;
  matrix: SubjectRecordMatrix;
}


export interface PersonProfile {
  name: string;
  wikidata_id: string | null;
  wikipedia_url: string | null;
  photo_url: string | null;
  full_name: string | null;
  birth_date: string | null;
  birth_place: string | null;
  nationality: string | null;
  field: string | null;
  affiliation: string | null;
  known_for: string | null;
  awards: string[];
  sources: Source[];
  claims: Claim[];
  skipped_sources: string[];
  rejected_sources: string[];
  discarded_sources?: DiscardedSource[];
  investigation_pivots?: InvestigationPivot[];
  auxiliary_leads?: AuxiliaryLead[];
  forensic_inquiries?: ForensicInquiry[];
  missing_slots: string[];
  researcher_ids: Record<string, string>;
  confirmed_ids: Record<string, boolean>;
  notability: NotabilityResult | null;
  saturation: ResearchSaturation | null;
  wikitext_en: string | null;
  wikitext_hi: string | null;
}

// Response shapes matching FastAPI endpoints
export interface ResearchStartResponse {
  wiki_status: WikiStatus;
  notability: NotabilityResult;
  profile: PersonProfile;
  resumed?: boolean;
}

export interface SdPipelineResult {
  doi?: string;
  title?: string;
  crossref_authors?: string[];
  openalex_author_id?: string | null;
  openalex_works_added?: number;
  scopus_id?: string | null;
}

export interface AddSourceResponse {
  source: Source | null;
  blocked: boolean;
  new_claims: Claim[];
  notability: NotabilityResult;
  pipeline?: SdPipelineResult | null;
  researcher_ids?: Record<string, string>;
  confirmed_ids?: Record<string, boolean>;
  sent_to_browser?: boolean;
}

export interface AddSourcePasteResponse {
  source: Source;
  new_claims: Claim[];
  notability: NotabilityResult;
}

export interface CrawlResponse {
  nodes_crawled: number;
  relevant_sources: number;
  new_claims: number;
  notability: NotabilityResult;
  sources: Source[];
}

export interface DraftIssue {
  code: string;
  message: string;
  count: number;
}

export interface DraftAudit {
  ready: boolean;
  eligible_claim_count: number;
  eligible_source_count: number;
  independent_source_count: number;
  excluded_claim_count: number;
  blockers: DraftIssue[];
  warnings: DraftIssue[];
  exclusions: DraftIssue[];
}

export interface DraftResponse {
  profile: PersonProfile;
  audit: DraftAudit;
}

export type DraftLinkStatus = "ok" | "blocked" | "dead" | "unknown";

export interface DraftLink {
  url: string;
  label: string;
  archived: boolean;
  status: DraftLinkStatus;
  status_code: number | null;
  final_url: string | null;
}

export type DraftWikilinkStatus = "ok" | "disambiguation" | "missing" | "unknown";

export interface DraftWikilink {
  target: string;
  label: string;
  status: DraftWikilinkStatus;
  canonical_target?: string | null;
  description?: string | null;
}

export interface DraftLinksResult {
  links: DraftLink[];
  wiki_links: DraftWikilink[];
}

export type DraftQaSeverity = "error" | "warning" | "info";

export interface DraftQaFinding {
  id: string;
  severity: DraftQaSeverity;
  message: string;
}

export interface DraftQaReport {
  findings: DraftQaFinding[];
  passed: boolean;
  counts: Record<DraftQaSeverity, number>;
}

export interface UrlSuggestion {
  url: string;
  title: string;
  snippet: string;
  reason: string;
  query?: string;
  expected_slots: string[];
  priority: number;
  source_type?: "profile" | "publication" | "news";
  fetchable: "open" | "needs_browser" | "paywalled";
  relevance: "high" | "medium" | "low";
  completion_value: number;
}

export interface StageAuditItem {
  stage_id: "discovery" | "provenance" | "claims" | "draft";
  label: string;
  status: "completed" | "in_progress" | "blocked" | "attention_needed";
  score: number;
  summary: string;
  metrics: Record<string, any>;
  recommendations: string[];
}

export interface FullLifecycleAudit {
  current_stage: "discovery" | "provenance" | "claims" | "draft";
  overall_health: "healthy" | "needs_attention" | "blocked";
  completion_rate: number;
  stages: StageAuditItem[];
  next_action: string;
  mobile_bridge_online: boolean;
}

export interface MobileBridgeStatus {
  online: boolean;
  details?: {
    status?: string;
    url?: string;
    has_captcha?: boolean;
    [key: string]: any;
  } | null;
}


