import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AuditView() {
  const [rows, setRows] = useState([]);
  const [verify, setVerify] = useState(null);
  const [q, setQ] = useState("");

  useEffect(() => { api.audit({ limit: 500 }).then(setRows).catch(() => {}); }, []);

  const shown = rows.filter((r) => !q || JSON.stringify(r).toLowerCase().includes(q.toLowerCase()));

  function exportCsv() {
    const head = ["id", "ts", "actor", "action", "entity_type", "entity_id", "details", "hash"];
    const esc = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
    const csv = [head.join(","), ...shown.map((r) => head.map((h) => esc(h === "details" ? JSON.stringify(r.details) : r[h])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "audit_trail.csv";
    a.click();
  }

  return (
    <main className="audit-page">
      <div className="audit-tools">
        <h2>Audit trail</h2>
        <input placeholder="Filter (user, action, model version…)" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="ghost" onClick={() => api.verifyAudit().then(setVerify)}>Verify hash chain</button>
        <button className="ghost" onClick={exportCsv}>Export CSV</button>
        {verify && (
          <span className={verify.valid ? "ok" : "error"}>
            {verify.valid ? `✓ intact (${verify.checked} events)` : `✗ chain broken at event #${verify.broken_at_event_id}`}
          </span>
        )}
      </div>
      <p className="muted small">
        Append-only. Each event stores the SHA-256 of the previous one, so editing or deleting any row is detectable.
      </p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th><th>Hash</th></tr></thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.id}</td>
                <td className="mono">{new Date(r.ts).toLocaleString()}</td>
                <td>{r.actor}</td>
                <td><span className={`act act-${r.action.split("_")[0]}`}>{r.action.replaceAll("_", " ")}</span></td>
                <td className="mono">{r.entity_type ? `${r.entity_type} ${r.entity_id}` : "—"}</td>
                <td className="mono small details">{Object.keys(r.details || {}).length ? JSON.stringify(r.details) : ""}</td>
                <td className="mono muted">{r.hash}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
