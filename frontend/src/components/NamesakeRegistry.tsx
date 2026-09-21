import { useEffect, useState } from "react";
import { addNamesake, deleteNamesake, listNamesakes } from "../api";
import type { PersonProfile, KnownNamesake } from "../types";

export default function NamesakeRegistry({ profile }: { profile: PersonProfile }) {
  const [namesakes, setNamesakes] = useState<KnownNamesake[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [terms, setTerms] = useState("");
  const [traits, setTraits] = useState("");

  const suspectCount = (profile.sources ?? []).filter((s) => s.identity_status === "suspect").length;

  async function load() {
    try {
      const d = await listNamesakes(profile.name);
      setNamesakes(d.namesakes ?? []);
    } catch (e: any) {
      setError(e?.message || "failed to load namesakes");
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.name]);

  async function handleAdd() {
    if (!displayName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const d = await addNamesake(profile.name, {
        display_name: displayName.trim(),
        signature_terms: terms.split(",").map((t) => t.trim()).filter(Boolean),
        distinguishing_traits: traits.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setNamesakes(d.namesakes ?? []);
      setDisplayName("");
      setTerms("");
      setTraits("");
      setOpen(false);
    } catch (e: any) {
      setError(e?.message || "failed to add");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    setBusy(true);
    try {
      const d = await deleteNamesake(profile.name, id);
      setNamesakes(d.namesakes ?? []);
    } catch (e: any) {
      setError(e?.message || "failed to delete");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" style={{ padding: 14, marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 800 }}>
            🎭 Namesake Registry <span style={{ color: "var(--muted)", fontWeight: 500, fontSize: 12 }}>({namesakes.length})</span>
          </h3>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)", maxWidth: 640 }}>
            Same-name different-person signatures. Every incoming source is screened against these — matching
            text is auto-discarded before it can attach. Names with initials-only matches attach as{" "}
            <strong style={{ color: "#b45309" }}>suspect</strong> for your review
            {suspectCount > 0 ? ` (${suspectCount} currently suspect)` : ""}.
          </p>
        </div>
        <button className="btn" type="button" onClick={() => setOpen((v) => !v)} style={{ fontSize: 12 }}>
          {open ? "Cancel" : "+ Add namesake"}
        </button>
      </div>

      {error && <div style={{ marginTop: 8, fontSize: 12, color: "#b91c1c" }}>{error}</div>}

      {open && (
        <div style={{ marginTop: 12, display: "grid", gap: 8, maxWidth: 720 }}>
          <input aria-label="Namesake display name" placeholder='Display name (e.g. "Pankaj Yadav — CIRB, active post-2023")'
                 value={displayName} onChange={(e) => setDisplayName(e.target.value)} style={{ padding: 8 }} />
          <input aria-label="Signature terms" placeholder="Signature terms, comma-separated (e.g. Pankaj Yadav, Pankaj S. Yadav)"
                 value={terms} onChange={(e) => setTerms(e.target.value)} style={{ padding: 8 }} />
          <input aria-label="Distinguishing traits" placeholder="Distinguishing traits, comma-separated (e.g. active after 2023, MitoQ works)"
                 value={traits} onChange={(e) => setTraits(e.target.value)} style={{ padding: 8 }} />
          <div>
            <button className="btn primary" type="button" disabled={busy || !displayName.trim()} onClick={handleAdd} style={{ fontSize: 12 }}>
              {busy ? "Saving…" : "Save signature"}
            </button>
          </div>
        </div>
      )}

      {namesakes.length === 0 ? (
        <p style={{ margin: "10px 0 0", fontSize: 12, color: "var(--muted)" }}>No namesakes recorded for this subject yet.</p>
      ) : (
        <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "grid", gap: 8 }}>
          {namesakes.map((n) => (
            <li key={n.namesake_id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                <div>
                  <strong style={{ fontSize: 13 }}>{n.display_name}</strong>
                  <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                    by {n.created_by}
                    {n.created_at ? ` · ${n.created_at.slice(0, 10)}` : ""}
                  </div>
                  {n.signature_terms?.length > 0 && (
                    <div style={{ marginTop: 4, display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {n.signature_terms.map((t) => (
                        <span key={t} style={{ background: "#fee2e2", color: "#991b1b", borderRadius: 10, padding: "1px 7px", fontSize: 11 }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {n.notes && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4 }}>{n.notes}</div>}
                </div>
                <button className="btn" type="button" disabled={busy} onClick={() => handleDelete(n.namesake_id)} style={{ fontSize: 11 }}>
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
