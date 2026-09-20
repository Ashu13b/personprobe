import { useState } from "react";

export default function GuideTab() {
  const [activeSection, setActiveSection] = useState<string>("all");

  const buttonItems = [
    {
      group: "Source Verification (L1–L3)",
      badge: "👤 Confirm as Human",
      badgeStyle: { background: "rgba(37, 99, 235, 0.12)", color: "var(--primary)", border: "1px solid rgba(37, 99, 235, 0.3)" },
      title: "L2 Identity Confirmation (Human)",
      meaning: "Confirms that you reviewed this link and confirmed it is about this exact subject (not an unrelated namesake). Automatically unlocks claim extraction.",
      whenToUse: "When you inspect a link and confirm the person matches.",
    },
    {
      group: "Source Verification (L1–L3)",
      badge: "🤖 Confirm as AI",
      badgeStyle: { background: "rgba(16, 185, 129, 0.12)", color: "#10b981", border: "1px solid rgba(16, 185, 129, 0.3)" },
      title: "L2 Identity Confirmation (AI / Agent)",
      meaning: "Confirms identity as an autonomous AI agent. Extracts claims into the workspace and stamps 'agent' in the audit trail.",
      whenToUse: "When running autonomous research runs or automated cross-reference checks.",
    },
    {
      group: "Source Verification (L1–L3)",
      badge: "✗ Wrong Person",
      badgeStyle: { background: "rgba(220, 38, 38, 0.12)", color: "var(--danger)", border: "1px solid rgba(220, 38, 38, 0.3)" },
      title: "Reject Namesake / Irrelevant",
      meaning: "Marks this source as rejected for identity reasons (different person of the same name or unrelated topic). Excludes it from claims and draft.",
      whenToUse: "When a search result returns another person with the same name.",
    },
    {
      group: "Source Ingestion",
      badge: "🔍 Auto-Search Missing Slots",
      badgeStyle: { background: "#f0f9ff", color: "#0369a1", border: "1px solid #7dd3fc" },
      title: "Targeted Biographical Slot Sweep",
      meaning: "Runs targeted DuckDuckGo/Google search queries specifically designed to locate missing biography slots (birth date, education, career milestones, awards).",
      whenToUse: "When your subject has empty biographical slots and needs more targeted secondary sources.",
    },
    {
      group: "Forensic & Auxiliary Leads",
      badge: "⚡ Run Public Records Sweep",
      badgeStyle: { background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" },
      title: "Public Records & Theses Sweep",
      meaning: "Launches specialized multi-hop queries across Shodhganga doctoral dissertations, ICAR/Ministry sanction orders, CAT tribunal filings, and fellow recruitment notices.",
      whenToUse: "When you want to dig up buried institutional, financial, and co-worker records beyond direct name matches.",
    },
    {
      group: "Forensic & Auxiliary Leads",
      badge: "+ Add Pivot Anchor",
      badgeStyle: { background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0" },
      title: "Register Investigation Anchor",
      meaning: "Registers a landmark project, workplace institution, campus housing quarter, or recruited fellow network to explore.",
      whenToUse: "When uncovering new institutions or major schemes (e.g. Project Hisar Gaurav).",
    },
    {
      group: "Forensic & Auxiliary Leads",
      badge: "✓ Corroborated",
      badgeStyle: { background: "#dcfce7", color: "#15803d", border: "1px solid #86efac" },
      title: "Corroborate Auxiliary Evidence",
      meaning: "Marks that an auxiliary document (e.g. student thesis acknowledgment or grant order) has been inspected and confirms biographical facts.",
      whenToUse: "When an auxiliary lead provides rock-solid proof for the person's timeline, laboratory tenure, or funding.",
    },
    {
      group: "Source Ingestion",
      badge: "📱 Browser Bridge",
      badgeStyle: { background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0" },
      title: "OpenScrape Mobile Carrier Proxy",
      meaning: "Routes scraping through the physical Android phone on an Indian carrier IP to bypass Cloudflare Ray ID blocks and bot mitigation.",
      whenToUse: "Active by default. Click to view status or open the local VM Chromium screen fallback.",
    },
    {
      group: "Claim Review & Triage",
      badge: "+ Draft",
      badgeStyle: { background: "rgba(22, 163, 74, 0.15)", color: "var(--success)", border: "1px solid rgba(22, 163, 74, 0.3)" },
      title: "L5 Draft Approval",
      meaning: "Adds this exact fact into the Wikipedia wikitext article. Requires that the backing source has been confirmed (by Human or Agent).",
      whenToUse: "When you want Wikipedia readers to see this fact in the published biography.",
    },
    {
      group: "Claim Review & Triage",
      badge: "✓ Dossier",
      badgeStyle: { background: "rgba(37, 99, 235, 0.12)", color: "var(--primary)", border: "1px solid rgba(37, 99, 235, 0.3)" },
      title: "Confirm for Research Dossier Only",
      meaning: "Saves this fact into your background research dossier / markdown notes, keeping it OUT of the Wikipedia draft.",
      whenToUse: "For minor details, routine dates, or background facts that are true, but would clutter or weaken a concise Wikipedia article.",
    },
    {
      group: "Claim Review & Triage",
      badge: "✎",
      badgeStyle: { background: "#f1f5f9", color: "var(--text)", border: "1px solid var(--border)" },
      title: "Edit / Draft Wording",
      meaning: "Allows you to edit either the raw claim fact or polish the exact encyclopedic wording (paraphrase) rendered in Wikipedia.",
      whenToUse: "When an extracted fact needs better phrasing, corrected dates, or a more neutral tone.",
    },
    {
      group: "Claim Review & Triage",
      badge: "✗",
      badgeStyle: { background: "rgba(220, 38, 38, 0.12)", color: "var(--danger)", border: "1px solid rgba(220, 38, 38, 0.3)" },
      title: "Skip / Reject Claim",
      meaning: "Completely ignores and excludes this claim from both the draft and dossier.",
      whenToUse: "When a claim is inaccurate, about the wrong person, or pure noise.",
    },
    {
      group: "Draft & Submission",
      badge: "Generate Draft",
      badgeStyle: { background: "var(--primary)", color: "#fff" },
      title: "Render Wikipedia Wikitext",
      meaning: "Runs the deterministic wikitext engine to produce standard Wikipedia markup strictly from your approved claims.",
      whenToUse: "When you have reviewed your claims and the Draft Readiness checklist shows green.",
    },
    {
      group: "Draft & Submission",
      badge: "Copy for AfC (with {{subst:submit}})",
      badgeStyle: { background: "var(--primary)", color: "#fff" },
      title: "1-Click Wikipedia Submission",
      meaning: "Copies the full wikitext with Wikipedia's submission template already attached at the top.",
      whenToUse: "When pasting into Wikipedia's Articles for Creation submission form.",
    },
  ];

  const filteredButtons = activeSection === "all"
    ? buttonItems
    : buttonItems.filter(b => b.group.toLowerCase().includes(activeSection.toLowerCase()));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, paddingBottom: 40 }}>
      {/* Hero Banner */}
      <div className="card" style={{ background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)", color: "#fff", border: "none" }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>How PersonProbe Works &amp; Verification Architecture</h2>
        <p style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, maxWidth: 740, margin: 0 }}>
          PersonProbe is a dual-client biographical research workbench. Both <strong>Autonomous AI Agents</strong> and <strong>Human Editors</strong> operate as first-class clients. Evidence is verified across five progressive levels, and every decision is stamped into an immutable audit trail.
        </p>
      </div>

      {/* 5-Level Verification Framework */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>The 5-Level Verification Framework</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          <div className="card" style={{ borderTop: "4px solid #3b82f6", padding: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#3b82f6", textTransform: "uppercase", marginBottom: 4 }}>Level 1: Liveness</div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>Reachable URL</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.4, margin: 0 }}>
              Checks if the web page is alive (HTTP 200) vs broken (404/dead) or blocked by bot walls.
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #10b981", padding: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#10b981", textTransform: "uppercase", marginBottom: 4 }}>Level 2: Identity</div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>Same Person Check</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.4, margin: 0 }}>
              Confirmed by <strong>Human</strong> or <strong>AI Agent</strong>. Resolves namesakes and unlocks fact extraction.
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #8b5cf6", padding: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#8b5cf6", textTransform: "uppercase", marginBottom: 4 }}>Level 3: Provenance</div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>Source Quality</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.4, margin: 0 }}>
              Classifies sources as Independent Secondary (WP:GNG), Academic Journal, or Primary / Self-Published.
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #f59e0b", padding: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#f59e0b", textTransform: "uppercase", marginBottom: 4 }}>Level 4: Claim Settlement</div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>Verbatim Evidence</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.4, margin: 0 }}>
              Verifies that the extracted claim is backed by exact quotes from the cited source text.
            </p>
          </div>

          <div className="card" style={{ borderTop: "4px solid #ec4899", padding: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#ec4899", textTransform: "uppercase", marginBottom: 4 }}>Level 5: Draft Gate</div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px" }}>Publication Gate</p>
            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.4, margin: 0 }}>
              Triage into <strong>+ Draft</strong> (Wikipedia wikitext) or <strong>✓ Dossier</strong> (background research notes).
            </p>
          </div>
        </div>
      </div>

      {/* Dual Client Architecture Concept */}
      <div className="card" style={{ background: "rgba(37, 99, 235, 0.04)", border: "1px solid rgba(37, 99, 235, 0.2)" }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--primary)", marginBottom: 8 }}>
          👥 Dual-Client Architecture: Humans and AI Agents
        </h3>
        <p style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.6, marginBottom: 12 }}>
          In PersonProbe, human review is <strong>not mandatory</strong> for research to progress. An autonomous agent can run overnight, identify sources, confirm entity identity, extract claims, and settle them. Every operation permanently records who authorized it:
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ padding: 12, background: "#fff", borderRadius: 8, border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--primary)", display: "block", marginBottom: 4 }}>
              👤 Human Reviewer
            </span>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              Manual editorial decisions: confirming ambiguous sources, resolving edge-case namesakes, polishing wording, and approving final Wikipedia submissions.
            </p>
          </div>
          <div style={{ padding: 12, background: "#fff", borderRadius: 8, border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#10b981", display: "block", marginBottom: 4 }}>
              🤖 Autonomous AI Agent
            </span>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              Batch sweeps, deep crawls, identity cross-matching against Wikidata/OpenAlex, and claim extraction. All actions are logged with timestamps and quotes.
            </p>
          </div>
        </div>
      </div>

      {/* Button & Action Guide */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>What Every Button Means</h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>Click a category filter to see specific button actions.</p>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {["all", "source", "claim", "draft"].map(cat => (
              <button
                key={cat}
                onClick={() => setActiveSection(cat)}
                style={{
                  fontSize: 11, fontWeight: 700, padding: "4px 10px", borderRadius: 6,
                  background: activeSection === cat ? "var(--primary)" : "transparent",
                  color: activeSection === cat ? "#fff" : "var(--muted)",
                  border: activeSection === cat ? "none" : "1px solid var(--border)",
                }}
              >
                {cat === "all" ? "All Buttons" : cat === "source" ? "Sources" : cat === "claim" ? "Claims" : "Draft"}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {filteredButtons.map((btn, idx) => (
            <div key={idx} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 8, background: "#fff" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, fontWeight: 700, padding: "3px 9px", borderRadius: 5, ...btn.badgeStyle }}>
                  {btn.badge}
                </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>
                  {btn.title}
                </span>
                <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto" }}>
                  {btn.group}
                </span>
              </div>
              <p style={{ fontSize: 12, color: "var(--text)", margin: "0 0 4px", lineHeight: 1.5 }}>
                <strong>What it does:</strong> {btn.meaning}
              </p>
              <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
                <strong>When to use:</strong> {btn.whenToUse}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Frequently Asked Questions */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Frequently Asked Questions</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: Does a human have to manually verify every single source before an agent can draft?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              No. Either a Human or an Autonomous Agent can confirm identity (L2) and settle claims (L4). However, the system logs exactly who confirmed it (<code>human</code> vs <code>agent</code>) so that human editors can inspect agent-approved claims before final submission.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: Why is scraping routed through a physical mobile phone?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              Cloud virtual machines (like Google Cloud) use datacenter IP addresses that are instantly blocked by Cloudflare (Ray ID), ResearchGate, and major news publishers. Routing requests through the OpenScrape mobile phone bridge on an Indian carrier IP bypasses all datacenter bot walls.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: What belongs in "In Draft" vs "Dossier Only"?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 6px", lineHeight: 1.5 }}>
              • <strong>In Draft (+ Draft):</strong> Encyclopedic milestones meeting Wikipedia standards (major awards, significant independent press-covered discoveries, verified appointments). Keep articles concise and neutral.
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              • <strong>Dossier Only (✓ Dossier):</strong> Background research archive for humans. Include comprehensive paper lists, routine committee seats, CV details, and uncorroborated quotes that are useful for research but would be rejected as trivial or promotional on Wikipedia.
            </p>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
            <p style={{ fontSize: 13, fontWeight: 700, margin: "0 0 4px", color: "var(--primary)" }}>
              Q: Why do some verified sources have 0 claims extracted?
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
              When a source is verified, the system checks for new encyclopedic claims. A source shows 0 claims if: (1) <strong>Already Backed / Redundant:</strong> The article repeats facts already captured in your session, (2) <strong>Passing Mention:</strong> The page mentions the subject in a committee list without narrative facts, or (3) <strong>Thin Snippet:</strong> Content was brief. You can always click <em>+ Add Sourced Claim</em> to manually record facts you read on the page.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
