import { useState, useMemo } from "react";
import type { PersonProfile, Claim } from "../types";
import { ProfileTab } from "./ProfileTab";
import ClaimsReview from "./ClaimsReview";
import TimelineTab from "./TimelineTab";
import { safeHref } from "../url";

interface Props {
  profile: PersonProfile;
  onProfileUpdate: (p: PersonProfile) => void;
  onLoadSuggestions?: () => void;
}

type DossierViewMode = "biography" | "review" | "timeline" | "slots";

interface BioChapter {
  id: string;
  title: string;
  icon: string;
  description: string;
  fields: string[];
  keywords: string[];
}

const UNIVERSAL_BIO_CHAPTERS: BioChapter[] = [
  {
    id: "early_life",
    title: "Early Life & Education",
    icon: "🎓",
    description: "Birth, native place, schooling, and university degrees",
    fields: ["birth_date", "birth_place", "education", "full_name", "early_life", "nationality"],
    keywords: ["born", "birth", "school", "college", "university", "degree", "ph.d", "bachelor", "master", "alumn"],
  },
  {
    id: "career",
    title: "Career & Positions",
    icon: "🏛️",
    description: "Professional appointments, organizational roles, and leadership",
    fields: ["position", "affiliation", "career", "roles", "appointment", "field"],
    keywords: ["director", "professor", "scientist", "head", "appointed", "president", "tenure", "founder", "officer"],
  },
  {
    id: "major_works",
    title: "Key Works & Breakthroughs",
    icon: "⭐",
    description: "Landmark discoveries, projects, major publications, and contributions",
    fields: ["known_for", "achievement", "publication", "paper", "project", "work"],
    keywords: ["discovery", "breakthrough", "developed", "published", "pioneer", "project", "author", "invent", "patent"],
  },
  {
    id: "awards",
    title: "Honors & Recognitions",
    icon: "🏆",
    description: "Prizes, medals, academy fellowships, and public honors",
    fields: ["award", "honors", "fellowship", "recognition"],
    keywords: ["award", "fellow", "fellowship", "medal", "prize", "honor", "honour", "distinction", "citation"],
  },
];

export default function LivingDossier({
  profile,
  onProfileUpdate,
  onLoadSuggestions,
}: Props) {
  const [viewMode, setViewMode] = useState<DossierViewMode>("biography");
  const [filterType, setFilterType] = useState<"all" | "draft" | "dossier">("all");

  const pendingClaims = useMemo(
    () => profile.claims.filter(c => c.verification === "unverified"),
    [profile.claims]
  );
  const draftClaims = useMemo(
    () => profile.claims.filter(c => c.draft_approved),
    [profile.claims]
  );
  const missingSlots = profile.missing_slots ?? [];

  // Group claims into universal biographical chapters
  const categorizedChapters = useMemo(() => {
    const claims = profile.claims;
    const assignedClaimIndices = new Set<number>();

    const chapters = UNIVERSAL_BIO_CHAPTERS.map(ch => {
      const chapterClaims: { claim: Claim; index: number }[] = [];
      claims.forEach((claim, idx) => {
        const fieldMatch = ch.fields.includes(claim.field.toLowerCase());
        const textMatch = ch.keywords.some(k => claim.text.toLowerCase().includes(k));
        if (fieldMatch || textMatch) {
          chapterClaims.push({ claim, index: idx });
          assignedClaimIndices.add(idx);
        }
      });
      return { ...ch, claims: chapterClaims };
    });

    const otherClaims: { claim: Claim; index: number }[] = [];
    claims.forEach((claim, idx) => {
      if (!assignedClaimIndices.has(idx)) {
        otherClaims.push({ claim, index: idx });
      }
    });

    return { chapters, otherClaims };
  }, [profile.claims]);

  return (
    <div className="living-dossier" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Dossier Control Header */}
      <div
        className="card"
        style={{
          padding: "14px 18px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          {[
            { id: "biography" as DossierViewMode, label: "Structured Biography", icon: "📑", count: profile.claims.length },
            { id: "review" as DossierViewMode, label: "Review Queue", icon: "✓", count: pendingClaims.length, alert: pendingClaims.length > 0 },
            { id: "timeline" as DossierViewMode, label: "Timeline", icon: "⏱️" },
            { id: "slots" as DossierViewMode, label: "Fact Slots", icon: "🎯", count: missingSlots.length },
          ].map(btn => {
            const active = viewMode === btn.id;
            return (
              <button
                key={btn.id}
                type="button"
                onClick={() => setViewMode(btn.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "6px 12px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontWeight: active ? 700 : 500,
                  background: active ? "var(--primary)" : "var(--bg)",
                  color: active ? "#ffffff" : "var(--text)",
                  border: active ? "1px solid var(--primary)" : "1px solid var(--border)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <span>{btn.icon}</span>
                <span>{btn.label}</span>
                {btn.count !== undefined && btn.count > 0 && (
                  <span
                    style={{
                      background: active
                        ? "rgba(255,255,255,0.3)"
                        : btn.alert
                        ? "#fef3c7"
                        : "var(--border)",
                      color: active
                        ? "#ffffff"
                        : btn.alert
                        ? "#92400e"
                        : "var(--muted)",
                      borderRadius: 10,
                      padding: "1px 6px",
                      fontSize: 10,
                      fontWeight: 700,
                    }}
                  >
                    {btn.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Global Stats Pill */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 12, color: "var(--muted)" }}>
          <span style={{ color: "var(--text)", fontWeight: 600 }}>
            {draftClaims.length} in draft · {profile.claims.length - draftClaims.length} in dossier
          </span>
          {profile.saturation && (
            <span
              style={{
                color: profile.saturation.level === "saturated" ? "var(--success)" : "var(--warning)",
                fontWeight: 600,
                background: profile.saturation.level === "saturated" ? "#dcfce7" : "#fef3c7",
                padding: "2px 8px",
                borderRadius: 10,
              }}
              title={`Saturation score: ${Math.round(profile.saturation.score * 100)}%`}
            >
              🌿 {profile.saturation.level}
            </span>
          )}
        </div>
      </div>

      {/* Review Callout (when there are unreviewed facts and user is on biography) */}
      {viewMode === "biography" && pendingClaims.length > 0 && (
        <div
          style={{
            padding: "10px 14px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontSize: 12, color: "#1e40af" }}>
            ⚡ <strong>{pendingClaims.length} new facts</strong> extracted from your sources need verification.
          </span>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setViewMode("review")}
            style={{ padding: "4px 12px", fontSize: 12 }}
          >
            Review &amp; Approve →
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {viewMode === "biography" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Simple Filter */}
          <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12 }}>
            <span style={{ color: "var(--muted)", fontWeight: 600 }}>Filter:</span>
            {[
              { id: "all" as const, label: `All (${profile.claims.length})` },
              { id: "draft" as const, label: `In Draft (${draftClaims.length})` },
              { id: "dossier" as const, label: `Dossier Only (${profile.claims.length - draftClaims.length})` },
            ].map(f => (
              <button
                key={f.id}
                type="button"
                onClick={() => setFilterType(f.id)}
                style={{
                  background: filterType === f.id ? "rgba(37, 99, 235, 0.1)" : "transparent",
                  border: filterType === f.id ? "1px solid var(--primary)" : "none",
                  padding: "3px 8px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: filterType === f.id ? 700 : 500,
                  color: filterType === f.id ? "var(--primary)" : "var(--muted)",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Chapters List */}
          {categorizedChapters.chapters.map(ch => {
            const visibleClaims = ch.claims.filter(({ claim }) => {
              if (filterType === "draft") return claim.draft_approved;
              if (filterType === "dossier") return !claim.draft_approved;
              return true;
            });

            if (visibleClaims.length === 0 && filterType !== "all") return null;

            return (
              <div key={ch.id} className="card" style={{ padding: "16px 18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 16 }}>{ch.icon}</span>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{ch.title}</h3>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        background: "var(--bg)",
                        color: "var(--muted)",
                        padding: "1px 7px",
                        borderRadius: 10,
                      }}
                    >
                      {visibleClaims.length}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>{ch.description}</span>
                </div>

                {visibleClaims.length === 0 ? (
                  <p style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", margin: 0 }}>
                    No facts recorded yet. Extract claims from sources or add facts manually.
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {visibleClaims.map(({ claim, index }) => (
                      <div
                        key={index}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          gap: 10,
                          padding: "8px 12px",
                          borderRadius: 6,
                          background: claim.draft_approved ? "rgba(37, 99, 235, 0.04)" : "var(--bg)",
                          border: claim.draft_approved ? "1px solid rgba(37, 99, 235, 0.2)" : "1px solid var(--border)",
                        }}
                      >
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3, flexWrap: "wrap" }}>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                textTransform: "uppercase",
                                color: "var(--muted)",
                                background: "#ffffff",
                                border: "1px solid var(--border)",
                                padding: "1px 5px",
                                borderRadius: 4,
                              }}
                            >
                              {claim.field.replace(/_/g, " ")}
                            </span>
                            {claim.draft_approved && (
                              <span style={{ fontSize: 10, fontWeight: 700, color: "var(--primary)", background: "#eff6ff", padding: "1px 5px", borderRadius: 4 }}>
                                ✓ In Draft
                              </span>
                            )}
                            {claim.is_independent && (
                              <span style={{ fontSize: 10, fontWeight: 700, color: "var(--success)", background: "#dcfce7", padding: "1px 5px", borderRadius: 4 }}>
                                Independent
                              </span>
                            )}
                          </div>
                          <p style={{ fontSize: 13, margin: 0, color: "var(--text)", lineHeight: 1.4 }}>
                            {claim.text}
                          </p>
                          {claim.source_url && (
                            <a
                              href={safeHref(claim.source_url)}
                              target="_blank"
                              rel="noreferrer"
                              style={{ fontSize: 11, color: "var(--muted)", textDecoration: "none", marginTop: 4, display: "inline-block" }}
                            >
                              🔗 {claim.source_url.length > 60 ? claim.source_url.slice(0, 60) + "…" : claim.source_url}
                            </a>
                          )}
                        </div>

                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            flexShrink: 0,
                            color: claim.verification === "confirmed" || claim.verification === "edited" ? "var(--success)" : "var(--warning)",
                          }}
                        >
                          {claim.verification === "confirmed" ? "✓ Verified" : claim.verification === "edited" ? "✎ Edited" : "⏳ Pending"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {categorizedChapters.otherClaims.length > 0 && (
            <div className="card" style={{ padding: "16px 18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 16 }}>🌐</span>
                <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Additional Research Facts</h3>
                <span style={{ fontSize: 11, background: "var(--bg)", color: "var(--muted)", padding: "1px 7px", borderRadius: 10 }}>
                  {categorizedChapters.otherClaims.length}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {categorizedChapters.otherClaims.map(({ claim, index }) => (
                  <div key={index} style={{ padding: "6px 10px", borderRadius: 6, background: "var(--bg)", border: "1px solid var(--border)", fontSize: 13 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", marginRight: 6 }}>
                      {claim.field}
                    </span>
                    <span>{claim.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Review Queue Mode */}
      {viewMode === "review" && (
        <ClaimsReview
          claims={profile.claims}
          allClaims={profile.claims}
          profile={profile}
          onProfileUpdate={onProfileUpdate}
          emptyMessage="No claims have been collected."
        />
      )}

      {/* Timeline Mode */}
      {viewMode === "timeline" && (
        <TimelineTab
          profile={profile}
          onProfileUpdate={onProfileUpdate}
          onLoadSuggestions={onLoadSuggestions}
        />
      )}

      {/* Biographical Slots Mode */}
      {viewMode === "slots" && (
        <ProfileTab
          profile={profile}
          onProfileUpdate={onProfileUpdate}
        />
      )}
    </div>
  );
}
