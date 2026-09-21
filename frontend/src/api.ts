import type {
  PersonCandidate,
  PersonProfile,
  ResearchStartResponse,
  AddSourceResponse,
  AddSourcePasteResponse,
  CrawlResponse,
  DraftResponse,
  DraftAudit,
  NotabilityResult,
} from "./types";

// Configurable for mobile builds (set VITE_API_BASE env var to the device's server IP)
const BASE = (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE) ?? "/api";

async function apiPost<T>(path: string, body: unknown, params?: Record<string, string>): Promise<T> {
  const url = params
    ? `${BASE}${path}?${new URLSearchParams(params).toString()}`
    : `${BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface IdentifyResult {
  kind: "identity" | "web";
  title: string;
  url: string;
  snippet: string;
  publisher: string;
  wikidata_id?: string | null;
  wikipedia_url?: string | null;
  photo_url?: string | null;
  birth_year?: string | null;
  nationality?: string | null;
  field?: string | null;
  affiliation?: string | null;
}

export async function identifyPerson(
  name: string, field: string | null, affiliation: string | null
): Promise<{ results: IdentifyResult[]; wiki_status: import("./types").WikiStatus | null }> {
  const data = await apiPost<{ results: IdentifyResult[]; wiki_status: import("./types").WikiStatus | null }>(
    "/identify", { name, field, affiliation });
  return data;
}

export async function startResearch(
  candidate: PersonCandidate,
): Promise<ResearchStartResponse> {
  return apiPost("/research/start", {
    name: candidate.name,
    wikidata_id: candidate.wikidata_id,
    wikipedia_url: candidate.wikipedia_url,
    photo_url: candidate.photo_url,
    field: candidate.field,
    affiliation: candidate.affiliation,
    nationality: candidate.nationality,
    birth_year: candidate.birth_year,
  });
}

export async function getSession(name: string): Promise<PersonProfile> {
  const data = await apiGet<{ profile: PersonProfile }>(`/session/${encodeURIComponent(name)}`);
  return data.profile;
}

export async function addSource(profileName: string, url: string): Promise<AddSourceResponse> {
  return apiPost("/research/add-source", { profile_name: profileName, url });
}

export async function fetchFromBrowser(profileName: string): Promise<AddSourceResponse> {
  return apiPost("/research/fetch-from-browser", { profile_name: profileName });
}

export async function fetchBlockedSources(profileName: string): Promise<{
  fetched: string[];
  walls: string[];
  profile?: PersonProfile;
  notability?: NotabilityResult | null;
}> {
  return apiPost("/research/fetch-blocked", { profile_name: profileName });
}

export async function skipSuggestion(profileName: string, url: string): Promise<{ ok: boolean }> {
  return apiPost("/research/skip-suggestion", { profile_name: profileName, url });
}

export async function addSourcePaste(
  profileName: string,
  url: string,
  pastedText: string,
): Promise<AddSourcePasteResponse> {
  return apiPost("/research/add-source-paste", {
    profile_name: profileName,
    url,
    pasted_text: pastedText,
  });
}

export async function deepCrawl(
  profileName: string,
  seedUrls: string[],
  keywords: string[],
  maxNodes = 40,
  maxDepth = 3,
): Promise<CrawlResponse> {
  return apiPost("/research/crawl", {
    profile_name: profileName,
    seed_urls: seedUrls,
    keywords,
    max_nodes: maxNodes,
    max_depth: maxDepth,
  });
}

export async function verifyClaim(
  profileName: string,
  claimIndex: number,
  action: "confirm" | "edit" | "skip" | "approve_draft" | "remove_draft" | "edit_draft_text",
  editedText?: string,
  actor: "human" | "agent" = "human",
  settledQuote?: string,
): Promise<{ claim: import("./types").Claim }> {
  return apiPost(
    "/research/verify-claim",
    {
      claim_index: claimIndex,
      action,
      edited_text: editedText ?? null,
      actor,
      settled_quote: settledQuote ?? null,
    },
    { name: profileName },
  );
}

export async function batchVerifyClaims(
  profileName: string,
  action: "approve_all_usable" | "confirm_all" | "skip_unverified",
  actor: "human" | "agent" = "human",
): Promise<{ profile: PersonProfile; updated_count: number }> {
  return apiPost(
    "/research/batch-verify-claims",
    { action, actor },
    { name: profileName },
  );
}

export async function verifySource(
  profileName: string,
  url: string,
  verified: boolean,
  actor: "human" | "agent" = "human",
): Promise<{ ok: boolean; source?: import("./types").Source; new_claims: import("./types").Claim[]; missing_slots: string[]; notability: import("./types").NotabilityResult | null }> {
  return apiPost("/research/source/verify", { profile_name: profileName, url, verified, actor });
}

export async function verifySourceLevel(
  profileName: string,
  url: string,
  level: "liveness" | "identity" | "provenance" | "all",
  options?: {
    actor?: "human" | "agent";
    status?: string;
    note?: string;
    coverage_depth?: "unassessed" | "passing_mention" | "significant";
    editorial_origin?: string;
  },
): Promise<{ ok: boolean; source: import("./types").Source; notability?: import("./types").NotabilityResult | null }> {
  return apiPost("/research/source/verify-level", {
    profile_name: profileName,
    url,
    level,
    actor: options?.actor ?? "human",
    status: options?.status,
    note: options?.note,
    coverage_depth: options?.coverage_depth,
    editorial_origin: options?.editorial_origin,
  });
}

export async function getVerificationSummary(profileName: string): Promise<import("./types").VerificationSummaryResponse> {
  return apiGet<import("./types").VerificationSummaryResponse>(`/research/verification-summary?profile_name=${encodeURIComponent(profileName)}`);
}

export async function assessSource(
  profileName: string,
  url: string,
  coverageDepth: import("./types").Source["coverage_depth"],
  editorialOrigin: string,
  researchNotes: string,
  actor: "human" | "agent" = "human",
): Promise<{ source: import("./types").Source; notability: NotabilityResult | null }> {
  return apiPost("/research/source/assess", {
    profile_name: profileName,
    url,
    coverage_depth: coverageDepth,
    editorial_origin: editorialOrigin || null,
    research_notes: researchNotes,
    actor,
  });
}
export async function rejectSource(
  profileName: string,
  url: string,
  reason: string,
): Promise<{ removed_claim_count: number; sources: import("./types").Source[]; claims: import("./types").Claim[]; notability: import("./types").NotabilityResult }> {
  return apiPost("/research/source/reject", { profile_name: profileName, url, reason });
}

export async function getDraftAudit(profileName: string): Promise<DraftAudit> {
  const data = await apiGet<{ audit: DraftAudit }>(`/draft/audit/${encodeURIComponent(profileName)}`);
  return data.audit;
}

export async function getDraftLinks(profileName: string): Promise<import("./types").DraftLinksResult> {
  const data = await apiPost<{ links: import("./types").DraftLink[]; wiki_links?: import("./types").DraftWikilink[] }>("/draft/links", { profile_name: profileName });
  return {
    links: data.links || [],
    wiki_links: data.wiki_links || [],
  };
}

export async function getDraftPreview(profileName: string): Promise<string> {
  const data = await apiPost<{ html: string }>("/draft/preview", { profile_name: profileName });
  return data.html;
}

export async function getDraftQa(profileName: string): Promise<import("./types").DraftQaReport> {
  return apiPost("/draft/qa", { profile_name: profileName });
}

export async function generateDraft(profileName: string): Promise<DraftResponse> {
  return apiPost("/draft", { profile_name: profileName });
}

export interface ClaimCoverage {
  claim_index: number;
  field: string;
  text: string;
  date_context: string | null;
  source_url: string | null;
  covered: boolean;
  score: number;
  note: string;
}

export interface ArticleProposal {
  article_title: string;
  article_url: string;
  article_excerpt: string;
  covered_count: number;
  missing_count: number;
  coverage: ClaimCoverage[];
}

export async function getArticleProposal(profileName: string): Promise<ArticleProposal> {
  const data = await apiPost<{ proposal: ArticleProposal }>("/research/article-proposal", { profile_name: profileName });
  return data.proposal;
}

export interface SessionSummary {
  id: string | null;
  name: string;
  field: string | null;
  affiliation: string | null;
  photo_url: string | null;
  source_count: number;
  claim_count: number;
  notability_label: string;
  notability_score: number;
  saved_at: string | null;
  file: string;
}

/** Stable session reference: the immutable session id when present, else the name. */
export function profileRef(profile: { session_id?: string | null; name: string }): string {
  return profile.session_id ?? profile.name;
}

export async function listSessions(): Promise<SessionSummary[]> {
  const data = await apiGet<{ sessions: SessionSummary[] }>("/sessions");
  return data.sessions;
}

export async function resumeSession(ref: string): Promise<{ profile: PersonProfile; wiki_status: import("./types").WikiStatus }> {
  return apiPost("/sessions/resume", { file: ref, session_id: ref });
}

export async function deleteSession(ref: string): Promise<void> {
  await apiDelete(`/sessions/${encodeURIComponent(ref)}`);
}

export interface TargetedSearchResponse {
  sources: import("./types").Source[];
  new_claims: import("./types").Claim[];
  missing_slots: string[];
  notability: import("./types").NotabilityResult;
}

export async function addDocumentFact(
  profileName: string,
  field: string,
  text: string,
): Promise<{ claim: import("./types").Claim }> {
  return apiPost("/research/add-document-fact", { profile_name: profileName, field, text });
}

export async function targetedSearch(
  profileName: string,
  slot: string,
  hint?: string,
): Promise<TargetedSearchResponse> {
  return apiPost("/research/targeted-search", {
    profile_name: profileName,
    slot,
    hint: hint ?? null,
  });
}

export interface ResearcherIdsResponse {
  researcher_ids: Record<string, string>;
  confirmed_ids: Record<string, boolean>;
}

export async function findResearcherIds(profileName: string): Promise<ResearcherIdsResponse> {
  return apiPost("/research/find-researcher-ids", { profile_name: profileName });
}

export interface RefreshPapersResponse {
  new_source_count: number;
  new_claim_count: number;
  sources: import("./types").Source[];
  claims: import("./types").Claim[];
  notability: import("./types").NotabilityResult;
  researcher_ids: Record<string, string>;
  confirmed_ids: Record<string, boolean>;
}

export async function refreshPapers(
  profileName: string,
  idType: string,
  idValue: string,
  confirm?: boolean,
): Promise<RefreshPapersResponse> {
  return apiPost("/research/refresh-papers", {
    profile_name: profileName,
    id_type: idType,
    id_value: idValue,
    confirm: confirm ?? false,
  });
}

export async function suggestUrls(profileName: string): Promise<import("./types").UrlSuggestion[]> {
  const data = await apiPost<{ suggestions: import("./types").UrlSuggestion[] }>("/research/suggest", { profile_name: profileName });
  return data.suggestions;
}

export interface AutoEnrichResponse {
  ok: boolean;
  added_source_count: number;
  added_claim_count: number;
  missing_slots: string[];
  notability: import("./types").NotabilityResult;
}

export async function autoEnrich(profileName: string): Promise<AutoEnrichResponse> {
  return apiPost("/research/auto-enrich", { profile_name: profileName });
}

export async function getLifecycleAudit(profileName: string): Promise<import("./types").FullLifecycleAudit> {
  return apiGet(`/research/lifecycle-audit?profile_name=${encodeURIComponent(profileName)}`);
}

export async function getDiscardedSources(
  profileName: string,
  reason?: string,
): Promise<{ count: number; discarded: import("./types").DiscardedSource[] }> {
  const query = reason ? `&reason=${encodeURIComponent(reason)}` : "";
  return apiGet(`/research/discarded-sources?profile_name=${encodeURIComponent(profileName)}${query}`);
}

export async function recoverDiscardedSource(
  profileName: string,
  url: string,
): Promise<{ ok: boolean; recovered: import("./types").DiscardedSource | null }> {
  return apiPost("/research/source/recover-discarded", { profile_name: profileName, url });
}

export async function getMobileBridgeStatus(): Promise<import("./types").MobileBridgeStatus> {
  return apiGet("/research/mobile-bridge-status");
}

export async function getForensicsSummary(profileName: string): Promise<import("./types").ForensicsSummaryResponse> {
  return apiGet(`/forensics/summary?profile_name=${encodeURIComponent(profileName)}`);
}

export async function addInvestigationPivot(
  profileName: string,
  pivot: {
    pivot_type: string;
    title: string;
    description?: string;
    time_period?: string | null;
    location?: string | null;
    associated_entities?: string[];
    actor?: "human" | "agent";
  }
): Promise<{ ok: boolean; pivot: import("./types").InvestigationPivot; pivots: import("./types").InvestigationPivot[] }> {
  return apiPost("/forensics/pivots", { profile_name: profileName, ...pivot });
}

export async function deleteInvestigationPivot(
  profileName: string,
  pivotId: string
): Promise<{ ok: boolean; pivots: import("./types").InvestigationPivot[] }> {
  return apiDelete(`/forensics/pivots/${encodeURIComponent(pivotId)}?profile_name=${encodeURIComponent(profileName)}`);
}

export async function addAuxiliaryLead(
  profileName: string,
  lead: {
    pivot_id?: string | null;
    title: string;
    url?: string | null;
    category?: string;
    lead_notes?: string;
    source_snippet?: string | null;
    automated_query?: string | null;
    actor?: "human" | "agent";
  }
): Promise<{ ok: boolean; lead: import("./types").AuxiliaryLead; leads: import("./types").AuxiliaryLead[] }> {
  return apiPost("/forensics/leads", { profile_name: profileName, ...lead });
}

export async function updateAuxiliaryLead(
  profileName: string,
  leadId: string,
  updates: {
    status?: "lead" | "inspected" | "corroborated" | "dead_end";
    lead_notes?: string;
    source_snippet?: string;
    url?: string;
    actor?: "human" | "agent";
  }
): Promise<{ ok: boolean; lead: import("./types").AuxiliaryLead; leads: import("./types").AuxiliaryLead[] }> {
  return apiPatch(`/forensics/leads/${encodeURIComponent(leadId)}`, { profile_name: profileName, lead_id: leadId, ...updates });
}

export async function deleteAuxiliaryLead(
  profileName: string,
  leadId: string
): Promise<{ ok: boolean; leads: import("./types").AuxiliaryLead[] }> {
  return apiDelete(`/forensics/leads/${encodeURIComponent(leadId)}?profile_name=${encodeURIComponent(profileName)}`);
}

export async function runForensicSweep(
  profileName: string,
  pivotId?: string | null,
  actor?: "human" | "agent"
): Promise<{ ok: boolean; new_leads_count: number; leads: import("./types").AuxiliaryLead[] }> {
  return apiPost("/forensics/sweep", { profile_name: profileName, pivot_id: pivotId, actor });
}

export async function promoteLeadToSource(
  profileName: string,
  leadId: string,
  actor: "human" | "agent" = "human"
): Promise<{ ok: boolean; promoted_source: import("./types").Source; lead: import("./types").AuxiliaryLead; already_existed?: boolean }> {
  return apiPost(`/forensics/leads/${encodeURIComponent(leadId)}/promote-to-source`, {
    profile_name: profileName,
    lead_id: leadId,
    actor,
  });
}

export async function generateForensicInquiries(
  profileName: string
): Promise<{ ok: boolean; new_inquiries_count: number; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPost("/forensics/inquiries/generate", { profile_name: profileName });
}

export async function addForensicInquiry(
  profileName: string,
  inquiry: {
    fact_anchor: string;
    domain?: string;
    deductive_question: string;
    expected_paper_trails?: string[];
    probe_queries?: string[];
    actor?: "human" | "agent";
  }
): Promise<{ ok: boolean; inquiry: import("./types").ForensicInquiry; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPost("/forensics/inquiries", { profile_name: profileName, ...inquiry });
}

export async function updateForensicInquiry(
  profileName: string,
  inquiryId: string,
  updates: {
    status?: "open" | "probed" | "confirmed" | "unarchived_offline";
    findings_summary?: string;
    corroborating_links?: string[];
    actor?: "human" | "agent";
  }
): Promise<{ ok: boolean; inquiry: import("./types").ForensicInquiry; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPatch(`/forensics/inquiries/${encodeURIComponent(inquiryId)}`, { profile_name: profileName, inquiry_id: inquiryId, ...updates });
}

export async function deleteForensicInquiry(
  profileName: string,
  inquiryId: string
): Promise<{ ok: boolean; inquiries: import("./types").ForensicInquiry[] }> {
  return apiDelete(`/forensics/inquiries/${encodeURIComponent(inquiryId)}?profile_name=${encodeURIComponent(profileName)}`);
}

export async function probeForensicInquiry(
  profileName: string,
  inquiryId: string,
  actor: "human" | "agent" = "human"
): Promise<{ ok: boolean; inquiry: import("./types").ForensicInquiry; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPost(`/forensics/inquiries/${encodeURIComponent(inquiryId)}/probe`, { profile_name: profileName, inquiry_id: inquiryId, actor });
}

export async function probeAllForensicInquiries(
  profileName: string,
  actor: "human" | "agent" = "human"
): Promise<{ ok: boolean; probed_count: number; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPost(`/forensics/inquiries/probe-all`, { profile_name: profileName, actor });
}

export async function getPublicRecordsAtlas(): Promise<import("./types").AtlasResponse> {
  return apiGet("/forensics/atlas");
}

export async function getSubjectRecordMatrix(
  profileName: string
): Promise<import("./types").AtlasMatrixResponse> {
  return apiGet(`/forensics/atlas/matrix?profile_name=${encodeURIComponent(profileName)}`);
}

export async function expandCivicInquiries(
  profileName: string
): Promise<{ ok: boolean; added_count: number; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPost("/forensics/inquiries/expand-civic", { profile_name: profileName });
}

export async function registerPublicRepository(
  repo: Partial<import("./types").PublicRecordRepository>
): Promise<{ ok: boolean; repository: import("./types").PublicRecordRepository; total_repositories: number }> {
  return apiPost("/forensics/atlas/repository", repo);
}

export async function deletePublicRepository(
  categoryId: string
): Promise<{ ok: boolean; deleted_id: string; total_repositories: number }> {
  return apiDelete(`/forensics/atlas/repository/${encodeURIComponent(categoryId)}`);
}

export async function logInquiryFailure(
  profileName: string,
  inquiryId: string,
  failureData: {
    failure_mode: string;
    failure_reason: string;
    learned_lesson: string;
    associated_repository_id?: string;
    actor?: "human" | "agent";
  }
): Promise<{ ok: boolean; inquiry: import("./types").ForensicInquiry; inquiries: import("./types").ForensicInquiry[] }> {
  return apiPost("/forensics/inquiries/log-failure", {
    profile_name: profileName,
    inquiry_id: inquiryId,
    ...failureData,
  });
}



export type FetchTelemetry = {
  rows: number;
  avg_latency_ms: number;
  max_latency_ms: number;
  throttle_events: number;
  by_transport: Record<string, { count: number; latency_ms: number; throttles: number; avg_latency_ms?: number }>;
  pending_rechecks: { host: string; recheck_at: string; wait_s: number }[];
};

export async function getFetchTelemetry(): Promise<FetchTelemetry> {
  const r = await fetch("/api/ops/fetch-telemetry");
  if (!r.ok) throw new Error(`telemetry fetch failed: ${r.status}`);
  return r.json();
}
