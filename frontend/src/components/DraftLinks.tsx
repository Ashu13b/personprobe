import { useCallback, useEffect, useState } from "react";
import type { DraftLink, DraftLinkStatus, DraftWikilink, DraftWikilinkStatus } from "../types";
import { getDraftLinks } from "../api";
import { getHostname, safeHref } from "../url";

const STATUS_META: Record<DraftLinkStatus, { label: string; bg: string; color: string }> = {
  ok: { label: "OK", bg: "#dcfce7", color: "#16a34a" },
  blocked: { label: "Blocked", bg: "#fef9c3", color: "#d97706" },
  dead: { label: "Dead", bg: "#fee2e2", color: "#dc2626" },
  unknown: { label: "Unknown", bg: "#f1f5f9", color: "#6b7280" },
};

const WIKI_STATUS_META: Record<DraftWikilinkStatus, { label: string; bg: string; color: string }> = {
  ok: { label: "✓ Live Article", bg: "#dcfce7", color: "#15803d" },
  disambiguation: { label: "⚠️ Disambiguation", bg: "#fef3c7", color: "#92400e" },
  missing: { label: "❌ Missing / Redlink", bg: "#fee2e2", color: "#b91c1c" },
  unknown: { label: "Unknown", bg: "#f1f5f9", color: "#6b7280" },
};

function DraftLinkRow({
  link,
  verified,
  onToggle,
}: {
  link: DraftLink;
  verified: boolean;
  onToggle: (url: string) => void;
}) {
  const meta = STATUS_META[link.status];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 11, fontWeight: 700, borderRadius: 4, padding: "1px 8px", background: meta.bg, color: meta.color, flexShrink: 0, whiteSpace: "nowrap" }}>
        {meta.label}{link.status_code ? ` ${link.status_code}` : ""}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 13, fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={link.label}>
          {link.label || getHostname(link.url)}
        </p>
        <p style={{ fontSize: 11, color: "var(--muted)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {link.url}
          {link.archived && <span style={{ marginLeft: 6, background: "rgba(99,102,241,0.12)", color: "#6366f1", borderRadius: 4, padding: "0 6px", fontWeight: 600 }}>archived</span>}
        </p>
      </div>
      <button
        onClick={() => onToggle(link.url)}
        title={verified ? "Marked as verified — click to unmark" : "I opened it and it's fine — mark verified"}
        style={{
          width: 30, height: 30, flexShrink: 0, borderRadius: 6, border: "1px solid var(--border)",
          background: verified ? "#dcfce7" : "var(--bg)", color: verified ? "#16a34a" : "var(--muted)",
          fontSize: 14, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        ✓
      </button>
      <a href={safeHref(link.url)} target="_blank" rel="noreferrer" style={{ flexShrink: 0, fontSize: 12, color: "var(--primary)", fontWeight: 600 }}>
        Open ↗
      </a>
    </div>
  );
}

function DraftWikilinkRow({ link }: { link: DraftWikilink }) {
  const meta = WIKI_STATUS_META[link.status] || WIKI_STATUS_META.unknown;
  const wikiHref = `https://en.wikipedia.org/wiki/${encodeURIComponent(link.target.replace(/ /g, "_"))}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, fontWeight: 700, borderRadius: 4, padding: "1px 8px", background: meta.bg, color: meta.color, flexShrink: 0 }}>
            {meta.label}
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>
            [[{link.target}]]
          </span>
          {link.label && link.label !== link.target && (
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              displayed as &quot;{link.label}&quot;
            </span>
          )}
        </div>
        <a
          href={wikiHref}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontSize: 12, color: "var(--primary)", fontWeight: 600, flexShrink: 0 }}
        >
          Check Wikipedia ↗
        </a>
      </div>

      {link.description && (
        <p style={{ fontSize: 12, color: "var(--muted)", margin: "2px 0 0" }}>
          {link.description}
        </p>
      )}

      {link.status === "disambiguation" && (
        <div style={{ fontSize: 11, background: "#fffbeb", border: "1px solid #fde68a", padding: "4px 8px", borderRadius: 4, color: "#92400e" }}>
          💡 <strong>Disambiguation page:</strong> Linking to &quot;{link.target}&quot; lands on a disambiguation directory.
          {link.canonical_target ? ` Use [[${link.canonical_target}|${link.label}]] instead.` : " Disambiguate to the specific article title."}
        </div>
      )}

      {link.status === "missing" && (
        <div style={{ fontSize: 11, background: "#fef2f2", border: "1px solid #fecaca", padding: "4px 8px", borderRadius: 4, color: "#991b1b" }}>
          ⚠️ <strong>Page not found (Redlink):</strong> No Wikipedia article exists for &quot;{link.target}&quot;.
          {link.canonical_target ? ` Did you mean [[${link.canonical_target}|${link.label}]]?` : " Verify spelling or remove the link brackets if unwritten."}
        </div>
      )}
    </div>
  );
}

export default function DraftLinks({ profileName }: { profileName: string }) {
  const [links, setLinks] = useState<DraftLink[] | null>(null);
  const [wikiLinks, setWikiLinks] = useState<DraftWikilink[]>([]);
  const [activeTab, setActiveTab] = useState<"external" | "wikilinks">("external");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [manualVerified, setManualVerified] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setChecking(true);
    setError(null);
    try {
      const resp = await getDraftLinks(profileName);
      setLinks(resp.links);
      setWikiLinks(resp.wiki_links || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setChecking(false);
    }
  }, [profileName]);

  useEffect(() => { load(); }, [load]);

  function toggleVerified(url: string) {
    setManualVerified(prev => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url); else next.add(url);
      return next;
    });
  }

  if (error) {
    return (
      <div className="card" style={{ fontSize: 13, color: "var(--danger)" }}>
        Could not load draft links: {error}
      </div>
    );
  }

  const counts: Record<DraftLinkStatus, number> = { ok: 0, blocked: 0, dead: 0, unknown: 0 };
  for (const link of links ?? []) counts[link.status]++;

  const problematicWikilinks = wikiLinks.filter(w => w.status === "missing" || w.status === "disambiguation");

  return (
    <div className="card" style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
      {/* Header & Tabs */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 6 }}>
          <button
            type="button"
            className={activeTab === "external" ? "btn-primary" : "btn-ghost"}
            onClick={() => setActiveTab("external")}
            style={{ fontSize: 12, padding: "5px 12px" }}
          >
            External Citation URLs ({links?.length ?? 0})
          </button>
          <button
            type="button"
            className={activeTab === "wikilinks" ? "btn-primary" : "btn-ghost"}
            onClick={() => setActiveTab("wikilinks")}
            style={{ fontSize: 12, padding: "5px 12px", display: "flex", alignItems: "center", gap: 6 }}
          >
            <span>In-Text Wikilinks ({wikiLinks.length})</span>
            {problematicWikilinks.length > 0 && (
              <span style={{ background: "#ef4444", color: "#fff", borderRadius: 10, padding: "1px 6px", fontSize: 10, fontWeight: 700 }}>
                {problematicWikilinks.length}
              </span>
            )}
          </button>
        </div>

        <button className="btn-ghost" onClick={load} disabled={checking} style={{ fontSize: 12, padding: "6px 14px", minHeight: 0 }}>
          {checking ? "Checking…" : "Re-check links"}
        </button>
      </div>

      {/* Tab 1: External Citation URLs */}
      {activeTab === "external" && (
        <>
          {links && (counts.blocked > 0 || counts.dead > 0) && (
            <div style={{ background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 8, padding: "10px 14px", fontSize: 12, marginBottom: 12, color: "#92400e" }}>
              {counts.dead} dead and {counts.blocked} blocked link{counts.blocked === 1 ? "" : "s"}. Open each below to confirm —
              dead pages should be replaced with an archived copy (archive-url) before submission.
            </div>
          )}

          {checking && links === null && (
            <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0", textAlign: "center" }}>
              Checking each cited link…
            </p>
          )}

          {links && links.length === 0 && (
            <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0" }}>
              No external links were found in the draft.
            </p>
          )}

          <div style={{ display: "flex", flexDirection: "column" }}>
            {links?.map(link => (
              <DraftLinkRow
                key={link.url}
                link={link}
                verified={manualVerified.has(link.url)}
                onToggle={toggleVerified}
              />
            ))}
          </div>
        </>
      )}

      {/* Tab 2: In-Text Wikipedia Links */}
      {activeTab === "wikilinks" && (
        <>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
            Every <code>[[wikilink]]</code> in your draft is verified against live Wikipedia articles.
            AfC reviewers reject drafts with unresolved redlinks or links to disambiguation pages (e.g. <code>[[CIRB]]</code>).
          </p>

          {wikiLinks.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--muted)", padding: "16px 0" }}>
              No in-text <code>[[wikilinks]]</code> in this draft.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {wikiLinks.map(wl => (
                <DraftWikilinkRow key={wl.target} link={wl} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
