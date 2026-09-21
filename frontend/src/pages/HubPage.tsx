import { useState, useEffect } from "react";
import type { PersonProfile, WikiStatus, DraftAudit } from "../types";
import { generateDraft, getDraftAudit, profileRef } from "../api";
import WorkspaceStatusBanner from "../components/WorkspaceStatusBanner";
import FetchOpsPanel from "../components/FetchOpsPanel";
import EvidenceWorkspace from "../components/EvidenceWorkspace";
import LivingDossier from "../components/LivingDossier";
import ForensicCanvas from "../components/ForensicCanvas";
import DraftAndOutputs from "../components/DraftAndOutputs";
import GuideTab from "../components/GuideTab";
import { NotabilityBadge } from "../components/WorkspaceCards";

interface Props {
  initialProfile: PersonProfile;
  wikiStatus: WikiStatus;
  resumedSession?: boolean;
  onDraft: (profile: PersonProfile) => void;
  onReset: () => void;
  relayPending?: { url: string; text: string } | null;
  onRelayConsumed?: () => void;
}

export type PrimarySpace = "evidence" | "dossier" | "forensics" | "outputs";

export default function HubPage({
  initialProfile,
  wikiStatus,
  resumedSession,
  onReset,
}: Props) {
  const [profile, setProfile] = useState(initialProfile);
  const [showResumedBanner, setShowResumedBanner] = useState(Boolean(resumedSession));
  const [activeSpace, setActiveSpace] = useState<PrimarySpace>("evidence");
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [draftAudit, setDraftAudit] = useState<DraftAudit | null>(null);
  const [openedLinks, setOpenedLinks] = useState<Set<string>>(new Set());
  const [showVmDesktop, setShowVmDesktop] = useState(false);
  const [showBridgeModal, setShowBridgeModal] = useState(false);
  const [showGuideModal, setShowGuideModal] = useState(false);

  const hasVerifiedSources = profile.sources.some(s => s.human_verified);

  useEffect(() => {
    let cancelled = false;
    getDraftAudit(profileRef(profile))
      .then(audit => {
        if (!cancelled) setDraftAudit(audit);
      })
      .catch(error => {
        console.error("Draft audit error:", error);
      });
    return () => {
      cancelled = true;
    };
  }, [profile]);

  async function handleGenerateDraft() {
    setDrafting(true);
    setDraftError(null);
    try {
      const result = await generateDraft(profileRef(profile));
      setProfile(result.profile);
      setActiveSpace("outputs");
    } catch (e) {
      setDraftError(String(e));
    } finally {
      setDrafting(false);
    }
  }

  function markLinkOpened(url: string) {
    setOpenedLinks(prev => new Set(prev).add(url));
  }

  const missingSlotsCount = (profile.missing_slots ?? []).length;

  return (
    <div
      className="hub-root"
      style={{
        maxWidth: showVmDesktop ? 1560 : 1200,
        margin: "0 auto",
        padding: "20px 20px 60px",
        transition: "max-width 0.2s ease",
      }}
    >
      {/* Streamlined Workspace Header */}
      <header
        className="workspace-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
          paddingBottom: 16,
          borderBottom: "1px solid var(--border)",
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {profile.photo_url ? (
            <img
              src={profile.photo_url}
              alt={profile.name}
              style={{
                width: 52,
                height: 52,
                borderRadius: 8,
                objectFit: "cover",
                border: "1px solid var(--border)",
              }}
            />
          ) : (
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 8,
                background: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 22,
                fontWeight: 800,
                color: "#ffffff",
                flexShrink: 0,
              }}
            >
              {profile.name[0] || "P"}
            </div>
          )}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>{profile.name}</h1>
              {hasVerifiedSources && profile.notability && (
                <NotabilityBadge n={profile.notability} />
              )}
            </div>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 0" }}>
              {[profile.field, profile.affiliation, profile.nationality].filter(Boolean).join(" · ")}
            </p>
          </div>
        </div>

        {/* Global Toolbar */}
        <div className="workspace-actions" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setShowBridgeModal(true)}
            style={{
              fontSize: 12,
              padding: "7px 12px",
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              color: "#166534",
            }}
            title="Configure Browser Scraping: Mobile Carrier Bridge (primary) vs VM Chromium Desktop (fallback)"
          >
            <span>📱</span>
            <span style={{ fontWeight: 600 }}>Browser Bridge</span>
            <span style={{ fontSize: 10, background: "#dcfce7", color: "#15803d", padding: "1px 6px", borderRadius: 10, fontWeight: 700 }}>
              {showVmDesktop ? "VM + Mobile" : "Mobile Primary"}
            </span>
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setShowGuideModal(true)}
            style={{
              fontSize: 12,
              padding: "7px 12px",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            📖 Guide
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={onReset}
            style={{ fontSize: 12, padding: "7px 12px" }}
          >
            New Subject
          </button>
        </div>
      </header>

      {/* Resumed Banner */}
      {showResumedBanner && (
        <div
          style={{
            marginBottom: 14,
            padding: "10px 14px",
            borderRadius: 8,
            background: "rgba(245, 158, 11, 0.12)",
            border: "1px solid #f59e0b55",
            color: "#92400e",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span style={{ flex: 1 }}>
            Resumed existing research session for <strong>{profile.name}</strong>.
          </span>
          <button
            type="button"
            onClick={() => setShowResumedBanner(false)}
            style={{
              background: "none",
              border: "none",
              color: "#92400e",
              fontSize: 15,
              cursor: "pointer",
              fontWeight: 700,
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Wikipedia Status Alert */}
      <WorkspaceStatusBanner wikiStatus={wikiStatus} />

      <FetchOpsPanel />

      {/* Primary 3-Step Guided Workflow Bar */}
      <nav
        className="primary-space-bar"
        aria-label="Research workflow steps"
        style={{
          display: "flex",
          gap: 6,
          background: "var(--surface)",
          padding: "6px",
          borderRadius: 12,
          border: "1px solid var(--border)",
          marginBottom: 16,
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveSpace("evidence")}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            padding: "9px 14px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: activeSpace === "evidence" ? 700 : 500,
            background: activeSpace === "evidence" ? "var(--primary)" : "transparent",
            color: activeSpace === "evidence" ? "#ffffff" : "var(--muted)",
            cursor: "pointer",
            transition: "all 0.15s ease",
            border: "none",
          }}
        >
          <span style={{ fontSize: 15 }}>1️⃣</span>
          <span>Sources &amp; Evidence</span>
          <span
            style={{
              background: activeSpace === "evidence" ? "rgba(255,255,255,0.25)" : "var(--bg)",
              color: activeSpace === "evidence" ? "#ffffff" : "var(--muted)",
              padding: "2px 7px",
              borderRadius: 10,
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            {profile.sources.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSpace("dossier")}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            padding: "9px 14px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: activeSpace === "dossier" ? 700 : 500,
            background: activeSpace === "dossier" ? "var(--primary)" : "transparent",
            color: activeSpace === "dossier" ? "#ffffff" : "var(--muted)",
            cursor: "pointer",
            transition: "all 0.15s ease",
            border: "none",
          }}
        >
          <span style={{ fontSize: 15 }}>2️⃣</span>
          <span>Living Dossier &amp; Facts</span>
          <span
            style={{
              background: activeSpace === "dossier" ? "rgba(255,255,255,0.25)" : "var(--bg)",
              color: activeSpace === "dossier" ? "#ffffff" : "var(--muted)",
              padding: "2px 7px",
              borderRadius: 10,
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            {profile.claims.length}
          </span>
          {missingSlotsCount > 0 && (
            <span
              style={{
                background: "var(--warning)",
                color: "#ffffff",
                padding: "2px 6px",
                borderRadius: 10,
                fontSize: 10,
                fontWeight: 700,
              }}
              title={`${missingSlotsCount} biographical slots missing`}
            >
              {missingSlotsCount} missing
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveSpace("forensics")}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            padding: "9px 14px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: activeSpace === "forensics" ? 700 : 500,
            background: activeSpace === "forensics" ? "var(--primary)" : "transparent",
            color: activeSpace === "forensics" ? "#ffffff" : "var(--muted)",
            cursor: "pointer",
            transition: "all 0.15s ease",
            border: "none",
          }}
        >
          <span style={{ fontSize: 15 }}>3️⃣</span>
          <span>Forensic Leads &amp; Pivots</span>
          {((profile.auxiliary_leads ?? []).length > 0 || (profile.investigation_pivots ?? []).length > 0) && (
            <span
              style={{
                background: activeSpace === "forensics" ? "rgba(255,255,255,0.25)" : "#eff6ff",
                color: activeSpace === "forensics" ? "#ffffff" : "#1d4ed8",
                padding: "2px 7px",
                borderRadius: 10,
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              {(profile.auxiliary_leads ?? []).length} leads
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveSpace("outputs")}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            padding: "9px 14px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: activeSpace === "outputs" ? 700 : 500,
            background: activeSpace === "outputs" ? "var(--primary)" : "transparent",
            color: activeSpace === "outputs" ? "#ffffff" : "var(--muted)",
            cursor: "pointer",
            transition: "all 0.15s ease",
            border: "none",
          }}
        >
          <span style={{ fontSize: 15 }}>4️⃣</span>
          <span>Outputs &amp; Draft</span>
          {draftAudit && (
            <span
              style={{
                background: activeSpace === "outputs" ? "rgba(255,255,255,0.25)" : draftAudit.ready ? "#dcfce7" : "#fee2e2",
                color: activeSpace === "outputs" ? "#ffffff" : draftAudit.ready ? "#15803d" : "#b91c1c",
                padding: "2px 7px",
                borderRadius: 10,
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              {draftAudit.ready ? "Ready" : `${draftAudit.blockers.length} blockers`}
            </span>
          )}
        </button>
      </nav>

      {/* Main Workspace Layout + Optional Companion Remote Browser */}
      <div className={`hub-main-layout ${showVmDesktop ? "browser-open" : ""}`}>
        <main className="workspace-main-panel">
          {activeSpace === "evidence" && (
            <EvidenceWorkspace
              profile={profile}
              openedLinks={openedLinks}
              onLinkOpen={markLinkOpened}
              onProfileUpdate={setProfile}
              onSelectSubjectDossier={() => setActiveSpace("dossier")}
            />
          )}

          {activeSpace === "dossier" && (
            <LivingDossier
              profile={profile}
              onProfileUpdate={setProfile}
            />
          )}

          {activeSpace === "forensics" && (
            <ForensicCanvas
              profile={profile}
              onProfileUpdate={setProfile}
            />
          )}

          {activeSpace === "outputs" && (
            <DraftAndOutputs
              profile={profile}
              wikiStatus={wikiStatus}
              draftAudit={draftAudit}
              onGenerateDraft={handleGenerateDraft}
              drafting={drafting}
              draftError={draftError}
            />
          )}
        </main>

        {/* Companion VM Chromium Desktop Fallback */}
        {showVmDesktop && (
          <aside
            className="card companion-browser-panel"
            style={{
              padding: 0,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              border: "1px solid var(--border)",
              boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
            }}
          >
            <div
              style={{
                padding: "10px 14px",
                background: "#f8fafc",
                borderBottom: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 15 }}>🖥️</span>
                <span style={{ fontSize: 13, fontWeight: 700 }}>VM Chromium Desktop (Local Fallback)</span>
              </div>
              <button
                type="button"
                onClick={() => setShowVmDesktop(false)}
                aria-label="Close VM browser"
                style={{
                  background: "none",
                  border: "none",
                  padding: "4px 8px",
                  fontSize: 14,
                  cursor: "pointer",
                  color: "var(--muted)",
                  fontWeight: 700,
                }}
              >
                ✕
              </button>
            </div>
            <iframe
              src={`${window.location.protocol}//${window.location.hostname}:6901/vnc.html?host=${window.location.hostname}&port=6901&path=websockify&autoconnect=true&resize=scale&quality=5&reconnect=true`}
              style={{ width: "100%", flex: 1, border: "none" }}
              title="Shared Browser (live desktop)"
            />
          </aside>
        )}
      </div>

      {/* Browser Bridge Modal */}
      {showBridgeModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Browser Bridge and Scraping Configuration"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowBridgeModal(false)}
        >
          <div
            className="card"
            style={{
              maxWidth: 680,
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 22 }}>🌐</span>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 800, margin: 0 }}>Browser Bridge &amp; Anti-Bot Infrastructure</h3>
                  <p style={{ fontSize: 12, color: "var(--muted)", margin: "2px 0 0" }}>
                    How PersonProbe safely scrapes web evidence without getting IP-blocked
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setShowBridgeModal(false)}
                style={{ padding: "4px 10px", fontSize: 12 }}
              >
                Close ✕
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Primary Mobile Bridge Card */}
              <div
                style={{
                  padding: "16px",
                  borderRadius: 8,
                  border: "1px solid #bbf7d0",
                  background: "#f0fdf4",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 18 }}>📱</span>
                    <strong style={{ fontSize: 14, color: "#166534" }}>Primary: OpenScrape Mobile Browser Bridge</strong>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 10, background: "#dcfce7", color: "#15803d" }}>
                    Active Carrier IP
                  </span>
                </div>
                <p style={{ fontSize: 12, color: "#166534", lineHeight: 1.5, margin: "0 0 10px" }}>
                  All automated scrapes and agent fetches route through the physical Android device on an Indian cellular mobile network. This transparently bypasses Cloudflare Ray ID blocks, bot detection walls, and ResearchGate shields that block datacenter IP addresses.
                </p>
                <div style={{ fontSize: 11, background: "#ffffff", border: "1px solid #bbf7d0", padding: "8px 12px", borderRadius: 6, color: "#374151" }}>
                  <strong>Need CAPTCHA solving?</strong> If a page presents an interactive slider or Cloudflare challenge, run:
                  <code style={{ display: "block", marginTop: 4, fontFamily: "monospace", color: "#1e40af", background: "#f8fafc", padding: "4px 8px", borderRadius: 4 }}>
                    python3 /home/ubuntu/Expeei/android-browser/phone_ctl.py solve &lt;url&gt;
                  </code>
                  and complete the challenge directly on the connected phone screen.
                </div>
              </div>

              {/* VM Chromium Fallback Card */}
              <div
                style={{
                  padding: "16px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "#ffffff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 18 }}>🖥️</span>
                    <strong style={{ fontSize: 14 }}>Secondary / Fallback: VM Chromium Desktop (Port :6901)</strong>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 10, background: "#f1f5f9", color: "#64748b" }}>
                    Datacenter IP (130.210.59.249)
                  </span>
                </div>
                <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5, margin: "0 0 12px" }}>
                  A headless virtual desktop running directly on the cloud VM. Useful for inspecting unblocked pages, inspecting domestic endpoints, or debugging locally. Note: Cloudflare and protected sites will block this IP.
                </p>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => {
                      setShowVmDesktop(!showVmDesktop);
                      setShowBridgeModal(false);
                    }}
                    style={{ fontSize: 12, padding: "6px 14px" }}
                  >
                    {showVmDesktop ? "Hide VM Desktop Screen" : "Open Live VM Desktop Screen"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Guide Modal */}
      {showGuideModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="How It Works and Buttons Guide"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setShowGuideModal(false)}
        >
          <div
            className="card"
            style={{
              maxWidth: 780,
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>📖 Workflow Guide &amp; Controls</h3>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setShowGuideModal(false)}
                style={{ padding: "4px 10px", fontSize: 12 }}
              >
                Close ✕
              </button>
            </div>
            <GuideTab />
          </div>
        </div>
      )}
    </div>
  );
}
