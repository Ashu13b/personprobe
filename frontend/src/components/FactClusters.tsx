import { useCallback, useEffect, useState } from "react";
import { getClaimClusters, selectClusterSource, selectBestAll, profileRef, type FactCluster } from "../api";
import type { PersonProfile } from "../types";

export default function FactClusters({ profile, onChanged }: { profile: PersonProfile; onChanged?: () => void }) {
  const [clusters, setClusters] = useState<FactCluster[]>([]);
  const [multi, setMulti] = useState(0);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyMulti, setOnlyMulti] = useState(true);
  const [bulkMsg, setBulkMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await getClaimClusters(profileRef(profile));
      setClusters(d.clusters ?? []);
      setMulti(d.multi_link ?? 0);
      setTotal(d.total_facts ?? 0);
    } catch (e: any) {
      setError(e?.message || "failed to load fact clusters");
    }
  }, [profile]);

  useEffect(() => {
    load();
  }, [load]);

  async function useBest(c: FactCluster) {
    if (!c.best_source_url || c.best_source_url === (c.sources.find((s) => s.rank !== -99)?.url ?? "")) return;
    setBusy(c.cluster_id);
    setError(null);
    try {
      await selectClusterSource(profileRef(profile), c.canonical_index, c.best_source_url);
      await load();
      onChanged?.();
    } catch (e: any) {
      setError(e?.message || "rebind failed");
    } finally {
      setBusy(null);
    }
  }

  const visible = onlyMulti ? clusters.filter((c) => c.link_count > 1) : clusters;

  return (
    <section className="card" style={{ padding: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 800 }}>
          🔗 Fact Clusters <span style={{ color: "var(--muted)", fontWeight: 500, fontSize: 12 }}>({total} facts · {multi} with multiple links)</span>
        </h3>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ fontSize: 12, color: "var(--muted)", display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={onlyMulti} onChange={(e) => setOnlyMulti(e.target.checked)} />
            only facts with multiple links
          </label>
          <button
            className="btn"
            type="button"
            style={{ fontSize: 11 }}
            disabled={bulkMsg === "working"}
            onClick={async () => {
              setBulkMsg("working");
              try {
                const plan = await selectBestAll(profileRef(profile), false);
                if (!plan.count) {
                  setBulkMsg("all facts already cite their best link");
                  return;
                }
                const ok = window.confirm(
                  `Upgrade ${plan.count} fact(s) to their best-ranked link?\n\n` +
                  plan.planned.slice(0, 5).map((p: { fact: string }) => `• ${p.fact}`).join("\n") +
                  (plan.count > 5 ? `\n…and ${plan.count - 5} more` : "") +
                  "\n\nRebinding clears verification + draft approval for those facts.",
                );
                if (!ok) {
                  setBulkMsg(null);
                  return;
                }
                const res = await selectBestAll(profileRef(profile), true);
                setBulkMsg(`upgraded ${res.count} fact(s)`);
                await load();
                onChanged?.();
              } catch (e: any) {
                setBulkMsg(e?.message || "bulk select failed");
              }
            }}
          >
            {bulkMsg === "working" ? "…" : "Auto-pick best link (all facts)"}
          </button>
          {bulkMsg && bulkMsg !== "working" && <span style={{ fontSize: 11, color: "var(--muted)" }}>{bulkMsg}</span>}
        </div>
      </div>
      <p style={{ margin: "4px 0 10px", fontSize: 12, color: "var(--muted)" }}>
        One fact can be corroborated by many links. Best citation is ranked by independence, coverage depth, trust and liveness.
        Rebinding a fact to another link clears its verification and draft approval — re-confirm after switching.
      </p>
      {error && <div style={{ fontSize: 12, color: "#b91c1c", marginBottom: 8 }}>{error}</div>}
      {visible.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>No clustered facts {onlyMulti ? "with multiple links" : "yet"}.</p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 10 }}>
          {visible.slice(0, 40).map((c) => (
            <li key={c.cluster_id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div style={{ maxWidth: 720 }}>
                  <div style={{ fontSize: 13 }}>{c.canonical_text}</div>
                  <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
                    {c.field} · {c.link_count} link{c.link_count === 1 ? "" : "s"}
                    {c.approved ? " · approved for draft" : ""}
                  </div>
                </div>
                {c.best_source_url && (
                  <button
                    className="btn"
                    type="button"
                    disabled={busy === c.cluster_id}
                    onClick={() => useBest(c)}
                    style={{ fontSize: 11, alignSelf: "flex-start" }}
                    title={`Best-ranked link (${c.best_source_rank}) becomes the citation`}
                  >
                    {busy === c.cluster_id ? "…" : "Use best link"}
                  </button>
                )}
              </div>
              <div style={{ marginTop: 8, display: "grid", gap: 4 }}>
                {c.sources.slice(0, 6).map((s, i) => (
                  <div key={s.url + i} style={{ fontSize: 11.5, display: "flex", gap: 8, alignItems: "baseline" }}>
                    <span style={{ color: i === 0 ? "#15803d" : "var(--muted)", fontWeight: i === 0 ? 700 : 400 }}>
                      {i === 0 ? "★" : "·"} {s.rank}
                    </span>
                    <span style={{ color: "var(--muted)" }}>{s.category}{s.depth && s.depth !== "unassessed" ? `/${s.depth}` : ""}</span>
                    <a href={s.url} target="_blank" rel="noreferrer" style={{ color: "var(--primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 520 }}>
                      {s.title || s.url}
                    </a>
                    {s.note && <span style={{ color: "#b91c1c" }}>{s.note}</span>}
                  </div>
                ))}
                {c.sources.length > 6 && <div style={{ fontSize: 11, color: "var(--muted)" }}>+{c.sources.length - 6} more links</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
