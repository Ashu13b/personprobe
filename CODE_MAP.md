<!-- context-kit CODE_MAP · v0.2.0 · generated 2026-11-03 16:08 UTC · sha a4a0fda · host instance-trading-bot-restored -->

# CODE_MAP

Symbol index (skim-grade). Consult before Grep/Read.

## Composition
- Python — 116 files · 1024 symbols
- TypeScript — 35 files · 293 symbols
- HTML — 2 files · 3 symbols
- JavaScript — 1 files · 0 symbols
- CSS — 1 file (unindexed)
- Shell Script — 1 file (unindexed)
_Total: 156 files · 1320 symbols across 6 languages._


## Compartments
- `auto` — dynamic (git files in play + 2-hop import neighborhood)

Run `ck compartment <name>` to load a compartment's warm symbol index.

<!-- ck:router -->

### ./
- `browser_home.html` — #status, #open-desktop
- `browser_server.py` — PROFILE_DIR, XVFB_DISPLAY, PORT, _UA, def looks_like_wall, class _Cmd, _q, _headed, _running, _xvfb, … +29 more
- `wiki_draft_checker.py` — class _UnsafeRedirect, class _SafeRedirectHandler(redirect_request), class CheckFinding, class LinkAuditResult, class SentenceGroundingResult, class DraftCheckerReport, PEACOCK_TERMS, PRIVACY_PATTERNS, DIRTY_TITLE_PATTERNS, ISO_DATE_PATTERN, … +4 more
### adapters/
- `adapters/wiki/article_compare.py` — WIKI_API, HEADERS, STOPWORDS, _COVERAGE_THRESHOLD, class ClaimCoverage, class ArticleProposal, def title_from_url, def fetch_article_text, def _tokens, def claim_coverage, … +1 more
- `adapters/wiki/draft.py` — class DraftIssue, class DraftEvidence, class DraftAudit, _NOISE_PATTERNS, _ROLE_WORDS, _CAREER_ACTIVITY_WORDS, _INSTITUTION_WORDS, _PUBLICATION_WORDS, _BIRTH_SUBJECT_NOISE, _RESEARCH_ACTIONS, … +25 more
- `adapters/wiki/draft_hi.py` — def _hindi_infobox, def _render_hindi_items, def render_hindi_draft
- `adapters/wiki/draft_qa.py` — Severity, class Finding, class QaReport(passed, counts), _WEAK_RELIABILITIES, _LEAD_END, _ATTRIBUTION, _REF_SNIPPET, _CITE_URL, _CITE_TITLE, _CITE_DATE, … +9 more
- `adapters/wiki/draft_verifier.py` — class DraftLink, _REF_OPEN, _REF_CLOSE, _CITE_FIELD, _EXTERNAL_LINK, def extract_draft_links, def check_draft_links, def _check_links_via_requests, def render_preview, class DraftWikilink, … +4 more
- `adapters/wiki/wiki_check.py` — HEADERS, WIKI_API, class WikiStatus, def draft_generation_allowed, def check_title_for, def check_existing_page, def _page_exists, def _deletion_note
### backend/
- `backend/main.py` — api_app, def lifespan, app, _TRUST_ALL_CLIENTS, _TAILSCALE_CGNAT, def _client_is_trusted, class _TrustedNetworkMiddleware(__init__, __call__), FRONTEND_DIST
- `backend/pipelines.py` — def _add_sd_article, def _add_sd_author_profile
- `backend/routes_browser.py` — browser_router, _last_captcha_solved, def captcha_solved, def last_captcha_solved
- `backend/routes_draft.py` — draft_router, def draft_audit, def generate_draft, def draft_links, def draft_preview, def draft_qa, def draft_verify, def draft_checker_endpoint
- `backend/routes_forensics.py` — forensics_router, def get_forensics_summary, def add_pivot, def delete_pivot, def add_auxiliary_lead, def update_auxiliary_lead, def promote_lead_to_source, def delete_auxiliary_lead, def run_forensic_sweep, def generate_inquiries, … +12 more
- `backend/routes_ops.py` — ops_router, def get_fetch_telemetry
- `backend/routes_research.py` — research_router, def _namesake_check, def identify, def _find_resumable_session, def _enrich_and_flag_sources, def _populate_initial_sources, def research_start, def add_source, def add_document_fact, def add_sourced_claim, … +33 more
- `backend/routes_sessions.py` — sessions_router, def resume_session, def list_sessions, def delete_session
- `backend/schemas.py` — class IdentifyRequest, class ResearchRequest, class AddSourceRequest, class AddNamesakeRequest, class DeleteNamesakeRequest, class AssessSourceRequest, class VerifySourceLevelRequest, class AddDocumentFact, class AddSourcedClaimRequest, class VerifyClaimRequest, … +19 more
- `backend/store.py` — SESSIONS_DIR, _sessions, _wiki_statuses, _lock, _llm, def llm, def _new_session_id, def _ensure_session_id, def _session_path, def _resolve_profile, … +9 more
### engine/
- `engine/agent_llm.py` — AGENT_JOBS_DIR, def _job_id, class AgentProvider(__init__, complete), def pending_jobs, def answer_job
- `engine/author_check.py` — CROSSREF_API, TIMEOUT, def name_variants, def _normalise, def _author_matches_variants, def _affiliation_matches, def check_doi_authors, def extract_doi
- `engine/canonical_url.py` — DOMAIN_ALIAS_MAP, TRACKING_PARAM_PREFIXES, def canonical_url, def is_same_url
- `engine/claim_selection.py` — _CATEGORY_RANK, _DEPTH_BONUS, _TRUST_BONUS, def source_citation_rank, def rank_sources_for_fact, def build_claim_clusters, READY, NEEDS_CONFIRM, NEEDS_SOURCE, BLOCKED, … +3 more
- `engine/classifier.py` — _RS_DOMAINS, _PRIMARY_DOMAINS, _SELF_DOMAINS, _UNRELIABLE_DOMAINS, def _domain_classify, SYSTEM, def classify_sources
- `engine/coauthor_network.py` — def _coauthor_mention_note, def extract_subject_mentions, def screen_coauthor_page, def coauthor_source_batch
- `engine/crawler.py` — TIMEOUT, S2_API, class SourceNode, class SourceGraph(to_sources), def crawl, def _extract_meta, def _extract_links, def _extract_dois, def _extract_entities, def _count_mentions, … +5 more
- `engine/discarded_registry.py` — def record_discarded, def is_discarded, def is_known_or_discarded, def get_known_and_discarded_canonical_urls, def recover_discarded, def get_discarded_by_reason
- `engine/doc_metadata.py` — def parse_pdf_date, def extract_pdf_metadata
- `engine/evidence.py` — def apply_quote_candidates
- `engine/extractor.py` — WIKI_SLOTS, SLOT_SOURCE_HINTS, def find_missing_slots, SYSTEM, def _validate_and_filter_claims, def filter_person_snippets, def extract_claims, def _deduplicate
- `engine/fetch_telemetry.py` — LOG_PATH, DEFAULT_DELAY_S, THROTTLE_DELAY_S, _THROTTLE_WINDOW_S, MAX_HOST_ATTEMPTS, def _host, def record, def timed, class _Timer(__init__, __enter__, __exit__), def recent_throttles, … +8 more
- `engine/fetcher.py` — HEADERS, BOT_HEADERS, TIMEOUT, MAX_FETCH_BYTES, BOT_WALL_RE, def is_safe_public_url, def check_liveness, def get_wayback_url, class FetchResult(__init__), _BROWSER_BASES, … +9 more
- `engine/fetcher_browser.py` — _SESSION_DIR, _LAUNCH_ARGS, _STEALTH_JS, _UA, def fetch_with_browser
- `engine/forensics.py` — class LifeEvent, class SubjectContext, def get_valid_indian_states, def _extract_field_keywords, def build_subject_context, def generate_pivot_id, def generate_lead_id, def generate_inquiry_id, def seed_default_pivots, def generate_forensic_queries_for_pivot, … +4 more
- `engine/identifier.py` — HEADERS, WIKI_API, WIKIDATA_API, def fetch_wikidata_photo_by_id, def find_candidates, _HONORIFICS, def _significant_tokens, def _name_matches, def _search_wikipedia, def _search_wikidata, … +5 more
- `engine/lifecycle_audit.py` — class StageAuditItem, class FullLifecycleAudit, def _host, def audit_discovery_stage, def audit_provenance_stage, def audit_claims_stage, def audit_draft_stage, def audit_full_lifecycle
- `engine/link_extractor.py` — _PROFILE_DOMAINS, _PROFILE_PATH_FRAGMENTS, def extract_profile_links
- `engine/llm.py` — class LLMProvider(complete), class ClaudeProvider(__init__, complete), class GeminiProvider(__init__, complete), class VertexClaudeProvider(__init__, complete), class LocalProvider(complete), class NullProvider(complete), class StubProvider(complete, _classify, _extract), _stub_warned, _agent_warned, def _agent_provider, … +4 more
- `engine/mobile_bridge.py` — ANDROID_BROWSER_DIR, logger, _client, def get_mobile_client, def is_mobile_bridge_available, def fetch_via_mobile_bridge
- `engine/models.py` — class SourceReliability, class VerificationState, class VerificationActor, class VerificationLevel, class VerificationLogEntry, class Source, class DiscardedSource, class KnownNamesake, class Claim, class NotabilityResult, … +11 more
- `engine/multilingual_search.py` — _NATIONALITY_TO_LANGUAGES, _INDIC_PHONETIC_MAP, _LOCALIZED_SLOT_TERMS, _COUNTRY_NEWS_OUTLETS, def detect_languages, def transliterate_name, def get_regional_news_outlets, def build_bilingual_queries
- `engine/name_verifier.py` — class NameVerificationResult, def generate_name_variants, def verify_name_in_content, def _is_initials_only_variant, def assess_namesake_risk
- `engine/notability.py` — S2_API, _S2_TTL_SECONDS, _s2_cache, def score_notability, def _semantic_scholar_signals, def _fetch_semantic_scholar
- `engine/openalex.py` — OPENALEX_API_BASE, OPENALEX_HEADERS, def search_author, def get_author_works, def convert_works_to_sources
- `engine/osint_dorks.py` — class OsintDork, def generate_osint_dorks
- `engine/provenance.py` — HIGH_TRUST_DOMAINS, MEDIUM_TRUST_DOMAINS, UNTRUSTED_DOMAINS, def normalize_url, MEDIUM_TRUST_DOMAINS, UNTRUSTED_DOMAINS, def get_domain_trust, def classify_source_provenance, def evaluate_claim_trust
- `engine/public_records_atlas.py` — REGISTRY_DIR, REGISTRY_FILE, BUILTIN_REPOSITORIES, def _ensure_registry_dir, def load_custom_repositories, def save_custom_repositories, def register_public_repository, def delete_custom_repository, def record_repository_learning, def get_public_records_atlas, … +2 more
- `engine/publishers.py` — def extract_domain, INDEPENDENT_NEWS_DOMAINS, ACADEMIC_PUBLISHER_DOMAINS, PRIMARY_OR_INSTITUTIONAL_DOMAINS, RECORD_REGISTRY_DOMAINS, SELF_PUBLISHED_DOMAINS, UNRELIABLE_DOMAINS, def matches_domain_set, def is_independent_secondary_news, def is_primary_or_institutional
- `engine/quote_backfill.py` — _MARKUP_RE, _NAV_RE, _STOP, def _tokens, def _norm_dates, def sentences, def best_quote, def collect_claims_needing_quotes
- `engine/relevance.py` — _WRONG_PERSON_SIGNALS, _ACADEMIC_FETCHED_BY, _DOI_PATTERNS, _SHORTENERS, _PRESENTATION_SUBDOMAINS, def _redirect_norm, def is_meaningful_redirect, _INDIC_NAME_MAP, _INDIC_CONTEXT_TERMS, def _significant_name_tokens, … +2 more
- `engine/researcher.py` — HEADERS, S2_API, GOOGLE_CSE_URL, _NEWS_OUTLETS, _DISAMBIG_STOPWORDS, _JUNK_URL_RE, def is_junk_source_url, def _disambiguator, def _sweep_news, def fetch_auto_sources, … +12 more
- `engine/researcher_ids.py` — HEADERS, OA_HEADERS, _ORCID_RE, _SCHOLAR_RE, _SCOPUS_RE, _SD_AUTHOR_RE, _RESEARCHGATE_RE, _S2_AUTHOR_RE, _SD_PII_RE, def extract_ids_from_sources, … +12 more
- `engine/saturation.py` — _STOPWORDS, _YEAR_RE, _WORD_RE, def _tokenize, def _ngrams, def calculate_claim_similarity, def cluster_claims, def analyze_research_saturation
- `engine/suggester.py` — _SLOT_PRIORITY, _PAYWALLED, _NEEDS_BROWSER, def _fetchability, def is_profile_url, def _classify_source_type, def _relevance, def _completion_value, def _extract_first_year, def detect_timeline_gaps, … +9 more
- `engine/workflow.py` — SOURCE_STAGE, SOURCE_STAGE_ORDER, def advance_source_stage
### frontend/
- `frontend/index.html` — #root
- `frontend/src/App.tsx` — ErrorBoundaryProps, ErrorBoundaryState, ErrorBoundary, constructor, getDerivedStateFromError, componentDidCatch, render, Stage, MainApp, handleMessage, … +5 more
- `frontend/src/api.ts` — apiPost, apiGet, apiDelete, apiPatch, IdentifyResult, identifyPerson, startResearch, getSession, addSource, fetchFromBrowser, … +71 more
- `frontend/src/components/ArticleProposal.tsx` — ArticleProposalView
- `frontend/src/components/BookmarkletCard.tsx` — BookmarkletCard, handleCopy
- `frontend/src/components/ClaimsReview.tsx` — FilterTab, ClaimsReview, toggleTrail, doVerify, handleBatchAction, ActionBtn
- `frontend/src/components/DiscardedTab.tsx` — Props, DiscardedTab, loadDiscarded, handleRecover
- `frontend/src/components/DraftAndOutputs.tsx` — Props, OutputSubTab, DraftAndOutputs, handleCopyWikitext, handleCopyAfc, handleCopyDossier, handleDownloadDossier
- `frontend/src/components/DraftChecker.tsx` — CheckFinding, LinkAuditResult, SentenceGroundingResult, DraftCheckerReport, Props, DraftChecker, runAudit
- `frontend/src/components/DraftLinks.tsx` — DraftLinkRow, DraftWikilinkRow, DraftLinks, toggleVerified
- `frontend/src/components/DraftPreview.tsx` — Props, DraftPreview, copy
- `frontend/src/components/DraftQa.tsx` — DraftQa
- `frontend/src/components/EvidenceWorkspace.tsx` — Props, EvidenceWorkspace, handleAddUrl, handleAddPaste, handleCrawl, handleAutoEnrichSlots, handleSearchOpenAlex, handleImportOpenAlex, refreshProfile
- `frontend/src/components/FactClusters.tsx` — FactClusters, useBest
- `frontend/src/components/FetchOpsPanel.tsx` — FetchOpsPanel, load
- `frontend/src/components/ForensicCanvas.tsx` — Props, ForensicCanvas, handleGenerateInquiries, handleProbeInquiry, handleProbeAllInquiries, handleExpandCivic, handleToggleAtlas, handleAddRepoSubmit, handleDeleteRepo, handleLogFailureSubmit, … +10 more
- `frontend/src/components/GuideTab.tsx` — GuideTab
- `frontend/src/components/LifecycleAuditCard.tsx` — Props, LifecycleAuditCard, handleStageClick, loadData
- `frontend/src/components/LivingDossier.tsx` — Props, DossierViewMode, BioChapter, LivingDossier
- `frontend/src/components/NamesakeRegistry.tsx` — NamesakeRegistry, load, handleAdd, handleDelete
- `frontend/src/components/ProfileTab.tsx` — ProfileTab, setMode, handleSearch, handleAddUrl, handleManual, ResearcherIdsStrip
- `frontend/src/components/SourceCard.tsx` — SourceCard, handleVerify, handleReject, handleAssess, handleVerifyIdentity, RelevanceBadge, FetchedByTag, AuthorMatchBadge, PipeStep, PipeConnector
- `frontend/src/components/TimelineTab.tsx` — parseFirstYear, TimelineTab, TLEvent, GapInfo, EventRow, GapRow, handleFillGap
- `frontend/src/components/WorkspaceCards.tsx` — Expander, NotabilityBadge, NotabilityCard, SaturationCard, DraftReadinessCard, ChecklistCard, TabBtn
- `frontend/src/components/WorkspaceStatusBanner.tsx` — WorkspaceStatusBanner
- `frontend/src/components/slotMeta.ts` — FillMode
- `frontend/src/pages/DraftPage.tsx` — Props, Tab, DraftPage, handleCopy, handleCopyAfc, TabBtn, SourceRow
- `frontend/src/pages/HubPage.tsx` — Props, PrimarySpace, HubPage, handleGenerateDraft, markLinkOpened
- `frontend/src/pages/IdentifyPage.tsx` — Props, View, IdentifyPage, handleResume, handleDelete, handleSearch, handleConfirm, handleConfirmIdentity
- `frontend/src/pages/ResearchPage.tsx` — Props, ResearchPage, Spinner
- `frontend/src/thematic.ts` — ThematicCategory, ThematicCategoryMeta, getSourceCategories, computeCategoryCounts, filterSources
- `frontend/src/types.ts` — PersonCandidate, SourceReliability, VerificationState, SourceFetchedBy, VerificationActor, VerificationLevel, VerificationLogEntry, Source, Claim, VerificationSummaryResponse, … +37 more
- `frontend/src/url.ts` — normalizeUrl, getHostname, safeHref
- `frontend/src/workflow.ts` — WorkspaceMode, WorkspaceTone, WorkspaceRoute, getWorkspaceRoute, canGenerateDraft, getDraftDestination
### scripts/
- `scripts/backfill_quotes.py` — API, SESSION_ID, PRIORITY_FIELDS, def page_text, def cmd_main
- `scripts/bulk_ingest_candidates.py` — API_BASE, SESSION_ID, SESSION_FILE, def api_post, def load_existing_urls, def main
- `scripts/coauthor_harvest.py` — API, def harvest_coauthors, def payload_url
- `scripts/crawl_link_bucket.py` — API_BASE, SESSION_ID, SESSION_FILE, SEEDS, WRONG_PERSON_ENTITIES, def load_existing_urls, def normalize_url, def is_valid_candidate, def verify_dr_yadav, def api_post, … +1 more
- `scripts/deduplicate_session.py` — API_BASE, SESSION_ID, SESSION_FILE, DOMAIN_ALIAS_MAP, def canonical_url, def deduplicate
- `scripts/forensic_hunter.py` — FORENSIC_QUERIES, def clean_google_url, def main
- `scripts/generate_draft.py` — root_dir, session_file, data, profile, audit, wikitext, out_en
- `scripts/google_harvest_phone.py` — SESSION_ID, SESSION_FILE, GOOGLE_QUERIES, def load_existing_canonical_urls, def main
- `scripts/harvest_awards_and_repos.py` — SESSION_ID, SESSION_FILE, QUERIES, def load_existing_urls, def main
- `scripts/harvest_deductive_sources.py` — SESSION_ID, SESSION_FILE, DEDUCTIVE_QUERIES, JUNK_DOMAINS, def load_existing_sources, def extract_publisher, def main
- `scripts/harvest_media_and_icar.py` — SESSION_ID, SESSION_FILE, QUERIES, def load_existing_urls, def main
- `scripts/harvest_national_press.py` — SESSION_ID, SESSION_FILE, NATIONAL_PRESS_QUERIES, def load_existing_canonical_urls, def main
- `scripts/harvest_researchgate_publications.py` — API_BASE, SESSION_ID, SESSION_FILE, def api_post, def load_existing_urls, def main
- `scripts/harvest_round2_named.py` — SESSION_ID, SESSION_FILE, OUTPUT_FILE, TARGET_QUERIES, NAME_PATTERNS, RELEVANCE_PATTERNS, def load_existing_urls, def name_matches, def relevance_matches, def main
- `scripts/harvest_strictly_named_links.py` — SESSION_ID, SESSION_FILE, OUTPUT_FILE, QUERIES, NAME_PATTERNS, RELEVANCE_PATTERNS, def load_existing_urls, def name_matches, def relevance_matches, def main
- `scripts/harvest_unconfirmed_inquiries.py` — SESSION_ID, SESSION_FILE, TARGET_QUERIES, def load_session, def save_session, def main
- `scripts/ingest_awards_candidates.py` — SESSION_ID, SESSION_FILE, CANDIDATES_FILE, def main
- `scripts/ingest_google_candidates.py` — SESSION_ID, SESSION_FILE, CANDIDATES_FILE, def clean_amp_url, def main
- `scripts/ingest_media_candidates.py` — SESSION_ID, SESSION_FILE, CANDIDATES_FILE, def main
- `scripts/ingest_verified_dois.py` — API_BASE, SESSION_ID, CONFIRMED_DOIS, def api_post, def fetch_doi_metadata, def main
- `scripts/ingest_verified_pubmed.py` — API_BASE, SESSION_ID, CONFIRMED_PMIDS, def api_post, def fetch_pubmed_details, def main
- `scripts/ingest_verified_s2.py` — API_BASE, SESSION_ID, def api_post, def main
- `scripts/phone_harvest.py` — API, def api_post, def client, def cmd_status, def cmd_scrape, def cmd_ingest, def session_id, def cmd_session, def cmd_cleanup
- `scripts/prune_generic_sources.py` — SESSION_ID, SESSION_FILE, URLS_TO_PRUNE, def main
- `scripts/read_last.py` — def main
- `scripts/throttle_status.py` — rows, lat, throttles, pending
- `scripts/unblock_verified_sources.py` — SESSION_ID, SESSION_FILE, def main
### tests/
- `tests/conftest.py` — def _isolated_sessions
- `tests/test_agent_llm.py` — def test_unanswered_prompt_queues_job_and_returns_empty, def test_answered_prompt_returns_agent_response, def test_get_provider_selects_agent_via_env
- `tests/test_article_compare.py` — def _profile, def test_title_from_url, def test_claim_coverage_flags_absent_fact, def test_temporal_year_absent_from_article_weakens_coverage, def test_build_proposal_splits_covered_and_additions, def test_article_proposal_route_requires_exists_status, def test_article_proposal_route_returns_proposal
- `tests/test_browser.py` — class _FakeResp(__init__), class _FakePage(__init__, goto, evaluate, close, url), def test_page_link_status_classifies_render_results, def test_browser_link_status_opens_throwaway_page_and_closes_it
- `tests/test_claim_selection.py` — def _src, def test_citation_rank_prefers_independent_significant_verified, def test_rank_sources_for_fact_orders_and_flags_context, def test_build_claim_clusters_groups_same_fact_across_links, def test_suggest_draft_upgrades_collapses_dupes_and_classifies
- `tests/test_classifier.py` — class _ExplodingProvider(complete), class _JsonProvider(__init__, complete), def test_known_news_domains_classify_without_llm, def test_known_primary_domains_classify_without_llm, def test_unknown_domain_uses_llm_reliability_field
- `tests/test_discarded_registry.py` — def test_record_discarded_canonical_dedup, def test_is_known_or_discarded, def test_get_known_and_discarded_canonical_urls, def test_recover_discarded, def test_get_discarded_by_reason
- `tests/test_draft.py` — def _source, def _ready_profile, def test_audit_excludes_cv_animal_birth_and_unverified_sources, def test_audit_blocks_profiles_without_explicit_draft_approval, def test_audit_blocks_drafts_without_independent_secondary_coverage, def test_audit_warns_when_achievement_claim_rests_on_primary_source, def test_audit_no_achievement_warning_when_sources_are_independent, def test_research_action_rule_accepts_common_research_verbs, def test_birth_noise_rule_scans_source_title_too, def test_human_birth_claim_not_blocked_by_animal_rule, … +51 more
- `tests/test_draft_hi.py` — def _sample_profile, def test_render_hindi_draft_contains_hindi_infobox_and_sections
- `tests/test_fetcher_fallback.py` — def test_fetch_url_direct_success, def test_fetch_url_mobile_bridge_fallback, def test_fetch_url_browser_server_fallback_when_mobile_unavailable, def test_check_liveness_recovers_blocked_via_mobile_bridge, def test_fetch_telemetry_records_and_advises, def test_fetch_telemetry_cooldown_and_recheck, def test_liveness_stops_after_five_host_throttles, def test_looks_throttled_text_markers
- `tests/test_forensics.py` — def test_seed_default_pivots_from_profile, def test_generate_forensic_queries, def test_forensic_routes, def test_generate_deductive_inquiries_unit, def test_forensic_inquiries_api
- `tests/test_lifecycle_audit.py` — def test_audit_discovery_stage, def test_audit_provenance_stage, def test_audit_claims_stage, def test_audit_draft_stage_blocked_when_no_evidence, def test_audit_full_lifecycle
- `tests/test_liveness.py` — def test_check_liveness_live, def test_check_liveness_dead_looks_up_wayback, def test_check_liveness_blocked, def test_get_wayback_url_parses_snapshot, def test_audit_excludes_dead_unarchived_source, def test_renderer_cites_wayback_url_for_dead_archived_source
- `tests/test_llm.py` — def test_extract_claims_is_noop_under_stub, def test_get_provider_uses_vertex_when_available, def test_get_provider_falls_back_to_agent_when_vertex_unavailable
- `tests/test_multilingual_search.py` — def test_detect_languages, def test_transliterate_name, def test_get_regional_news_outlets, def test_build_bilingual_queries_hindi, def test_build_bilingual_queries_carries_date_and_event_hint_into_hindi, def test_build_bilingual_queries_french, def test_build_bilingual_queries_german
- `tests/test_name_verifier.py` — def test_generate_name_variants_western, def test_generate_name_variants_indic, def test_verify_name_in_content_exact_and_initials, def test_verify_name_in_content_devanagari, def test_verify_name_no_match, def test_verify_name_homonym_risk, def test_namesake_risk_known_conflict_and_siblings, def test_identity_strength_full_vs_weak, def test_coauthor_profile_network_screen
- `tests/test_osint.py` — def test_openalex_search_and_ranking, def test_openalex_get_works_and_convert_sources, def test_generate_osint_dorks, def test_pdf_metadata_extraction, def test_parse_pdf_date_variants, def test_multi_archive_fallback_to_archive_today
- `tests/test_production_hardening.py` — def test_is_safe_public_url_blocks_private_and_loopback, def test_is_safe_public_url_allows_public_https, def test_fetch_url_and_liveness_reject_unsafe_urls, def test_liveness_rejects_redirect_to_private_ip, def test_atomic_session_save, def test_cite_value_escapes_wikitext_template_braces, def test_citation_with_curly_braces, def test_resume_and_delete_session_block_path_traversal, def test_browser_server_navigate_blocks_unsafe_urls, def test_network_guard_rejects_untrusted_client_addresses

### Collapsed Directories (Fractal Router)
- 📁 `tests/` — 12 file(s) (test_domain_trust_classification, test_source_provenance_classification, test_academic_indexes_never_count_as_independent_news, test_search_discovery_does_not_make_unknown_site_independent…) · `ck show tests/` lists them

_Router mode: 134 of 146 files shown, ranked by import fan-in. Locate a symbol with `ck where <name>`; list any file's symbols with `ck show <path>`; pull the working set with `ck compartment auto`._
