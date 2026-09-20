import { useState, useEffect } from "react";
import type { PersonProfile, DiscardedSource } from "../types";
import { getDiscardedSources, recoverDiscardedSource, profileRef } from "../api";

interface Props {
  profile: PersonProfile;
  onRecovered: () => void;
}

const REASON_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  no_name_match: { label: "No Name Match", color: "#b45309", bg: "#fef3c7" },
  homonym_risk: { label: "Homonym Risk", color: "#b91c1c", bg: "#fee2e2" },
  unreliable: { label: "Unreliable / Self-Published", color: "#6b7280", bg: "#f3f4f6" },
  off_topic: { label: "Off Topic", color: "#4b5563", bg: "#f3f4f6" },
  user_rejected: { label: "User Rejected", color: "#4338ca", bg: "#e0e7ff" },
  user_skipped: { label: "User Skipped", color: "#6b7280", bg: "#f3f4f6" },
  dead: { label: "Dead Page", color: "#dc2626", bg: "#fef2f2" },
};

export default function DiscardedTab({ profile, onRecovered }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [discarded, setDiscarded] = useState<DiscardedSource[]>(profile.discarded_sources || []);
  const [selectedReason, setSelectedReason] = useState<string>("all");
  const [recoveringUrl, setRecoveringUrl] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadDiscarded() {
    setLoading(true);
    setError(null);
    try {
      const res = await getDiscardedSources(profileRef(profile));
      setDiscarded(res.discarded || []);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDiscarded();
  }, [profile]);

  async function handleRecover(url: string) {
    setRecoveringUrl(url);
    setSuccessMessage(null);
    try {
      const res = await recoverDiscardedSource(profileRef(profile), url);
      if (res.ok) {
        setSuccessMessage(`Recovered "${res.recovered?.title || url}". It has been removed from the discarded registry.`);
        setDiscarded(prev => prev.filter(d => d.url !== url && d.canonical_url !== url));
        onRecovered();
      } else {
        setError("Failed to recover the link. Please try again.");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setRecoveringUrl(null);
    }
  }

  // Count by reason
  const counts: Record<string, number> = { all: discarded.length };
  for (const item of discarded) {
    const r = item.reason || "no_name_match";
    counts[r] = (counts[r] || 0) + 1;
  }

  const filtered = selectedReason === "all"
    ? discarded
    : discarded.filter(d => (d.reason || "no_name_match") === selectedReason);

  const availableReasons = Object.keys(counts).filter(r => r !== "all");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header card explaining the dual purpose */}
      <div className="card" style={{ background: "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)", borderLeft: "4px solid #64748b" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 4px" }}>
              Discarded Links Registry & Recovery
            </h3>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: 0, maxWidth: 720, lineHeight: 1.5 }}>
              Candidate links filtered during web crawling or user rejection are logged here with their rejection reason.
              If an item contains an alternative name variation (e.g. Indic script, initials, or minor typo), click <strong>"Recover Source"</strong> to restore it to active research.
              This registry also protects discovery engines from re-crawling rejected URLs.
            </p>
          </div>
          <button
            type="button"
            className="btn-ghost"
            onClick={loadDiscarded}
            disabled={loading}
            style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}
          >
            🔄 Refresh Registry
          </button>
        </div>
      </div>

      {successMessage && (
        <div style={{ padding: "10px 14px", borderRadius: 8, background: "#ecfdf5", border: "1px solid #6ee7b7", color: "#065f46", fontSize: 13, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>✓ {successMessage}</span>
          <button type="button" onClick={() => setSuccessMessage(null)} style={{ background: "none", border: "none", color: "#065f46", cursor: "pointer", fontWeight: 700 }}>✕</button>
        </div>
      )}

      {error && (
        <div style={{ padding: "12px 16px", borderRadius: 8, background: "#fef2f2", border: "1px solid #fca5a5", color: "#991b1b", fontSize: 13 }}>
          <p style={{ margin: "0 0 8px" }}>{error}</p>
          <button type="button" className="btn-ghost" onClick={loadDiscarded} style={{ fontSize: 12 }}>Retry</button>
        </div>
      )}

      {/* Filter pills */}
      {discarded.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button
            type="button"
            className={selectedReason === "all" ? "btn-primary" : "btn-ghost"}
            onClick={() => setSelectedReason("all")}
            style={{ fontSize: 12, padding: "4px 12px", minHeight: 32, borderRadius: 20 }}
          >
            All ({counts.all})
          </button>
          {availableReasons.map(reason => {
            const meta = REASON_LABELS[reason] || { label: reason, color: "#374151", bg: "#f3f4f6" };
            const isActive = selectedReason === reason;
            return (
              <button
                key={reason}
                type="button"
                className={isActive ? "btn-primary" : "btn-ghost"}
                onClick={() => setSelectedReason(reason)}
                style={{
                  fontSize: 12,
                  padding: "4px 12px",
                  minHeight: 32,
                  borderRadius: 20,
                  border: isActive ? "none" : `1px solid var(--border)`,
                }}
              >
                {meta.label} ({counts[reason]})
              </button>
            );
          })}
        </div>
      )}

      {/* Loading state */}
      {loading && discarded.length === 0 && (
        <div className="card" style={{ padding: 40, textAlign: "center", color: "var(--muted)" }}>
          <p style={{ fontSize: 14 }}>Loading discarded links registry…</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && discarded.length === 0 && (
        <div className="card" style={{ padding: 48, textAlign: "center" }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🛡️</div>
          <h4 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px" }}>No Discarded Links</h4>
          <p style={{ fontSize: 13, color: "var(--muted)", maxWidth: 440, margin: "0 auto" }}>
            All discovered links have satisfied name verification, liveness, and provenance checks.
          </p>
        </div>
      )}

      {/* Filter empty state */}
      {!loading && discarded.length > 0 && filtered.length === 0 && (
        <div className="card" style={{ padding: 36, textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>
            No discarded links match the filter &quot;{selectedReason}&quot;.
          </p>
        </div>
      )}

      {/* Discarded cards list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map((item, idx) => {
          const reasonMeta = REASON_LABELS[item.reason] || {
            label: item.reason || "no_name_match",
            color: "#374151",
            bg: "#f3f4f6",
          };
          const isRecovering = recoveringUrl === item.url;

          return (
            <div
              key={`${item.canonical_url}-${idx}`}
              className="card"
              style={{
                padding: "14px 18px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "border-color 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 260 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 6,
                        color: reasonMeta.color,
                        background: reasonMeta.bg,
                      }}
                    >
                      {reasonMeta.label}
                    </span>
                    {item.name_checked && (
                      <span style={{ fontSize: 11, color: "var(--muted)" }}>
                        Checked for: <strong>{item.name_checked}</strong>
                      </span>
                    )}
                    {item.date_recorded && (
                      <span style={{ fontSize: 11, color: "var(--muted)" }}>
                        · {item.date_recorded}
                      </span>
                    )}
                  </div>

                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: 14,
                      fontWeight: 700,
                      color: "var(--text)",
                      textDecoration: "none",
                      display: "block",
                      marginBottom: 2,
                      wordBreak: "break-word",
                    }}
                  >
                    {item.title || item.url} ↗
                  </a>
                  <span style={{ fontSize: 12, color: "var(--muted)", wordBreak: "break-all" }}>
                    {item.canonical_url}
                  </span>
                </div>

                <div>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => handleRecover(item.url)}
                    disabled={isRecovering}
                    style={{
                      fontSize: 12,
                      padding: "6px 14px",
                      fontWeight: 700,
                      borderColor: "var(--primary)",
                      color: "var(--primary)",
                    }}
                  >
                    {isRecovering ? "Recovering…" : "✓ Recover Source"}
                  </button>
                </div>
              </div>

              {item.snippet && (
                <div style={{
                  fontSize: 12,
                  color: "#475569",
                  background: "#f8fafc",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #e2e8f0",
                  lineHeight: 1.45,
                  maxHeight: 90,
                  overflowY: "auto",
                }}>
                  &quot;{item.snippet}&quot;
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
