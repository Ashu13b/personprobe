import { useState, useEffect } from "react";

export interface CheckFinding {
  category: string;
  severity: "CRITICAL" | "ERROR" | "WARNING" | "INFO";
  rule_id: string;
  message: string;
  context: string;
  suggestion: string;
}

export interface LinkAuditResult {
  url: string;
  ref_name: string;
  status: string;
  status_code: number | null;
  title: string;
  domain: string;
  is_archived: boolean;
  error_message: string;
}

export interface SentenceGroundingResult {
  sentence: string;
  has_citation: boolean;
  citation_count: number;
  matched_links: string[];
  relevance_score: number;
  flag: string;
}

export interface DraftCheckerReport {
  verdict: "PASS" | "WARN" | "FAIL";
  quality_score: number;
  sentence_count: number;
  total_citations: number;
  unique_links_count: number;
  findings: CheckFinding[];
  link_audits: LinkAuditResult[];
  grounding: SentenceGroundingResult[];
  counts_by_severity: Record<string, number>;
}

interface Props {
  profileName: string;
  defaultWikitext?: string;
}

export default function DraftChecker({ profileName, defaultWikitext = "" }: Props) {
  const [wikitext, setWikitext] = useState<string>(defaultWikitext);
  const [checkLiveLinks, setCheckLiveLinks] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<DraftCheckerReport | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");

  useEffect(() => {
    if (defaultWikitext && !wikitext) {
      setWikitext(defaultWikitext);
    }
  }, [defaultWikitext]);

  async function runAudit() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/draft/checker", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_name: profileName,
          wikitext: wikitext.trim() || undefined,
          check_live_links: checkLiveLinks,
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${resp.status}`);
      }
      const data: DraftCheckerReport = await resp.json();
      setReport(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const filteredFindings = report?.findings.filter(f => {
    if (filterSeverity === "ALL") return true;
    return f.severity === filterSeverity;
  }) || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Configuration Header Card */}
      <div
        className="card"
        style={{
          padding: 16,
          background: "#ffffff",
          border: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
              <span>🔍</span> Standalone Wiki Draft &amp; Integrity Checker
            </h3>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 0 0" }}>
              Deterministic code + intelligence engine auditing dead links, link-text grounding, WP:BLP privacy, and neutrality.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6, cursor: "pointer", color: "var(--text)" }}>
              <input
                type="checkbox"
                checked={checkLiveLinks}
                onChange={e => setCheckLiveLinks(e.target.checked)}
              />
              Verify Live URLs (HTTP probe)
            </label>
            <button
              type="button"
              className="btn-primary"
              onClick={runAudit}
              disabled={loading || (!wikitext.trim() && !profileName)}
              style={{ fontSize: 13, padding: "8px 16px" }}
            >
              {loading ? "Auditing Draft…" : "⚡ Run Integrity Audit"}
            </button>
          </div>
        </div>

        {/* Wikitext Editor / Paste Area */}
        <details style={{ marginTop: 12 }}>
          <summary style={{ fontSize: 12, fontWeight: 600, cursor: "pointer", color: "var(--primary)" }}>
            {wikitext ? "Inspect / Modify Wikitext Source (or paste external draft)" : "Paste Raw Wikitext to Audit"}
          </summary>
          <div style={{ marginTop: 8 }}>
            <textarea
              value={wikitext}
              onChange={e => setWikitext(e.target.value)}
              placeholder="Paste arbitrary wikitext here to audit any draft from any repository or human author..."
              style={{
                width: "100%",
                height: 140,
                fontFamily: "monospace",
                fontSize: 12,
                padding: 10,
                borderRadius: 6,
                border: "1px solid var(--border)",
                background: "var(--bg)",
                resize: "vertical",
              }}
            />
            {defaultWikitext && wikitext !== defaultWikitext && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setWikitext(defaultWikitext)}
                style={{ fontSize: 11, marginTop: 4, padding: "2px 8px" }}
              >
                Reset to Current Session Draft
              </button>
            )}
          </div>
        </details>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8, color: "var(--danger)", fontSize: 13 }}>
          <strong>Error running draft checker:</strong> {error}
        </div>
      )}

      {/* Audit Report View */}
      {report && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Verdict Score Banner */}
          <div
            className="card"
            style={{
              padding: "16px 20px",
              background:
                report.verdict === "PASS"
                  ? "#f0fdf4"
                  : report.verdict === "WARN"
                  ? "#fffbeb"
                  : "#fef2f2",
              border: `1px solid ${
                report.verdict === "PASS"
                  ? "#bbf7d0"
                  : report.verdict === "WARN"
                  ? "#fde68a"
                  : "#fecaca"
              }`,
              borderRadius: 8,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 28 }}>
                  {report.verdict === "PASS" ? "✅" : report.verdict === "WARN" ? "⚠️" : "❌"}
                </span>
                <div>
                  <h4 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: report.verdict === "PASS" ? "#166534" : report.verdict === "WARN" ? "#854d0e" : "#991b1b" }}>
                    AfC Verdict: {report.verdict}
                  </h4>
                  <p style={{ margin: "2px 0 0 0", fontSize: 12, color: "var(--muted)" }}>
                    {report.verdict === "PASS"
                      ? "The draft satisfies AfC integrity rules, citations, neutrality, and WP:BLP standards."
                      : report.verdict === "WARN"
                      ? "The draft has advisories or warnings that should be reviewed prior to Wikipedia AfC submission."
                      : "The draft contains blocking issues (e.g. ungrounded claims, privacy leaks, or dead links)."}
                  </p>
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                  Integrity Score
                </div>
                <div
                  style={{
                    fontSize: 26,
                    fontWeight: 900,
                    color: report.quality_score >= 80 ? "#15803d" : report.quality_score >= 50 ? "#b45309" : "#b91c1c",
                  }}
                >
                  {report.quality_score} <span style={{ fontSize: 14, fontWeight: 600 }}>/ 100</span>
                </div>
              </div>
            </div>

            {/* Quick Metrics Cards */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                gap: 10,
                marginTop: 14,
                paddingTop: 14,
                borderTop: "1px solid rgba(0,0,0,0.06)",
              }}
            >
              <div style={{ background: "rgba(255,255,255,0.7)", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>Prose Sentences</div>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{report.sentence_count}</div>
              </div>
              <div style={{ background: "rgba(255,255,255,0.7)", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>Total Footnotes</div>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{report.total_citations}</div>
              </div>
              <div style={{ background: "rgba(255,255,255,0.7)", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>Unique Links</div>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{report.unique_links_count}</div>
              </div>
              <div style={{ background: "rgba(255,255,255,0.7)", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>Issues Breakdown</div>
                <div style={{ fontSize: 12, fontWeight: 600, display: "flex", gap: 6, marginTop: 2 }}>
                  <span style={{ color: "#b91c1c" }}>{report.counts_by_severity.CRITICAL || 0} crit</span>
                  <span style={{ color: "#ea580c" }}>{report.counts_by_severity.ERROR || 0} err</span>
                  <span style={{ color: "#ca8a04" }}>{report.counts_by_severity.WARNING || 0} warn</span>
                </div>
              </div>
            </div>
          </div>

          {/* Findings Filter & Details */}
          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>
                Audit Findings ({report.findings.length})
              </h4>
              <div style={{ display: "flex", gap: 6 }}>
                {(["ALL", "CRITICAL", "ERROR", "WARNING", "INFO"] as const).map(sev => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() => setFilterSeverity(sev)}
                    style={{
                      fontSize: 11,
                      fontWeight: filterSeverity === sev ? 700 : 500,
                      padding: "2px 8px",
                      borderRadius: 12,
                      border: "1px solid var(--border)",
                      background: filterSeverity === sev ? "var(--primary)" : "none",
                      color: filterSeverity === sev ? "#fff" : "var(--muted)",
                      cursor: "pointer",
                    }}
                  >
                    {sev} {sev !== "ALL" && `(${report.counts_by_severity[sev] || 0})`}
                  </button>
                ))}
              </div>
            </div>

            {filteredFindings.length === 0 ? (
              <div style={{ padding: "20px 0", textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
                ✨ No findings in this category.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {filteredFindings.map((finding, idx) => {
                  const badgeColor =
                    finding.severity === "CRITICAL"
                      ? { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5" }
                      : finding.severity === "ERROR"
                      ? { bg: "#ffedd5", text: "#9a3412", border: "#fdba74" }
                      : finding.severity === "WARNING"
                      ? { bg: "#fef9c3", text: "#854d0e", border: "#fde047" }
                      : { bg: "#e0f2fe", text: "#075985", border: "#7dd3fc" };

                  return (
                    <div
                      key={idx}
                      style={{
                        padding: "10px 14px",
                        borderRadius: 6,
                        border: `1px solid ${badgeColor.border}`,
                        background: "#fff",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 800,
                              padding: "2px 6px",
                              borderRadius: 4,
                              background: badgeColor.bg,
                              color: badgeColor.text,
                            }}
                          >
                            {finding.severity}
                          </span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                            [{finding.category}] {finding.rule_id}
                          </span>
                        </div>
                      </div>

                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", marginTop: 4 }}>
                        {finding.message}
                      </div>

                      {finding.context && (
                        <div
                          style={{
                            marginTop: 6,
                            padding: "6px 8px",
                            background: "var(--bg)",
                            borderRadius: 4,
                            fontFamily: "monospace",
                            fontSize: 11,
                            color: "var(--muted)",
                            overflowX: "auto",
                          }}
                        >
                          {finding.context}
                        </div>
                      )}

                      {finding.suggestion && (
                        <div style={{ fontSize: 12, color: "var(--primary)", marginTop: 6, display: "flex", gap: 4 }}>
                          <span>💡</span>
                          <span><strong>Suggested Fix:</strong> {finding.suggestion}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Sentence Grounding & Alignment Grid */}
          <details className="card" style={{ padding: 16 }}>
            <summary style={{ fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
              📝 Sentence-by-Sentence Grounding Matrix ({report.grounding.length} sentences)
            </summary>
            <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
              {report.grounding.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    background: item.has_citation ? "#ffffff" : "#fef2f2",
                    fontSize: 12,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, color: "var(--muted)" }}>Sentence {idx + 1}</span>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: "1px 6px",
                        borderRadius: 10,
                        background: item.has_citation ? "#dcfce7" : "#fee2e2",
                        color: item.has_citation ? "#15803d" : "#b91c1c",
                      }}
                    >
                      {item.has_citation ? `${item.citation_count} Citation(s)` : "Ungrounded"}
                    </span>
                  </div>
                  <div style={{ color: "var(--text)", lineHeight: 1.4 }}>{item.sentence}</div>
                </div>
              ))}
            </div>
          </details>

          {/* External Citation Links Table */}
          <details className="card" style={{ padding: 16 }}>
            <summary style={{ fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
              🌐 External Citations &amp; Protocol Audits ({report.link_audits.length} links)
            </summary>
            <div style={{ marginTop: 12, overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", color: "var(--muted)" }}>
                    <th style={{ padding: "6px 8px" }}>Status</th>
                    <th style={{ padding: "6px 8px" }}>Domain</th>
                    <th style={{ padding: "6px 8px" }}>Title / Ref Name</th>
                    <th style={{ padding: "6px 8px" }}>URL</th>
                  </tr>
                </thead>
                <tbody>
                  {report.link_audits.map((link, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid rgba(0,0,0,0.04)" }}>
                      <td style={{ padding: "6px 8px", fontWeight: 700 }}>
                        <span
                          style={{
                            color:
                              link.status === "valid"
                                ? "#15803d"
                                : link.status === "dead"
                                ? "#b91c1c"
                                : "#ca8a04",
                          }}
                        >
                          {link.status === "valid" ? "🟢 Valid" : link.status === "dead" ? "🔴 Dead (404)" : `🟡 ${link.status}`}
                        </span>
                      </td>
                      <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{link.domain}</td>
                      <td style={{ padding: "6px 8px", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {link.title || link.ref_name || "—"}
                      </td>
                      <td style={{ padding: "6px 8px" }}>
                        <a href={link.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--primary)", textDecoration: "none" }}>
                          {link.url.length > 50 ? `${link.url.substring(0, 50)}…` : link.url}
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
