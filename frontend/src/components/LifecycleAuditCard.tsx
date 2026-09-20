import { useState, useEffect } from "react";
import type { FullLifecycleAudit, MobileBridgeStatus } from "../types";
import { getLifecycleAudit, getMobileBridgeStatus } from "../api";

interface Props {
  profileName: string;
  onNavigateTab?: (tab: any) => void;
}

const STAGE_ICONS: Record<string, string> = {
  discovery: "🌐",
  provenance: "🏛️",
  claims: "📑",
  draft: "📝",
};

const STATUS_TONES: Record<string, { label: string; color: string; bg: string; border: string }> = {
  completed: { label: "Completed", color: "#059669", bg: "#ecfdf5", border: "#a7f3d0" },
  in_progress: { label: "In Progress", color: "#2563eb", bg: "#eff6ff", border: "#bfdbfe" },
  attention_needed: { label: "Attention Needed", color: "#d97706", bg: "#fffbeb", border: "#fde68a" },
  blocked: { label: "Blocked", color: "#dc2626", bg: "#fef2f2", border: "#fecaca" },
};

export default function LifecycleAuditCard({ profileName, onNavigateTab }: Props) {
  const [audit, setAudit] = useState<FullLifecycleAudit | null>(null);
  const [bridgeStatus, setBridgeStatus] = useState<MobileBridgeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  function handleStageClick(stageId: string) {
    if (!onNavigateTab) return;
    if (stageId === "discovery") onNavigateTab("sources");
    else if (stageId === "provenance") onNavigateTab("sources");
    else if (stageId === "claims") onNavigateTab("claims");
    else if (stageId === "draft") onNavigateTab("claims");
  }

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [auditData, bridgeData] = await Promise.all([
        getLifecycleAudit(profileName),
        getMobileBridgeStatus().catch(() => ({ online: false })),
      ]);
      setAudit(auditData);
      setBridgeStatus(bridgeData);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [profileName]);

  if (loading && !audit) {
    return (
      <div className="card" style={{ padding: 20, textAlign: "center", color: "var(--muted)" }}>
        <p style={{ margin: 0, fontSize: 13 }}>Auditing research lifecycle…</p>
      </div>
    );
  }

  if (error && !audit) {
    return (
      <div className="card" style={{ padding: 16, borderLeft: "4px solid var(--danger)", background: "#fef2f2" }}>
        <p style={{ margin: "0 0 8px", fontSize: 13, color: "var(--danger)" }}>Failed to load lifecycle audit: {error}</p>
        <button type="button" className="btn-ghost" onClick={loadData} style={{ fontSize: 12 }}>Retry</button>
      </div>
    );
  }

  if (!audit) return null;

  const pct = Math.round(audit.completion_rate * 100);

  return (
    <div className="card" style={{ padding: "18px 20px" }}>
      {/* Top Banner: Stage & Progress */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, flexWrap: "wrap", marginBottom: 14 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1, color: "var(--muted)" }}>
              Research Lifecycle Audit
            </span>
            {bridgeStatus?.online ? (
              <span style={{
                fontSize: 11,
                fontWeight: 700,
                color: "#059669",
                background: "#ecfdf5",
                padding: "2px 8px",
                borderRadius: 12,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981" }} />
                Mobile Scrap Browser Online
              </span>
            ) : (
              <span style={{
                fontSize: 11,
                fontWeight: 600,
                color: "#6b7280",
                background: "#f3f4f6",
                padding: "2px 8px",
                borderRadius: 12,
              }}>
                Mobile Bridge Standby
              </span>
            )}
          </div>
          <h3 style={{ fontSize: 17, fontWeight: 800, margin: 0 }}>
            Lifecycle Progression: {pct}% Completed
          </h3>
        </div>

        <div style={{ textAlign: "right" }}>
          <button
            type="button"
            className="btn-ghost"
            onClick={loadData}
            style={{ fontSize: 12, padding: "4px 10px" }}
          >
            🔄 Re-Audit
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{
        width: "100%",
        height: 8,
        borderRadius: 4,
        background: "var(--border)",
        overflow: "hidden",
        marginBottom: 16,
      }}>
        <div style={{
          width: `${pct}%`,
          height: "100%",
          background: pct >= 80 ? "var(--success)" : pct >= 50 ? "var(--primary)" : "var(--warning)",
          transition: "width 0.3s ease",
        }} />
      </div>

      {/* Next Priority Action callout */}
      <div style={{
        background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)",
        border: "1px solid #86efac",
        borderRadius: 8,
        padding: "10px 14px",
        marginBottom: 16,
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 13,
        color: "#166534",
      }}>
        <span style={{ fontSize: 16 }}>🎯</span>
        <span style={{ flex: 1 }}>
          <strong>Next Action:</strong> {audit.next_action}
        </span>
      </div>

      {/* 4 Stage Accordion / Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
        {audit.stages.map((stage) => {
          const tone = STATUS_TONES[stage.status] || STATUS_TONES.in_progress;
          const isExpanded = expandedStage === stage.stage_id;
          const icon = STAGE_ICONS[stage.stage_id] || "📌";

          return (
            <div
              key={stage.stage_id}
              style={{
                border: `1px solid ${tone.border}`,
                background: isExpanded ? tone.bg : "#ffffff",
                borderRadius: 8,
                padding: "12px 14px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                  <span>{icon}</span> {stage.label}
                </span>
                <span style={{
                  fontSize: 10,
                  fontWeight: 800,
                  color: tone.color,
                  background: tone.bg,
                  border: `1px solid ${tone.border}`,
                  padding: "1px 6px",
                  borderRadius: 6,
                }}>
                  {tone.label}
                </span>
              </div>

              <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.4, flex: 1 }}>
                {stage.summary}
              </p>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 4 }}>
                {stage.recommendations.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => setExpandedStage(isExpanded ? null : stage.stage_id)}
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      fontSize: 11,
                      color: "var(--primary)",
                      cursor: "pointer",
                      textAlign: "left",
                      fontWeight: 700,
                    }}
                  >
                    {isExpanded ? "▲ Hide details" : `▼ ${stage.recommendations.length} recommendation(s)`}
                  </button>
                ) : <span />}
                {onNavigateTab && (
                  <button
                    type="button"
                    onClick={() => handleStageClick(stage.stage_id)}
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      fontSize: 11,
                      color: "var(--muted)",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Open Tab →
                  </button>
                )}
              </div>

              {isExpanded && stage.recommendations.length > 0 && (
                <ul style={{ margin: "4px 0 0", paddingLeft: 16, fontSize: 11, color: "#334155", display: "flex", flexDirection: "column", gap: 4 }}>
                  {stage.recommendations.map((rec, rIdx) => (
                    <li key={rIdx}>{rec}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
