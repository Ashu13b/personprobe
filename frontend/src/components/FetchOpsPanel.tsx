import { useEffect, useState } from "react";
import { getFetchTelemetry, type FetchTelemetry } from "../api";

export default function FetchOpsPanel() {
  const [data, setData] = useState<FetchTelemetry | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const load = () =>
      getFetchTelemetry()
        .then((d) => live && setData(d))
        .catch((e) => live && setError(e?.message || "telemetry unavailable"));
    load();
    const t = setInterval(load, 30000);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, []);

  if (error) {
    return <div className="card" style={{ padding: 12, fontSize: 12, color: "var(--muted)" }}>Fetch ops: {error}</div>;
  }
  if (!data) return null;

  const transports = Object.entries(data.by_transport || {});
  return (
    <div className="card" style={{ padding: "10px 14px", fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 12.5 }}>⚡ Fetch ops</strong>
        <span style={{ color: "var(--muted)" }}>avg {data.avg_latency_ms}ms · max {data.max_latency_ms}ms</span>
        <span style={{ color: data.throttle_events ? "#b45309" : "var(--muted)", fontWeight: data.throttle_events ? 700 : 500 }}>
          {data.throttle_events} throttle event{data.throttle_events === 1 ? "" : "s"}
        </span>
        {transports.map(([name, v]) => (
          <span key={name} style={{ color: "var(--muted)" }}>
            {name}: {v.count} calls · {v.avg_latency_ms ?? 0}ms{v.throttles ? ` · ${v.throttles} parked` : ""}
          </span>
        ))}
      </div>
      {data.pending_rechecks?.length ? (
        <div style={{ color: "#b45309" }}>
          ⏳ Hosts in cooldown (auto re-check):{" "}
          {data.pending_rechecks.map((p) => `${p.host} in ${p.wait_s}s`).join(" · ")}
        </div>
      ) : (
        <div style={{ color: "var(--muted)" }}>No hosts in cooldown.</div>
      )}
    </div>
  );
}
