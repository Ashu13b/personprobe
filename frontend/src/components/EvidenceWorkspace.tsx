import { useState, useMemo, useEffect } from "react";
import type { PersonProfile } from "../types";
import {
  THEMATIC_CATEGORIES,
  ThematicCategory,
  computeCategoryCounts,
  filterSources,
} from "../thematic";
import { addSource, addSourcePaste, autoEnrich, deepCrawl, getSession, profileRef } from "../api";
import { normalizeUrl } from "../url";
import { SourceCard } from "./SourceCard";
import DiscardedTab from "./DiscardedTab";
import NamesakeRegistry from "./NamesakeRegistry";
import BookmarkletCard from "./BookmarkletCard";

interface Props {
  profile: PersonProfile;
  openedLinks: Set<string>;
  onLinkOpen: (url: string) => void;
  onProfileUpdate: (p: PersonProfile) => void;
  onSelectSubjectDossier?: () => void;
}

const PAGE_SIZE = 30;

export default function EvidenceWorkspace({
  profile,
  openedLinks,
  onLinkOpen,
  onProfileUpdate,
}: Props) {
  const [selectedCategory, setSelectedCategory] = useState<ThematicCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [livenessFilter, setLivenessFilter] = useState<"all" | "alive" | "dead" | "blocked">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "verified" | "has_claims" | "independent" | "suspect">("all");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // Add source controls
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [pipelineMsg, setPipelineMsg] = useState<string | null>(null);

  // Advanced import drawer
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advancedMode, setAdvancedMode] = useState<"paste" | "crawl">("paste");
  const [pasteUrl, setPasteUrl] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [pasteLoading, setPasteLoading] = useState(false);
  const [pasteError, setPasteError] = useState<string | null>(null);

  const [crawlSeeds, setCrawlSeeds] = useState("");
  const [crawlKeywords, setCrawlKeywords] = useState("");
  const [crawlLoading, setCrawlLoading] = useState(false);
  const [crawlResult, setCrawlResult] = useState<string | null>(null);
  const [crawlError, setCrawlError] = useState<string | null>(null);

  // Multi-level verification health and agent/human attribution
  const verificationHealth = useMemo(() => {
    const total = profile.sources.length;
    const l1Alive = profile.sources.filter(s => s.liveness === "alive").length;
    const l2Confirmed = profile.sources.filter(s => s.identity_status === "confirmed" || s.human_verified).length;
    const l3Independent = profile.sources.filter(s => s.is_independent && s.provenance_category === "independent_secondary").length;
    const agentChecks = profile.sources.reduce((acc, s) => acc + (s.verification_trail?.filter(t => t.actor === "agent").length ?? 0), 0);
    const humanChecks = profile.sources.reduce((acc, s) => acc + (s.verification_trail?.filter(t => t.actor === "human").length ?? 0), 0);
    return { total, l1Alive, l2Confirmed, l3Independent, agentChecks, humanChecks };
  }, [profile.sources]);

  // Compute category counts
  const categoryCounts = useMemo(() => {
    return computeCategoryCounts(
      profile.sources,
      profile.claims,
      profile.name,
      (profile.discarded_sources ?? []).length
    );
  }, [profile.sources, profile.claims, profile.name, profile.discarded_sources]);

  // Compute filtered sources
  const filteredList = useMemo(() => {
    if (selectedCategory === "discarded") return [];
    return filterSources(
      profile.sources,
      profile.claims,
      profile.name,
      selectedCategory,
      searchQuery,
      livenessFilter,
      statusFilter
    );
  }, [
    profile.sources,
    profile.claims,
    profile.name,
    selectedCategory,
    searchQuery,
    livenessFilter,
    statusFilter,
  ]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [selectedCategory, searchQuery, livenessFilter, statusFilter]);

  const isDuplicate =
    urlInput.trim() !== "" &&
    profile.sources.some(s => normalizeUrl(s.url) === normalizeUrl(urlInput));

  async function handleAddUrl() {
    if (!urlInput.trim() || isDuplicate) return;
    setUrlLoading(true);
    setUrlError(null);
    setPipelineMsg(null);
    try {
      const resp = await addSource(profileRef(profile), urlInput.trim());
      const newSources = resp.source ? [...profile.sources, resp.source] : profile.sources;
      onProfileUpdate({
        ...profile,
        sources: newSources,
        claims: [...profile.claims, ...resp.new_claims],
        notability: resp.notability,
        ...(resp.researcher_ids !== undefined && { researcher_ids: resp.researcher_ids }),
        ...(resp.confirmed_ids !== undefined && { confirmed_ids: resp.confirmed_ids }),
      });
      if (resp.pipeline) {
        const parts: string[] = [];
        if (resp.pipeline.doi) parts.push(`DOI: ${resp.pipeline.doi}`);
        if ((resp.pipeline.openalex_works_added ?? 0) > 0) parts.push(`${resp.pipeline.openalex_works_added} papers found`);
        if (parts.length) setPipelineMsg(parts.join(" · "));
      }
      setUrlInput("");
    } catch (e) {
      setUrlError(String(e));
    } finally {
      setUrlLoading(false);
    }
  }

  async function handleAddPaste() {
    if (!pasteUrl.trim() || !pasteText.trim()) return;
    setPasteLoading(true);
    setPasteError(null);
    try {
      const resp = await addSourcePaste(profileRef(profile), pasteUrl.trim(), pasteText.trim());
      onProfileUpdate({
        ...profile,
        sources: [...profile.sources, resp.source],
        claims: [...profile.claims, ...resp.new_claims],
        notability: resp.notability,
      });
      setPasteUrl("");
      setPasteText("");
      setShowAdvanced(false);
    } catch (e) {
      setPasteError(String(e));
    } finally {
      setPasteLoading(false);
    }
  }

  async function handleCrawl() {
    const seeds = crawlSeeds.split("\n").map(s => s.trim()).filter(Boolean);
    if (!seeds.length) return;
    const keywords = crawlKeywords.split(",").map(k => k.trim()).filter(Boolean);
    setCrawlLoading(true);
    setCrawlError(null);
    setCrawlResult(null);
    try {
      const resp = await deepCrawl(profileRef(profile), seeds, keywords);
      const updated = await getSession(profileRef(profile));
      onProfileUpdate(updated);
      setCrawlResult(`Crawled ${resp.nodes_crawled} pages · ${resp.relevant_sources} sources · ${resp.new_claims} claims`);
      setCrawlSeeds("");
      setCrawlKeywords("");
    } catch (e) {
      setCrawlError(String(e));
    } finally {
      setCrawlLoading(false);
    }
  }

  const [enrichingSlots, setEnrichingSlots] = useState(false);
  const [enrichSlotsMsg, setEnrichSlotsMsg] = useState<string | null>(null);
  const [enrichSlotsError, setEnrichSlotsError] = useState<string | null>(null);

  async function handleAutoEnrichSlots() {
    setEnrichingSlots(true);
    setEnrichSlotsMsg(null);
    setEnrichSlotsError(null);
    try {
      const res = await autoEnrich(profileRef(profile));
      if (res.ok) {
        const updated = await getSession(profileRef(profile));
        onProfileUpdate(updated);
        setEnrichSlotsMsg(`Slot search completed · ${res.added_source_count} new sources added · ${res.added_claim_count} new claims`);
      }
    } catch (e) {
      setEnrichSlotsError(String(e));
    } finally {
      setEnrichingSlots(false);
    }
  }

  async function refreshProfile() {
    try {
      const updated = await getSession(profileRef(profile));
      onProfileUpdate(updated);
    } catch (e) {
      console.error(e);
    }
  }

  const missingSlotsCount = (profile.missing_slots ?? []).length;
  const visibleSources = filteredList.slice(0, visibleCount);

  return (
    <div className="evidence-workspace" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Streamlined Source Ingest & Filter Card */}
      <div
        className="card"
        style={{
          padding: "16px 18px",
          background: "#ffffff",
          border: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          {/* Main URL Ingest */}
          <div style={{ display: "flex", gap: 8, flex: 2, minWidth: 260 }}>
            <input
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAddUrl()}
              placeholder="Paste article, profile, or paper URL to ingest…"
              aria-label="Source URL to ingest"
              style={{
                fontSize: 13,
                padding: "9px 12px",
                borderColor: isDuplicate ? "var(--warning)" : undefined,
              }}
            />
            <button
              type="button"
              className="btn-primary"
              onClick={handleAddUrl}
              disabled={urlLoading || !urlInput.trim() || isDuplicate}
              style={{ padding: "9px 16px", fontSize: 13, whiteSpace: "nowrap" }}
            >
              {urlLoading ? "Ingesting…" : "+ Ingest"}
            </button>
          </div>

          {/* Quick Filter */}
          <div style={{ position: "relative", flex: 1, minWidth: 180 }}>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="🔍 Search sources…"
              aria-label="Filter sources"
              style={{ padding: "9px 12px", fontSize: 13 }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search query"
                style={{
                  position: "absolute",
                  right: 8,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  padding: 4,
                  fontSize: 12,
                  color: "var(--muted)",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            )}
          </div>

          <button
            type="button"
            className="btn-ghost"
            onClick={handleAutoEnrichSlots}
            disabled={enrichingSlots}
            title={missingSlotsCount > 0 ? `Targeted searches for missing slots: ${(profile.missing_slots ?? []).join(", ")}` : "All biographical core slots filled"}
            style={{
              fontSize: 12,
              padding: "8px 12px",
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#f0f9ff",
              border: "1px solid #bae6fd",
              color: "#0369a1",
            }}
          >
            {enrichingSlots ? "🔄 Searching Slots…" : `🔍 Auto-Search Missing Slots${missingSlotsCount > 0 ? ` (${missingSlotsCount})` : ""}`}
          </button>

          <button
            type="button"
            className="btn-ghost"
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{ fontSize: 12, padding: "8px 12px", color: "var(--muted)" }}
          >
            {showAdvanced ? "Hide Ingestion Tools" : "⚙️ Paste / Crawl"}
          </button>
        </div>

        {isDuplicate && (
          <p style={{ color: "var(--warning)", fontSize: 12, marginTop: 6, marginBottom: 0 }}>
            ⚠️ Already in your collected sources.
          </p>
        )}
        {urlError && (
          <p style={{ color: "var(--danger)", fontSize: 12, marginTop: 6, marginBottom: 0 }}>
            {urlError}
          </p>
        )}
        {pipelineMsg && (
          <p style={{ color: "var(--success)", fontSize: 12, marginTop: 6, marginBottom: 0, fontWeight: 600 }}>
            ✓ {pipelineMsg}
          </p>
        )}
        {enrichSlotsMsg && (
          <p style={{ color: "var(--success)", fontSize: 12, marginTop: 6, marginBottom: 0, fontWeight: 600 }}>
            ✓ {enrichSlotsMsg}
          </p>
        )}
        {enrichSlotsError && (
          <p style={{ color: "var(--danger)", fontSize: 12, marginTop: 6, marginBottom: 0 }}>
            {enrichSlotsError}
          </p>
        )}

        {/* Expandable Advanced Ingestion Drawer */}
        {showAdvanced && (
          <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
              <button
                type="button"
                className={advancedMode === "paste" ? "btn-primary" : "btn-ghost"}
                onClick={() => setAdvancedMode("paste")}
                style={{ fontSize: 12, padding: "5px 12px" }}
              >
                Paste Text / PDF
              </button>
              <button
                type="button"
                className={advancedMode === "crawl" ? "btn-primary" : "btn-ghost"}
                onClick={() => setAdvancedMode("crawl")}
                style={{ fontSize: 12, padding: "5px 12px" }}
              >
                Deep Web Crawl
              </button>
            </div>

            {advancedMode === "paste" ? (
              <div>
                <BookmarkletCard />
                <input
                  value={pasteUrl}
                  onChange={e => setPasteUrl(e.target.value)}
                  placeholder="Source URL (for citation provenance)"
                  aria-label="Pasted source URL"
                  style={{ marginBottom: 8, fontSize: 13 }}
                />
                <textarea
                  value={pasteText}
                  onChange={e => setPasteText(e.target.value)}
                  placeholder="Paste article or bio text here…"
                  aria-label="Pasted text content"
                  style={{ height: 90, resize: "vertical", fontSize: 13 }}
                />
                {pasteError && <p style={{ color: "var(--danger)", fontSize: 12, margin: "4px 0" }}>{pasteError}</p>}
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleAddPaste}
                  disabled={pasteLoading || !pasteUrl.trim() || !pasteText.trim()}
                  style={{ marginTop: 6, padding: "6px 14px", fontSize: 12 }}
                >
                  {pasteLoading ? "Submitting…" : "Submit Pasted Content"}
                </button>
              </div>
            ) : (
              <div>
                <textarea
                  value={crawlSeeds}
                  onChange={e => setCrawlSeeds(e.target.value)}
                  placeholder="Seed URLs (one per line)"
                  aria-label="Seed URLs for crawling"
                  style={{ height: 70, resize: "vertical", marginBottom: 8, fontSize: 13 }}
                />
                <input
                  value={crawlKeywords}
                  onChange={e => setCrawlKeywords(e.target.value)}
                  placeholder="Filter keywords (e.g. subject name, organization, field)"
                  aria-label="Crawl keywords"
                  style={{ marginBottom: 8, fontSize: 13 }}
                />
                {crawlError && <p style={{ color: "var(--danger)", fontSize: 12, marginBottom: 6 }}>{crawlError}</p>}
                {crawlResult && <p style={{ color: "var(--success)", fontSize: 12, marginBottom: 6 }}>{crawlResult}</p>}
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleCrawl}
                  disabled={crawlLoading || !crawlSeeds.trim()}
                  style={{ padding: "6px 14px", fontSize: 12 }}
                >
                  {crawlLoading ? "Crawling…" : "Start Crawl"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Clean Category Bar */}
      <div
        className="thematic-pills-bar"
        style={{
          display: "flex",
          gap: 6,
          overflowX: "auto",
          paddingBottom: 2,
          scrollbarWidth: "none",
        }}
      >
        {THEMATIC_CATEGORIES.map(cat => {
          const count = categoryCounts[cat.id] ?? 0;
          const isSelected = selectedCategory === cat.id;
          if (cat.id === "discarded" && count === 0) return null;

          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 12px",
                borderRadius: 18,
                fontSize: 12,
                fontWeight: isSelected ? 700 : 500,
                border: isSelected ? `2px solid ${cat.badgeColor}` : "1px solid var(--border)",
                background: isSelected ? cat.badgeBg : "#ffffff",
                color: isSelected ? cat.badgeColor : "var(--text)",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.15s ease",
              }}
              title={cat.description}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
              <span
                style={{
                  background: isSelected ? cat.badgeColor : "var(--bg)",
                  color: isSelected ? "#ffffff" : "var(--muted)",
                  borderRadius: 10,
                  padding: "1px 6px",
                  fontSize: 10,
                  fontWeight: 700,
                }}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <NamesakeRegistry profile={profile} />

      {/* Discarded Sub-view or Active Sources List */}
      {selectedCategory === "discarded" ? (
        <DiscardedTab profile={profile} onRecovered={refreshProfile} />
      ) : (
        <>
          {/* Sub-filters bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 8,
              fontSize: 12,
              color: "var(--muted)",
              padding: "0 2px",
            }}
          >
            <span>
              Showing <strong>{visibleSources.length}</strong> of {filteredList.length} sources
            </span>

            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value as any)}
                aria-label="Filter by verification status"
                style={{ fontSize: 12, padding: "3px 8px", borderRadius: 6, border: "1px solid var(--border)" }}
              >
                <option value="all">All statuses</option>
                <option value="verified">Verified only</option>
                <option value="has_claims">Has extracted facts</option>
                <option value="independent">Independent media only</option>
                <option value="suspect">⚠️ Suspect identity (needs check)</option>
              </select>

              <select
                value={livenessFilter}
                onChange={e => setLivenessFilter(e.target.value as any)}
                aria-label="Filter by link liveness"
                style={{ fontSize: 12, padding: "3px 8px", borderRadius: 6, border: "1px solid var(--border)" }}
              >
                <option value="all">All links</option>
                <option value="alive">Alive</option>
                <option value="dead">Dead / archived</option>
                <option value="blocked">Blocked / mitigated</option>
              </select>
            </div>
          </div>

          {/* Multi-Level Verification & Dual-Client Health Bar */}
          {profile.sources.length > 0 && (
            <div style={{
              display: "flex", alignItems: "center", gap: 10, padding: "7px 12px",
              background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6,
              marginBottom: 10, fontSize: 11, color: "var(--muted)", flexWrap: "wrap",
            }}>
              <strong style={{ color: "var(--text)" }}>Verification Levels:</strong>
              <span>L1 Live: <strong style={{ color: "#059669" }}>{verificationHealth.l1Alive}</strong>/{verificationHealth.total}</span>
              <span>·</span>
              <span>L2 Person Confirmed: <strong style={{ color: "var(--primary)" }}>{verificationHealth.l2Confirmed}</strong>/{verificationHealth.total}</span>
              <span>·</span>
              <span>L3 Independent: <strong style={{ color: "#059669" }}>{verificationHealth.l3Independent}</strong></span>
              {(verificationHealth.agentChecks > 0 || verificationHealth.humanChecks > 0) && (
                <span style={{ marginLeft: "auto", display: "inline-flex", gap: 8 }}>
                  <span title="Actions performed autonomously by Agent">🤖 Agent: <strong>{verificationHealth.agentChecks}</strong></span>
                  <span title="Actions performed by Human">👤 Human: <strong>{verificationHealth.humanChecks}</strong></span>
                </span>
              )}
            </div>
          )}

          {/* Source Cards List */}
          {visibleSources.length === 0 ? (
            <div className="card" style={{ padding: "32px 20px", textAlign: "center", color: "var(--muted)" }}>
              <p style={{ fontSize: 24, marginBottom: 6 }}>🔍</p>
              <h4 style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>
                No matching sources
              </h4>
              <p style={{ fontSize: 12, margin: 0 }}>
                {searchQuery
                  ? `No sources matched "${searchQuery}".`
                  : "No sources found under this filter. Ingest links above to expand your research."}
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {visibleSources.map(({ source, index }) => (
                <SourceCard
                  key={source.url + index}
                  source={source}
                  sourceNumber={index + 1}
                  profileName={profileRef(profile)}
                  linkOpened={openedLinks.has(source.url)}
                  allClaims={profile.claims}
                  onLinkOpen={() => onLinkOpen(source.url)}
                  onVerified={(verified, newClaims, missingSlots) => {
                    const sources = profile.sources.map(src =>
                      src.url === source.url ? { ...src, human_verified: verified } : src
                    );
                    const freshClaims = newClaims
                      ? newClaims.filter(
                          c => !profile.claims.some(ex => ex.source_url === c.source_url && ex.text === c.text)
                        )
                      : [];
                    onProfileUpdate({
                      ...profile,
                      sources,
                      claims: [...profile.claims, ...freshClaims],
                      missing_slots: missingSlots ?? profile.missing_slots,
                    });
                  }}
                  onAssessed={(updatedSource, notability) => {
                    onProfileUpdate({
                      ...profile,
                      sources: profile.sources.map(src =>
                        src.url === updatedSource.url ? updatedSource : src
                      ),
                      notability,
                    });
                  }}
                  onRejected={result => {
                    onProfileUpdate({
                      ...profile,
                      sources: result.sources as PersonProfile["sources"],
                      claims: result.claims as PersonProfile["claims"],
                      notability: result.notability,
                    });
                  }}
                />
              ))}

              {visibleCount < filteredList.length && (
                <div style={{ textAlign: "center", padding: "12px 0" }}>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setVisibleCount(c => c + PAGE_SIZE)}
                    style={{ padding: "6px 20px", fontSize: 12 }}
                  >
                    Load More ({filteredList.length - visibleCount} remaining)
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
